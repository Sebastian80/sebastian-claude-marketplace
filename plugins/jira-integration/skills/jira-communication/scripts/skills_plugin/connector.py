"""
JiraConnector - Bridge connector wrapping atlassian.Jira client.

Implements ConnectorProtocol to integrate with ai-tool-bridge:
- Lifecycle management (connect/disconnect)
- Health monitoring
- Circuit breaker state tracking
- Registration with connector_registry
"""

import logging
import time
from typing import Any

logger = logging.getLogger("jira_plugin")


class JiraConnector:
    """Connector wrapping atlassian.Jira client.

    Implements ConnectorProtocol for bridge integration while
    preserving the atlassian library's high-level API.

    Usage:
        connector = JiraConnector()
        await connector.connect()

        # Access underlying client
        issues = connector.client.search_issues("project = PROJ")

        # Check health
        if connector.healthy:
            ...
    """

    def __init__(self) -> None:
        self._client = None
        self._healthy = False
        self._circuit_state = "closed"
        self._failure_count = 0
        self._last_failure_time = 0
        self._base_url = ""

        # Circuit breaker config
        self._failure_threshold = 5
        self._reset_timeout = 30.0

    @property
    def name(self) -> str:
        """Unique connector identifier."""
        return "jira"

    @property
    def healthy(self) -> bool:
        """Current health status."""
        return self._healthy and self._client is not None

    @property
    def circuit_state(self) -> str:
        """Current circuit breaker state: closed, open, half_open."""
        # Check if we should transition from open to half_open
        if self._circuit_state == "open":
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._circuit_state = "half_open"
        return self._circuit_state

    @property
    def client(self):
        """Access underlying atlassian.Jira client.

        Returns:
            Jira client instance or None if not connected

        Raises:
            RuntimeError: If circuit breaker is open
        """
        if self.circuit_state == "open":
            raise RuntimeError(f"Circuit breaker open for {self.name}")
        return self._client

    async def connect(self) -> None:
        """Initialize Jira client connection."""
        try:
            from lib.client import get_jira_client

            self._client = get_jira_client()
            self._base_url = getattr(self._client, "url", "")

            # Verify connection
            self._client.myself()

            self._healthy = True
            self._circuit_state = "closed"
            self._failure_count = 0
            logger.info("Jira connector connected", extra={"url": self._base_url})

        except Exception as e:
            self._healthy = False
            self._record_failure()
            logger.error(f"Jira connector failed to connect: {e}")
            raise

    async def disconnect(self) -> None:
        """Clean shutdown."""
        self._client = None
        self._healthy = False
        logger.info("Jira connector disconnected")

    async def check_health(self) -> bool:
        """Verify Jira is reachable."""
        if self._client is None:
            return False

        try:
            self._client.myself()
            self._healthy = True

            # Successful health check resets circuit breaker
            if self._circuit_state == "half_open":
                self._circuit_state = "closed"
                self._failure_count = 0
                logger.info("Circuit breaker closed after successful health check")

            return True

        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self._healthy = False
            self._record_failure()
            return False

    def _record_failure(self) -> None:
        """Record a failure and potentially open circuit breaker."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self._failure_threshold:
            if self._circuit_state != "open":
                self._circuit_state = "open"
                logger.warning(
                    f"Circuit breaker opened after {self._failure_count} failures"
                )

    def status(self) -> dict[str, Any]:
        """Current connector status."""
        return {
            "name": self.name,
            "healthy": self.healthy,
            "circuit_state": self.circuit_state,
            "base_url": self._base_url,
            "failure_count": self._failure_count,
        }

    # HTTP method stubs - not used directly but required by protocol
    # Routes use self.client.method() instead

    async def get(self, path: str, **kwargs: Any) -> Any:
        """HTTP GET - use client methods instead."""
        raise NotImplementedError("Use connector.client methods directly")

    async def post(self, path: str, **kwargs: Any) -> Any:
        """HTTP POST - use client methods instead."""
        raise NotImplementedError("Use connector.client methods directly")

    async def put(self, path: str, **kwargs: Any) -> Any:
        """HTTP PUT - use client methods instead."""
        raise NotImplementedError("Use connector.client methods directly")

    async def delete(self, path: str, **kwargs: Any) -> Any:
        """HTTP DELETE - use client methods instead."""
        raise NotImplementedError("Use connector.client methods directly")
