"""
Connector Protocol - Contract for external service connections.

Connectors wrap HTTP clients with:
- Circuit breaker protection
- Health monitoring
- Automatic reconnection
- Connection pooling
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConnectorProtocol(Protocol):
    """Contract for external service connectors.

    Implementations must provide HTTP methods with circuit breaker protection
    and health monitoring capabilities.

    Example:
        class JiraConnector:
            @property
            def name(self) -> str:
                return "jira"

            async def get(self, path: str, **kwargs) -> Any:
                return await self._client.get(path, **kwargs)
    """

    @property
    def name(self) -> str:
        """Unique connector identifier.

        Used for registration and lookup in ConnectorRegistry.
        """
        ...

    @property
    def healthy(self) -> bool:
        """Current health status.

        True if the service is reachable and responding.
        Updated by background health checks.
        """
        ...

    @property
    def circuit_state(self) -> str:
        """Current circuit breaker state.

        Returns one of: 'closed', 'open', 'half_open'
        """
        ...

    async def get(self, path: str, **kwargs: Any) -> Any:
        """HTTP GET request with circuit breaker protection.

        Args:
            path: URL path (appended to base_url)
            **kwargs: Additional arguments passed to httpx

        Returns:
            Response data (usually dict or list)

        Raises:
            ConnectorUnavailable: If circuit is open or service unreachable
        """
        ...

    async def post(self, path: str, **kwargs: Any) -> Any:
        """HTTP POST request with circuit breaker protection.

        Args:
            path: URL path (appended to base_url)
            **kwargs: Additional arguments passed to httpx (json, data, etc.)

        Returns:
            Response data

        Raises:
            ConnectorUnavailable: If circuit is open or service unreachable
        """
        ...

    async def put(self, path: str, **kwargs: Any) -> Any:
        """HTTP PUT request with circuit breaker protection."""
        ...

    async def delete(self, path: str, **kwargs: Any) -> Any:
        """HTTP DELETE request with circuit breaker protection."""
        ...

    async def check_health(self) -> bool:
        """Verify service is reachable.

        Called by background health monitor.
        Should be fast (short timeout).

        Returns:
            True if health check passed
        """
        ...

    async def connect(self) -> None:
        """Establish connection and initialize client.

        Called on startup and after reconnection.
        Should create httpx client, set up auth, etc.
        """
        ...

    async def disconnect(self) -> None:
        """Clean shutdown.

        Called on bridge shutdown.
        Should close httpx client, release resources.
        """
        ...

    def status(self) -> dict[str, Any]:
        """Current connector status for health endpoint.

        Returns:
            Dict with keys: name, healthy, circuit_state, base_url, etc.
        """
        ...


class ConnectorUnavailable(Exception):
    """Raised when connector cannot handle request.

    Reasons:
    - Circuit breaker is open
    - Service is unreachable
    - Connection not established
    """

    def __init__(self, connector_name: str, reason: str):
        self.connector_name = connector_name
        self.reason = reason
        super().__init__(f"Connector '{connector_name}' unavailable: {reason}")
