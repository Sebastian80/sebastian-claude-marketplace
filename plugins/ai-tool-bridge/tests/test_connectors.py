"""Tests for connector registry."""

import pytest

from ai_tool_bridge.connectors import ConnectorRegistry


class MockConnector:
    """Mock connector for testing."""

    def __init__(self, name: str, healthy: bool = True):
        self.name = name
        self._healthy = healthy
        self._connected = False

    @property
    def healthy(self) -> bool:
        return self._healthy and self._connected

    @property
    def circuit_state(self) -> str:
        return "closed"

    async def connect(self):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    def status(self) -> dict:
        return {
            "name": self.name,
            "healthy": self.healthy,
            "circuit_state": self.circuit_state,
        }


class TestConnectorRegistry:
    """Test connector registry operations."""

    def test_register_connector(self):
        """Can register a connector."""
        registry = ConnectorRegistry()
        connector = MockConnector("test")

        registry.register(connector)

        assert registry.get_optional("test") is connector
        assert len(registry.names()) == 1

    def test_get_connector(self):
        """Can retrieve registered connector."""
        registry = ConnectorRegistry()
        connector = MockConnector("test")
        registry.register(connector)

        result = registry.get("test")

        assert result is connector

    def test_get_unknown_raises_keyerror(self):
        """Getting unknown connector raises KeyError."""
        registry = ConnectorRegistry()

        with pytest.raises(KeyError):
            registry.get("unknown")

    def test_get_optional_unknown_returns_none(self):
        """Getting unknown connector via get_optional returns None."""
        registry = ConnectorRegistry()

        result = registry.get_optional("unknown")

        assert result is None

    def test_unregister_connector(self):
        """Can unregister a connector."""
        registry = ConnectorRegistry()
        connector = MockConnector("test")
        registry.register(connector)

        result = registry.unregister("test")

        assert result is connector
        assert registry.get_optional("test") is None

    def test_unregister_unknown_returns_none(self):
        """Unregistering unknown connector returns None."""
        registry = ConnectorRegistry()

        result = registry.unregister("unknown")

        assert result is None

    def test_duplicate_register_raises(self):
        """Registering duplicate name raises ValueError."""
        registry = ConnectorRegistry()
        connector1 = MockConnector("test")
        connector2 = MockConnector("test")

        registry.register(connector1)

        with pytest.raises(ValueError):
            registry.register(connector2)

    @pytest.mark.asyncio
    async def test_connect_all(self):
        """Connect all registered connectors."""
        registry = ConnectorRegistry()
        c1 = MockConnector("c1")
        c2 = MockConnector("c2")
        registry.register(c1)
        registry.register(c2)

        await registry.connect_all()

        assert c1._connected
        assert c2._connected

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """Disconnect all registered connectors."""
        registry = ConnectorRegistry()
        c1 = MockConnector("c1")
        c2 = MockConnector("c2")
        registry.register(c1)
        registry.register(c2)
        await registry.connect_all()

        await registry.disconnect_all()

        assert not c1._connected
        assert not c2._connected

    def test_status(self):
        """Status returns dict of all connector statuses."""
        registry = ConnectorRegistry()
        registry.register(MockConnector("c1"))
        registry.register(MockConnector("c2"))

        status = registry.status()

        assert "connectors" in status
        assert "c1" in status["connectors"]
        assert "c2" in status["connectors"]
        assert status["total"] == 2

    def test_names(self):
        """Names returns list of connector names."""
        registry = ConnectorRegistry()
        registry.register(MockConnector("c1"))
        registry.register(MockConnector("c2"))

        names = registry.names()

        assert "c1" in names
        assert "c2" in names

    def test_all(self):
        """All returns list of all connectors."""
        registry = ConnectorRegistry()
        c1 = MockConnector("c1")
        c2 = MockConnector("c2")
        registry.register(c1)
        registry.register(c2)

        connectors = registry.all()

        assert c1 in connectors
        assert c2 in connectors

    def test_clear(self):
        """Clear removes all connectors."""
        registry = ConnectorRegistry()
        registry.register(MockConnector("c1"))
        registry.register(MockConnector("c2"))

        removed = registry.clear()

        assert "c1" in removed
        assert "c2" in removed
        assert len(registry.names()) == 0
