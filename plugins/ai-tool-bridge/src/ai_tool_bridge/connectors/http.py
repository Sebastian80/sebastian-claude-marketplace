"""
HTTP Connector - Default implementation of ConnectorProtocol.

Features:
- Circuit breaker protection
- Connection pooling via httpx
- Configurable timeouts
- Authentication support
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..contracts import ConnectorUnavailable
from .circuit import CircuitBreaker


@dataclass
class ConnectorConfig:
    """Configuration for an HTTP connector."""

    name: str
    base_url: str
    health_endpoint: str = "/health"
    timeout: float = 30.0
    pool_size: int = 10
    health_check_interval: float = 10.0

    # Circuit breaker settings
    failure_threshold: int = 5
    reset_timeout: float = 30.0

    # Authentication (optional)
    auth: httpx.Auth | None = None
    headers: dict[str, str] = field(default_factory=dict)


class HTTPConnector:
    """HTTP connector with circuit breaker protection.

    Implements ConnectorProtocol.

    Example:
        config = ConnectorConfig(
            name="jira",
            base_url="https://company.atlassian.net",
            health_endpoint="/rest/api/2/myself",
            auth=httpx.BasicAuth(user, token),
        )
        connector = HTTPConnector(config)
        await connector.connect()

        response = await connector.get("/rest/api/2/issue/PROJ-123")
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._circuit = CircuitBreaker(
            failure_threshold=config.failure_threshold,
            reset_timeout=config.reset_timeout,
        )
        self._healthy = False
        self._last_health_check: float = 0
        self._consecutive_failures: int = 0
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        """Connector identifier."""
        return self.config.name

    @property
    def healthy(self) -> bool:
        """Current health status."""
        return self._healthy

    @property
    def circuit_state(self) -> str:
        """Current circuit breaker state."""
        return self._circuit.state.value

    async def connect(self) -> None:
        """Initialize HTTP client."""
        async with self._lock:
            if self._client:
                await self._client.aclose()

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout),
                limits=httpx.Limits(
                    max_connections=self.config.pool_size,
                    max_keepalive_connections=self.config.pool_size,
                    keepalive_expiry=30.0,
                ),
                auth=self.config.auth,
                headers=self.config.headers,
                follow_redirects=True,
            )

    async def disconnect(self) -> None:
        """Close HTTP client."""
        async with self._lock:
            if self._client:
                await self._client.aclose()
                self._client = None
        self._healthy = False

    async def check_health(self) -> bool:
        """Check if service is reachable."""
        if not self._client:
            return False

        try:
            response = await self._client.get(
                self.config.health_endpoint,
                timeout=httpx.Timeout(5.0),
            )
            return response.status_code < 500
        except Exception:
            return False

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make HTTP request with circuit breaker protection."""
        if not self._circuit.can_execute():
            raise ConnectorUnavailable(
                self.name,
                f"Circuit breaker is {self._circuit.state.value}",
            )

        if not self._client:
            raise ConnectorUnavailable(self.name, "Not connected")

        try:
            response = await self._client.request(method, path, **kwargs)

            # 5xx = server error, count as failure
            if response.status_code >= 500:
                self._circuit.record_failure()
                raise ConnectorUnavailable(
                    self.name,
                    f"Server error: {response.status_code}",
                )

            self._circuit.record_success()
            return response

        except httpx.TimeoutException as e:
            self._circuit.record_failure()
            raise ConnectorUnavailable(self.name, f"Timeout: {e}") from e

        except httpx.ConnectError as e:
            self._circuit.record_failure()
            raise ConnectorUnavailable(self.name, f"Connection error: {e}") from e

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """HTTP GET request."""
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """HTTP POST request."""
        return await self._request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """HTTP PUT request."""
        return await self._request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """HTTP DELETE request."""
        return await self._request("DELETE", path, **kwargs)

    def status(self) -> dict[str, Any]:
        """Current connector status."""
        return {
            "name": self.name,
            "base_url": self.config.base_url,
            "healthy": self._healthy,
            "connected": self._client is not None,
            "circuit": self._circuit.status(),
        }
