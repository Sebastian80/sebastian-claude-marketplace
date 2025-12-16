"""
Plugin Protocol - Contract for bridge plugins.

Plugins extend the bridge with new capabilities:
- Jira integration
- Confluence integration
- Serena (PHP LSP)
- Custom tools
"""

from typing import Any, Protocol, runtime_checkable

from fastapi import APIRouter


@runtime_checkable
class PluginProtocol(Protocol):
    """Contract for bridge plugins.

    Plugins provide:
    - A FastAPI router with endpoints
    - Lifecycle hooks (startup, shutdown)
    - Health check capability

    Example:
        class JiraPlugin:
            @property
            def name(self) -> str:
                return "jira"

            @property
            def router(self) -> APIRouter:
                return self._router

            async def startup(self) -> None:
                # Initialize Jira client
                ...
    """

    @property
    def name(self) -> str:
        """Plugin identifier.

        Used as URL prefix: /{name}/...
        Must be unique across all plugins.
        """
        ...

    @property
    def version(self) -> str:
        """Plugin version string."""
        ...

    @property
    def description(self) -> str:
        """Short description for /plugins endpoint."""
        ...

    @property
    def router(self) -> APIRouter:
        """FastAPI router with all plugin endpoints.

        Router is mounted at /{plugin.name}/
        """
        ...

    async def startup(self) -> None:
        """Called on bridge startup.

        Initialize resources:
        - Register connectors with connector_registry
        - Load configuration
        """
        ...

    async def shutdown(self) -> None:
        """Called on bridge shutdown.

        Cleanup resources:
        - Unregister connectors
        """
        ...

    async def health_check(self) -> dict[str, Any]:
        """Return plugin health status.

        Called by /health endpoint.

        Returns:
            Dict with at least 'status' key ('ok', 'degraded', 'error')
        """
        ...
