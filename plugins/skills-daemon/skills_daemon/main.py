"""
FastAPI application for skills daemon.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from pathlib import Path

from . import __version__, DEFAULT_HOST, DEFAULT_PORT
from .config import config
from .lifecycle import LifecycleManager
from .logging import logger, set_request_id, generate_request_id, request_id_ctx
from .plugins import registry
from .colors import force_colors

# Always emit ANSI color codes in formatted responses.
# Clients decide whether to strip them based on their TTY status.
force_colors(True)


# Slow request threshold (1 second)
SLOW_REQUEST_THRESHOLD_MS = 1000


def check_cwd_valid() -> bool:
    """Check if working directory still exists.

    Detects stale daemon processes whose working directory was deleted
    (e.g., plugin source directory removed during update).
    """
    try:
        cwd = Path.cwd()
        # Check for (deleted) marker in /proc on Linux
        proc_cwd = Path("/proc/self/cwd")
        if proc_cwd.exists():
            resolved = proc_cwd.resolve()
            if "(deleted)" in str(resolved):
                return False
        return cwd.exists()
    except Exception:
        return False


def check_venv_valid() -> bool:
    """Check if venv is intact.

    Verifies the stable runtime venv exists and has a working Python.
    """
    venv_python = config.venv_dir / "bin" / "python"
    return venv_python.exists()

# Lifecycle manager (initialized on startup)
lifecycle: LifecycleManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global lifecycle
    from .dependencies import sync_plugin_dependencies

    lifecycle = LifecycleManager()

    # Ensure runtime directories exist
    config.ensure_dirs()

    # Sync plugin dependencies before loading
    dep_result = sync_plugin_dependencies()
    if dep_result.get("installed"):
        logger.info(
            "Installed plugin dependencies",
            installed=dep_result["installed"],
        )

    # Write PID file
    lifecycle.write_pid_file()

    # Setup signal handlers
    lifecycle.setup_signal_handlers()

    # Start plugins and establish connections
    for plugin in registry.all():
        try:
            await plugin.startup()
            logger.info(f"Plugin started: {plugin.name}")
        except Exception as e:
            logger.error(f"Plugin {plugin.name} failed to start: {e}")

        # Auto-connect (exceptions logged but don't prevent daemon from running)
        try:
            await plugin.connect()
        except Exception as e:
            logger.warning(f"Plugin {plugin.name}: connection failed: {e}")

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

        # Shutdown plugins with timeout protection
        async def _shutdown_plugins():
            for plugin in registry.all():
                try:
                    await plugin.shutdown()
                    logger.info(f"Plugin stopped: {plugin.name}")
                except Exception as e:
                    logger.error(f"Plugin {plugin.name} failed to stop: {e}")

        try:
            await asyncio.wait_for(
                _shutdown_plugins(),
                timeout=config.shutdown_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Plugin shutdown timed out after {config.shutdown_timeout}s"
            )

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
    """Health check endpoint.

    Returns daemon status including self-healing checks:
    - cwd_valid: False if working directory was deleted (stale process)
    - venv_valid: False if venv is corrupted/missing
    """
    plugin_health = {}
    for plugin in registry.all():
        try:
            plugin_health[plugin.name] = plugin.health_check()
        except Exception as e:
            plugin_health[plugin.name] = {"status": "error", "error": str(e)}

    cwd_valid = check_cwd_valid()
    venv_valid = check_venv_valid()

    return {
        "status": "running",
        "version": __version__,
        "cwd_valid": cwd_valid,
        "venv_valid": venv_valid,
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


@app.get("/{plugin}/help")
async def plugin_help(plugin: str, command: str | None = None) -> dict[str, Any]:
    """Generate CLI help from FastAPI metadata.

    This endpoint enables self-discovery - Claude can call this
    to learn available commands and their parameters.

    Args:
        plugin: Plugin name (e.g., 'jira', 'serena')
        command: Optional command name for detailed help
    """
    plugin_obj = registry.get(plugin)
    if not plugin_obj:
        return {"error": f"Unknown plugin: {plugin}", "available": registry.names()}

    if command:
        return _generate_command_help(plugin_obj, command)
    else:
        return _generate_plugin_help(plugin_obj)


def _generate_plugin_help(plugin) -> dict[str, Any]:
    """Generate help for entire plugin from FastAPI metadata."""
    commands = []
    for route in plugin.router.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue

        # Get route name from path
        path_parts = route.path.strip("/").split("/")
        name = path_parts[0] if path_parts[0] else "root"

        # Skip internal routes
        if name.startswith("_"):
            continue

        # Get metadata from FastAPI route - prefer description (docstring) over function name
        # FastAPI stores first line of docstring in summary, full docstring in description
        summary = getattr(route, "summary", None)
        if not summary or summary == route.name:
            # Try to get from endpoint's docstring directly
            endpoint = getattr(route, "endpoint", None)
            if endpoint and endpoint.__doc__:
                summary = endpoint.__doc__.strip().split('\n')[0]
            else:
                summary = route.name or name
        methods = list(getattr(route, "methods", ["GET"]))

        commands.append({
            "name": name,
            "path": route.path,
            "summary": summary,
            "methods": methods,
        })

    return {
        "plugin": plugin.name,
        "description": plugin.description,
        "version": plugin.version,
        "commands": commands,
        "hint": f"Call GET /{plugin.name}/help?command=<name> for detailed command help",
    }


def _generate_command_help(plugin, command: str) -> dict[str, Any]:
    """Generate detailed help for a specific command."""
    for route in plugin.router.routes:
        if not hasattr(route, "path"):
            continue

        path_parts = route.path.strip("/").split("/")
        route_name = path_parts[0] if path_parts[0] else "root"

        if route_name != command:
            continue

        # Extract parameters from FastAPI's dependant
        params = []
        if hasattr(route, "dependant") and route.dependant:
            # Query parameters
            for param in getattr(route.dependant, "query_params", []):
                # Check if required (default is ... or PydanticUndefined)
                default_val = getattr(param.field_info, "default", None)
                is_required = default_val is ... or (
                    hasattr(default_val, "__class__") and
                    "PydanticUndefined" in default_val.__class__.__name__
                )

                # Use alias if defined (e.g., Query(..., alias="type"))
                display_name = getattr(param.field_info, "alias", None) or param.name
                param_info = {
                    "name": display_name,
                    "in": "query",
                    "required": is_required,
                }
                if hasattr(param.field_info, "description") and param.field_info.description:
                    param_info["description"] = param.field_info.description
                # Only add default if it's a serializable value
                if not is_required and default_val is not None:
                    try:
                        # Test if serializable
                        import json
                        json.dumps(default_val)
                        param_info["default"] = default_val
                    except (TypeError, ValueError):
                        pass  # Skip non-serializable defaults
                params.append(param_info)

            # Path parameters
            for param in getattr(route.dependant, "path_params", []):
                params.append({
                    "name": param.name,
                    "in": "path",
                    "required": True,
                })

        # Extract docstring and examples
        endpoint = getattr(route, "endpoint", None)
        docstring = ""
        examples = []
        if endpoint and endpoint.__doc__:
            doc_lines = endpoint.__doc__.strip().split('\n')
            # First line is summary, rest is description
            doc_parts = []
            in_examples = False
            for line in doc_lines[1:]:  # Skip first line (summary)
                stripped = line.strip()
                if stripped.lower().startswith('example'):
                    in_examples = True
                    continue
                if in_examples:
                    if stripped.startswith('jira ') or stripped.startswith('skills-client '):
                        examples.append(stripped)
                    elif stripped and not stripped.startswith('#'):
                        # Non-empty, non-comment line ends examples section
                        if not stripped.startswith('-'):
                            in_examples = False
                else:
                    doc_parts.append(line.rstrip())
            docstring = '\n'.join(doc_parts).strip()

        # Generate usage hint
        required_params = [p["name"] for p in params if p.get("required") and p.get("in") == "query"]
        path_params = [p["name"] for p in params if p.get("in") == "path"]
        usage_parts = [f"jira {command}"]
        for pp in path_params:
            usage_parts.append(f"<{pp}>")
        for rp in required_params:
            usage_parts.append(f"--{rp} <value>")
        usage = " ".join(usage_parts)

        return {
            "plugin": plugin.name,
            "command": command,
            "path": f"/{plugin.name}{route.path}",
            "summary": getattr(route, "summary", "") or route.name or command,
            "description": docstring or getattr(route, "description", "") or "",
            "methods": list(getattr(route, "methods", ["GET"])),
            "parameters": params,
            "usage": usage,
            "examples": examples,
        }

    # Command not found
    available = []
    for route in plugin.router.routes:
        if hasattr(route, "path"):
            path_parts = route.path.strip("/").split("/")
            name = path_parts[0] if path_parts[0] else "root"
            if not name.startswith("_"):
                available.append(name)

    return {"error": f"Unknown command: {command}", "available": list(set(available))}


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
