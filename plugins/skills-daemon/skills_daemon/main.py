"""
FastAPI application for skills daemon.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__, DEFAULT_HOST, DEFAULT_PORT
from .lifecycle import LifecycleManager
from .logging import logger, set_request_id, generate_request_id, request_id_ctx
from .plugins import registry


# Slow request threshold (1 second)
SLOW_REQUEST_THRESHOLD_MS = 1000

# Lifecycle manager (initialized on startup)
lifecycle: LifecycleManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global lifecycle
    lifecycle = LifecycleManager()

    # Write PID file
    lifecycle.write_pid_file()

    # Setup signal handlers
    lifecycle.setup_signal_handlers()

    # Start plugins
    for plugin in registry.all():
        try:
            await plugin.startup()
            logger.info(f"Plugin started: {plugin.name}")
        except Exception as e:
            logger.error(f"Plugin {plugin.name} failed to start: {e}")

    # Start idle timeout checker
    timeout_task = asyncio.create_task(lifecycle.idle_timeout_checker())

    logger.info(f"Skills daemon started", version=__version__, plugins=registry.names())

    try:
        yield
    finally:
        # Stop timeout checker
        timeout_task.cancel()
        try:
            await timeout_task
        except asyncio.CancelledError:
            pass

        # Shutdown plugins
        for plugin in registry.all():
            try:
                await plugin.shutdown()
                logger.info(f"Plugin stopped: {plugin.name}")
            except Exception as e:
                logger.error(f"Plugin {plugin.name} failed to stop: {e}")

        # Run shutdown callbacks
        await lifecycle.run_shutdown_callbacks()

        # Remove PID file
        lifecycle.remove_pid_file()

        logger.info("Skills daemon stopped")


# Create FastAPI app
app = FastAPI(
    title="Skills Daemon",
    description="Central daemon for Claude Code skills with plugin architecture",
    version=__version__,
    lifespan=lifespan,
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and update idle timeout."""
    # Generate and set request ID
    request_id = request.headers.get('X-Request-ID', generate_request_id())
    token = set_request_id(request_id)

    start = time.time()

    # Update last request time
    if lifecycle:
        lifecycle.touch()

    try:
        response = await call_next(request)

        duration_ms = (time.time() - start) * 1000

        # Log at DEBUG level normally
        logger.debug(
            "request",
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Log slow requests at WARNING level
        if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "slow_request",
                request_id=request_id,
                method=request.method,
                path=str(request.url.path),
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
                threshold_ms=SLOW_REQUEST_THRESHOLD_MS,
            )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        # Reset context
        request_id_ctx.reset(token)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", path=str(request.url.path))
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "hint": "Check daemon logs for details",
        },
    )


# Core endpoints
@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    plugin_health = {}
    for plugin in registry.all():
        try:
            plugin_health[plugin.name] = plugin.health_check()
        except Exception as e:
            plugin_health[plugin.name] = {"status": "error", "error": str(e)}

    return {
        "status": "running",
        "version": __version__,
        "plugins": registry.names(),
        "plugin_health": plugin_health,
    }


@app.get("/plugins")
async def list_plugins() -> dict[str, Any]:
    """List loaded plugins with their endpoints."""
    plugins = []
    for plugin in registry.all():
        routes = []
        for route in plugin.router.routes:
            if hasattr(route, "methods"):
                for method in route.methods:
                    routes.append({
                        "method": method,
                        "path": f"/{plugin.name}{route.path}",
                    })
        plugins.append({
            "name": plugin.name,
            "description": plugin.description,
            "version": plugin.version,
            "endpoints": routes,
        })

    return {"plugins": plugins}


@app.post("/shutdown")
async def shutdown() -> dict[str, Any]:
    """Trigger graceful shutdown."""
    if lifecycle:
        lifecycle.shutdown_event.set()
    return {"success": True, "message": "Shutdown initiated"}


