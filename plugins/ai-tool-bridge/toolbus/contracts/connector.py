"""
Connector Protocol - Contract for external service connections.

Defines the LIFECYCLE interface that the bridge needs to manage connectors.
Transport-specific methods (HTTP get/post, MCP calls, CLI execute) are
implemented by plugins - the bridge only manages lifecycle and health.

Connector types:
- HTTP APIs (Jira, Confluence) - plugins add get/post/put/delete
- MCP servers (Serena) - plugins expose .client
- CLI tools - plugins add execute()
- WebSocket - plugins add send/receive
"""

from typing import Any, Protocol, runtime_checkable

__all__ = ["ConnectorProtocol", "ConnectorUnavailableError"]


@runtime_checkable
class ConnectorProtocol(Protocol):
    """Lifecycle contract for external service connectors.

    The bridge uses this interface to:
    - Manage connection lifecycle (connect/disconnect all)
    - Monitor health across all services
    - Aggregate status for /connectors endpoint

    Transport-specific methods (HTTP, MCP, CLI) are NOT part of this
    protocol - plugins implement those separately.

    Example:
        class JiraConnector:
            @property
            def name(self) -> str:
                return "jira"

            @property
            def healthy(self) -> bool:
                return self._healthy

            @property
            def circuit_state(self) -> str:
                return self._circuit_state

            async def connect(self) -> None:
                self._client = httpx.AsyncClient(...)

            async def disconnect(self) -> None:
                await self._client.aclose()

            async def check_health(self) -> bool:
                response = await self._client.get("/health")
                return response.status_code == 200

            def status(self) -> dict[str, Any]:
                return {"name": self.name, "healthy": self.healthy, ...}

            # Transport-specific (NOT in protocol):
            async def get(self, path: str) -> Any: ...
            async def post(self, path: str, **kwargs) -> Any: ...
    """

    @property
    def name(self) -> str:
        """Unique connector identifier."""
        ...

    @property
    def healthy(self) -> bool:
        """Current health status."""
        ...

    @property
    def circuit_state(self) -> str:
        """Circuit breaker state: 'closed', 'open', or 'half_open'."""
        ...

    async def connect(self) -> None:
        """Establish connection. Called on startup."""
        ...

    async def disconnect(self) -> None:
        """Clean shutdown. Called on bridge shutdown."""
        ...

    async def check_health(self) -> bool:
        """Verify service is reachable. Returns True if healthy."""
        ...

    def status(self) -> dict[str, Any]:
        """Current status for health endpoint."""
        ...


class ConnectorUnavailableError(Exception):
    """Raised when connector cannot handle request."""

    def __init__(self, connector_name: str, reason: str):
        self.connector_name = connector_name
        self.reason = reason
        super().__init__(f"Connector '{connector_name}' unavailable: {reason}")
