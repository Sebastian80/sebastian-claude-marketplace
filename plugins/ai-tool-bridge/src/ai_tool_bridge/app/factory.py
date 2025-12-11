"""
Application Factory - Creates and configures the FastAPI app.

Uses the factory pattern for testability and flexibility.
Each call creates a fresh app instance with all components wired up.
"""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI

from ..builtins import register_builtin_formatters
from ..config import BridgeConfig
from ..connectors import connector_registry
from ..lifecycle import IdleMonitor, SignalHandler
from ..plugins import discover_plugins, load_plugin, plugin_registry
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

    # Register builtin formatters (synchronous)
    register_builtin_formatters()

    # Discover and load plugins BEFORE creating app (so routes can be mounted)
    _load_plugins_sync(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle."""
        logger.info("bridge_starting", version="1.0.0")

        # Connect all connectors
        await connector_registry.connect_all()

        # Start all plugins (async startup)
        await plugin_registry.startup_all()

        # Start idle monitoring
        await idle_monitor.start()

        logger.info(
            "bridge_started",
            plugins=len(plugin_registry),
            connectors=len(connector_registry._connectors),
        )

        yield

        # Shutdown
        logger.info("bridge_stopping")

        await idle_monitor.stop()
        await plugin_registry.shutdown_all()
        await connector_registry.disconnect_all()

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

    return app


def _load_plugins_sync(config: BridgeConfig) -> None:
    """Discover and load all plugins synchronously.

    Called during app creation so routes can be mounted.

    Args:
        config: Bridge configuration
    """
    manifests = discover_plugins()

    bridge_context: dict[str, Any] = {
        "config": config,
        "connector_registry": connector_registry,
    }

    for manifest in manifests:
        try:
            plugin = load_plugin(manifest, bridge_context)
            plugin_registry.register(plugin)
        except Exception as e:
            logger.error(
                "plugin_load_failed",
                name=manifest.name,
                error=str(e),
            )