@app.post("/reload-plugins")
async def reload_plugins() -> dict[str, Any]:
    """Hot-reload plugins without restarting daemon.

    - Discovers new plugins and mounts them
    - Calls shutdown() on removed plugins
    - Updates plugin registry
    """
    old_plugins = set(registry.names())

    # Remove plugin routes from app (routes starting with /<plugin_name>/)
    plugin_prefixes = [f"/{name}" for name in old_plugins]
    app.routes[:] = [
        route for route in app.routes
        if not any(
            hasattr(route, 'path') and route.path.startswith(prefix)
            for prefix in plugin_prefixes
        )
    ]

    # Shutdown old plugins
    for name in old_plugins:
        plugin = registry.get(name)
        if plugin:
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down plugin {name}: {e}")

    # Clear registry and re-discover
    registry.clear()
    discover_and_register_plugins()

    # Mount new plugin routers
    mount_plugin_routers(app)

    # Startup new plugins
    for plugin in registry.all():
        try:
            await plugin.startup()
        except Exception as e:
            logger.warning(f"Error starting plugin {plugin.name}: {e}")

    new_plugins = set(registry.names())
    added = new_plugins - old_plugins
    removed = old_plugins - new_plugins
    unchanged = old_plugins & new_plugins

    logger.info(
        "Plugins reloaded",
        added=list(added),
        removed=list(removed),
        total=len(new_plugins),
    )

    return {
        "success": True,
        "added": list(added),
        "removed": list(removed),
        "reloaded": list(unchanged),
        "total": len(new_plugins),
    }


def discover_and_register_plugins() -> None:
    """Discover and register plugins dynamically.

    Discovery order:
    1. SKILLS_DAEMON_PLUGINS env var (colon-separated paths)
    2. Config file ~/.config/skills-daemon/plugins.conf (one path per line)
    3. Convention: scan ~/.claude/plugins/**/skills_plugin/
    """
    import importlib.util
    import os
    from pathlib import Path

    plugin_paths: list[Path] = []

    # 1. Environment variable
    env_plugins = os.environ.get("SKILLS_DAEMON_PLUGINS", "")
    if env_plugins:
        for p in env_plugins.split(":"):
            if p.strip():
                plugin_paths.append(Path(p.strip()).expanduser())

    # 2. Config file
    config_file = Path.home() / ".config" / "skills-daemon" / "plugins.conf"
    if config_file.exists():
        for line in config_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                plugin_paths.append(Path(line).expanduser())

    # 3. Convention-based discovery: scan for skills_plugin directories
    if not plugin_paths:
        claude_plugins = Path.home() / ".claude" / "plugins"
        if claude_plugins.exists():
            # Find all skills_plugin directories
            for skills_plugin in claude_plugins.rglob("skills_plugin"):
                if skills_plugin.is_dir() and (skills_plugin / "__init__.py").exists():
                    plugin_paths.append(skills_plugin)

    # Load each plugin
    for plugin_path in plugin_paths:
        init_file = plugin_path / "__init__.py" if plugin_path.is_dir() else plugin_path
        if not init_file.exists():
            logger.warning(f"Plugin path not found: {plugin_path}")
            continue

        try:
            load_plugin_from_path(init_file)
        except Exception as e:
            logger.warning(f"Could not load plugin from {plugin_path}: {e}")


def load_plugin_from_path(init_file: "Path") -> None:
    """Load a plugin from a Python file."""
    import importlib.util
    from pathlib import Path

    # Generate unique module name from path
    module_name = f"skills_plugin_{hash(str(init_file))}"

    spec = importlib.util.spec_from_file_location(module_name, init_file)
    if not spec or not spec.loader:
        raise ImportError(f"Could not create spec for {init_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find plugin class (must be named *Plugin and have name/router properties)
    found = False
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and attr_name.endswith("Plugin")
            and attr_name != "SkillPlugin"
            and hasattr(attr, "name")
            and hasattr(attr, "router")
        ):
            plugin = attr()
            registry.register(plugin)
            logger.info(f"Registered plugin: {plugin.name}", path=str(init_file))
            found = True
            break

    if not found:
        logger.warning(f"No plugin class found in {init_file}")


def mount_plugin_routers(app: FastAPI) -> None:
    """Mount all plugin routers to the app."""
    for plugin in registry.all():
        app.include_router(
            plugin.router,
            prefix=f"/{plugin.name}",
            tags=[plugin.name.capitalize()],
        )


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    discover_and_register_plugins()
    mount_plugin_routers(app)
    return app


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the daemon server."""
    import uvicorn

    create_app()
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",  # Suppress uvicorn logs, we have our own
    )


if __name__ == "__main__":
    run_server()
