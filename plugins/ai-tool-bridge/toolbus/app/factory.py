"""
Application Factory - Creates and configures the FastAPI app.

Uses the factory pattern for testability and flexibility.
Each call creates a fresh app instance with all components wired up.
"""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ..events import EventBus

from fastapi import FastAPI

from ..config import BridgeConfig
from ..connectors import connector_registry
from ..events import init_event_bus
from ..lifecycle import ClaudePluginMonitor, IdleMonitor, SignalHandler, init_notifier
from ..plugins import (
    PluginManifest,
    discover_plugins,
    install_cli,
    load_plugin,
    plugin_registry,
)
from ..reload import init_hot_reloader
from .middleware import ActivityMiddleware, ErrorMiddleware, LoggingMiddleware
from .routes import router as core_router

__all__ = ["create_app"]

logger = structlog.get_logger(__name__)


def create_app(
    config: BridgeConfig | None = None,
    signal_handler: SignalHandler | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Bridge configuration (uses defaults if None)
        signal_handler: Signal handler for graceful shutdown

    Returns:
        Configured FastAPI application
    """
    if config is None:
        config = BridgeConfig()

    # Initialize event bus (central message broker)
    bus = init_event_bus()

    # Initialize notifier and subscribe to events
    notifier = init_notifier(enabled=config.notifications_enabled)
    notifier.subscribe(bus)

    # Create idle monitor
    idle_monitor = IdleMonitor(
        timeout_seconds=config.idle_timeout,
        on_idle=signal_handler.trigger_shutdown if signal_handler else None,
    )

    # Discover and load plugins BEFORE creating app (so routes can be mounted)
    _load_plugins_sync(config, bus)

    # Hot reloader will be initialized after app is created
    hot_reloader = None

    # Claude Code plugin monitor (watches for plugin installs/enables)
    claude_monitor = ClaudePluginMonitor(check_interval=2.0, config=config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle."""
        nonlocal hot_reloader
        # Initialize hot reloader with app reference
        hot_reloader = init_hot_reloader(app, config, check_interval=5.0)
        app.state.hot_reloader = hot_reloader

        logger.info("bridge_starting", version="1.0.0")

        # Connect all connectors
        connector_results = await connector_registry.connect_all()

        # Emit error events for connector failures
        for name, error in connector_results.items():
            if error is not None:
                await bus.emit("bridge", "error", {
                    "source": name,
                    "message": f"Connection failed: {error}",
                })

        # Start all plugins (async startup)
        plugin_results = await plugin_registry.startup_all()

        # Emit error events for plugin failures
        started_plugins = []
        for name, success in plugin_results.items():
            if success:
                started_plugins.append(name)
            else:
                await bus.emit("bridge", "error", {
                    "source": name,
                    "message": "Plugin startup failed",
                })

        # Start idle monitoring
        await idle_monitor.start()

        # Start hot reloader (watches for manifest changes)
        await hot_reloader.start()

        # Start Claude Code plugin monitor
        await claude_monitor.start()

        logger.info(
            "bridge_started",
            plugins=len(plugin_registry),
            connectors=len(connector_registry._connectors),
        )

        # Emit daemon started event
        await bus.emit("bridge", "daemon.started", {"plugins": started_plugins})

        yield

        # Shutdown
        logger.info("bridge_stopping")

        await claude_monitor.stop()
        await hot_reloader.stop()
        await idle_monitor.stop()
        await plugin_registry.shutdown_all()
        await connector_registry.disconnect_all()

        # Emit daemon stopped event
        await bus.emit("bridge", "daemon.stopped", {})

        logger.info("bridge_stopped")

    # Create app
    app = FastAPI(
        title="AI Tool Bridge",
        description="Unified interface for AI tool integrations",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add middleware (order matters - last added runs first)
    app.add_middleware(ErrorMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ActivityMiddleware, on_activity=idle_monitor.touch)

    # Mount core routes
    app.include_router(core_router)

    # Mount plugin routes (plugins already loaded)
    for prefix, plugin_router in plugin_registry.get_routers():
        app.include_router(plugin_router, prefix=prefix)
        logger.debug("plugin_routes_mounted", prefix=prefix)

    # Store config and components on app state
    app.state.config = config
    app.state.idle_monitor = idle_monitor
    app.state.event_bus = bus
    app.state.notifier = notifier
    app.state.claude_monitor = claude_monitor

    return app


def _install_plugin_dependencies(manifest: "PluginManifest", config: BridgeConfig) -> bool:
    """Install plugin dependencies using UV.

    Args:
        manifest: Plugin manifest with dependencies list
        config: Bridge configuration

    Returns:
        True if all dependencies satisfied, False on failure
    """
    if not manifest.dependencies:
        return True

    from ..deps import run_uv_install

    logger.info("installing_dependencies", plugin=manifest.name, deps=manifest.dependencies)
    return run_uv_install(config, manifest.dependencies)


def _load_plugins_sync(config: BridgeConfig, bus: "EventBus") -> None:
    """Discover and load all plugins synchronously.

    Called during app creation so routes can be mounted.

    Args:
        config: Bridge configuration
        bus: Event bus for plugin communication
    """
    manifests = discover_plugins()

    bridge_context: dict[str, Any] = {
        "config": config,
        "connector_registry": connector_registry,
        "event_bus": bus,
    }

    for manifest in manifests:
        try:
            # Install dependencies before loading
            if not _install_plugin_dependencies(manifest, config):
                logger.warning("skipping_plugin", name=manifest.name, reason="dep install failed")
                continue

            plugin = load_plugin(manifest, bridge_context)

            # Get CLI command name if declared
            cli_command = manifest.cli.get("command") if manifest.cli else None
            plugin_registry.register(plugin, cli_command=cli_command)

            # Install CLI wrapper if declared in manifest
            install_cli(manifest)
        except Exception as e:
            logger.error(
                "plugin_load_failed",
                name=manifest.name,
                error=str(e),
            )
