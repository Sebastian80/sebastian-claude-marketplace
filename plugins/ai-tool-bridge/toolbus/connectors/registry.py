"""
Connector Registry - Manages all registered connectors.

Plugins register their connectors here during startup.
The registry provides:
- Connector lookup by name
- Status aggregation for health endpoint
- Lifecycle management (connect/disconnect all)
"""

from typing import Any

from ..contracts import ConnectorProtocol

__all__ = ["ConnectorRegistry", "connector_registry"]


class ConnectorRegistry:
    """Registry for external service connectors.

    Example:
        registry = ConnectorRegistry()

        # Plugin registers its connector
        registry.register(jira_connector)

        # Later, get connector by name
        jira = registry.get("jira")
        response = await jira.get("/rest/api/2/issue/PROJ-123")
    """

    def __init__(self) -> None:
        self._connectors: dict[str, ConnectorProtocol] = {}

    def register(self, connector: ConnectorProtocol) -> None:
        """Register a connector.

        Args:
            connector: Connector instance implementing ConnectorProtocol

        Raises:
            ValueError: If connector with same name already registered
        """
        if connector.name in self._connectors:
            raise ValueError(f"Connector already registered: {connector.name}")
        self._connectors[connector.name] = connector

    def unregister(self, name: str) -> ConnectorProtocol | None:
        """Unregister a connector by name.

        Returns:
            The removed connector, or None if not found
        """
        return self._connectors.pop(name, None)

    def get(self, name: str) -> ConnectorProtocol:
        """Get connector by name.

        Args:
            name: Connector identifier

        Returns:
            Connector instance

        Raises:
            KeyError: If connector not found
        """
        if name not in self._connectors:
            raise KeyError(f"Unknown connector: {name}")
        return self._connectors[name]

    def get_optional(self, name: str) -> ConnectorProtocol | None:
        """Get connector by name, or None if not found."""
        return self._connectors.get(name)

    def all(self) -> list[ConnectorProtocol]:
        """Get all registered connectors."""
        return list(self._connectors.values())

    def names(self) -> list[str]:
        """Get all connector names."""
        return list(self._connectors.keys())

    def clear(self) -> list[str]:
        """Clear all connectors. Returns removed names."""
        names = list(self._connectors.keys())
        self._connectors.clear()
        return names

    async def connect_all(self) -> dict[str, Exception | None]:
        """Connect all registered connectors in parallel.

        Returns:
            Dict mapping connector name to exception (None if success)
        """
        import asyncio

        async def connect_one(
            name: str, connector: ConnectorProtocol
        ) -> tuple[str, Exception | None]:
            try:
                await connector.connect()
                return (name, None)
            except Exception as e:
                return (name, e)

        tasks = [connect_one(n, c) for n, c in self._connectors.items()]
        results_list = await asyncio.gather(*tasks)
        return dict(results_list)

    async def disconnect_all(self) -> None:
        """Disconnect all registered connectors."""
        for connector in self._connectors.values():
            try:
                await connector.disconnect()
            except Exception:
                pass  # Best effort cleanup

    def status(self) -> dict[str, Any]:
        """Aggregated status of all connectors."""
        connector_status = {
            name: connector.status()
            for name, connector in self._connectors.items()
        }

        all_healthy = all(
            s.get("healthy", False) for s in connector_status.values()
        ) if connector_status else True
        any_healthy = any(
            s.get("healthy", False) for s in connector_status.values()
        ) if connector_status else True

        return {
            "status": "healthy" if all_healthy else ("degraded" if any_healthy else "unhealthy"),
            "total": len(self._connectors),
            "healthy_count": sum(1 for s in connector_status.values() if s.get("healthy")),
            "connectors": connector_status,
        }


# Global registry instance
connector_registry = ConnectorRegistry()
