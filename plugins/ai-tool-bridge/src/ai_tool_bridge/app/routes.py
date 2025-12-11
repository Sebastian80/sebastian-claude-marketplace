"""
Core Routes - Health, status, and management endpoints.

These routes are always available regardless of loaded plugins.
Plugin routes are mounted dynamically at /{plugin_name}/...
"""

from typing import Any

from fastapi import APIRouter

from ..connectors import connector_registry
from ..plugins import plugin_registry

router = APIRouter(tags=["core"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Basic health check.

    Always returns 200 if the server is running.
    Use /ready for deeper health checks.
    """
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, Any]:
    """Readiness check including plugin health.

    Returns 200 if all critical components are healthy.
    Used by load balancers and orchestrators.
    """
    plugin_health = await plugin_registry.health_status()
    connector_health = connector_registry.status()

    all_healthy = all(
        p.get("status") == "healthy" for p in plugin_health.values()
    )

    return {
        "status": "ready" if all_healthy else "degraded",
        "plugins": plugin_health,
        "connectors": connector_health,
    }


@router.get("/status")
async def status() -> dict[str, Any]:
    """Detailed status information.

    Returns comprehensive information about the bridge
    and all loaded components.
    """
    from .. import __version__

    return {
        "version": __version__,
        "plugins": plugin_registry.list_plugins(),
        "connectors": connector_registry.status(),
    }


@router.get("/plugins")
async def list_plugins() -> list[dict[str, Any]]:
    """List all registered plugins."""
    return plugin_registry.list_plugins()


@router.get("/plugins/{name}")
async def get_plugin(name: str) -> dict[str, Any]:
    """Get details about a specific plugin."""
    plugin = plugin_registry.get(name)
    if not plugin:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    health = await plugin_registry.health_check(name)

    return {
        "name": plugin.name,
        "version": plugin.version,
        "description": plugin.description,
        "health": health,
    }


@router.get("/connectors")
async def list_connectors() -> dict[str, Any]:
    """List all registered connectors and their status."""
    return connector_registry.status()


@router.post("/connectors/{name}/reconnect")
async def reconnect_connector(name: str) -> dict[str, Any]:
    """Force reconnection of a specific connector."""
    connector = connector_registry.get(name)
    if not connector:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Connector '{name}' not found")

    await connector.disconnect()
    await connector.connect()

    return {"status": "reconnected", "connector": name}
