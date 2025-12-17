"""
Application Factory - Creates and configures the FastAPI app.

Uses the factory pattern for testability and flexibility.
Each call creates a fresh app instance with all components wired up.
"""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI

from ..config import BridgeConfig
from ..connectors import connector_registry
from ..lifecycle import IdleMonitor, SignalHandler, get_notifier, init_notifier
from ..plugins import discover_plugins, install_cli, load_plugin, plugin_registry
from ..reload import init_hot_reloader
from .middleware import ActivityMiddleware, ErrorMiddleware, LoggingMiddleware
from .routes import router as core_router

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

    # Create idle monitor
    idle_monitor = IdleMonitor(
        timeout_seconds=config.idle_timeout,
        on_idle=signal_handler.trigger_shutdown if signal_handler else None,
    )

    # Initialize notifier
    notifier = init_notifier(enabled=config.notifications_enabled)

    # Discover and load plugins BEFORE creating app (so routes can be mounted)
    _load_plugins_sync(config, notifier)

    # Hot reloader will be initialized after app is created
    hot_reloader = None

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

        # Send notifications for connector results
        # Notify only on connection failures (silent success)
        for name, error in connector_results.items():
            if error is not None:
                notifier.connector_connection_failed(name, str(error))

        # Start all plugins (async startup)
        plugin_results = await plugin_registry.startup_all()

        # Notify only on plugin failures (silent success)
        started_plugins = []
        for name, success in plugin_results.items():
            if success:
                started_plugins.append(name)
            else:
                notifier.plugin_start_failed(name, "Startup failed")

        # Start idle monitoring
        await idle_monitor.start()

        # Start hot reloader (watches for manifest changes)
        await hot_reloader.start()

        logger.info(
            "bridge_started",
            plugins=len(plugin_registry),
            connectors=len(connector_registry._connectors),
        )

        # Single notification with plugin names
        notifier.daemon_started(started_plugins)

        yield

        # Shutdown
        logger.info("bridge_stopping")

        await hot_reloader.stop()
        await idle_monitor.stop()
        await plugin_registry.shutdown_all()
        await connector_registry.disconnect_all()

        # Send daemon stopped notification
        notifier.daemon_stopped()

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
    app.state.notifier = notifier

    return app


def _install_plugin_dependencies(manifest: Any) -> bool:
    """Install plugin dependencies if not already installed.

    Args:
        manifest: Plugin manifest with dependencies list

    Returns:
        True if all dependencies satisfied, False on failure
    """
    if not manifest.dependencies:
        return True

    import subprocess
    import sys

    # Check which packages need installation
    missing = []
    for dep in manifest.dependencies:
        # Extract package name (e.g., "atlassian-python-api>=4.0" -> "atlassian-python-api")
        pkg_name = dep.split(">=")[0].split("==")[0].split("<")[0].split(">")[0].strip()
        # Normalize: some packages use dashes but import with underscores
        import_name = pkg_name.replace("-", "_")

        try:
            __import__(import_name)
        except ImportError:
            missing.append(dep)

    if not missing:
        return True

    logger.info("installing_dependencies", plugin=manifest.name, packages=missing)

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error("dependency_install_failed", plugin=manifest.name, error=str(e))
        return False


def _load_plugins_sync(config: BridgeConfig, notifier: Any) -> None:
    """Discover and load all plugins synchronously.

    Called during app creation so routes can be mounted.

    Args:
        config: Bridge configuration
        notifier: Notification service for plugins
    """
    manifests = discover_plugins()

    bridge_context: dict[str, Any] = {
        "config": config,
        "connector_registry": connector_registry,
        "notifier": notifier,
    }

    for manifest in manifests:
        try:
            # Install dependencies before loading
            if not _install_plugin_dependencies(manifest):
                logger.warning("skipping_plugin", name=manifest.name, reason="dependency installation failed")
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
