"""
Tests for JiraPlugin lifecycle: startup(), shutdown(), health_check().
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Setup paths
PLUGIN_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PLUGIN_ROOT / "skills" / "jira" / "scripts"
AI_TOOL_BRIDGE = PLUGIN_ROOT.parent / "ai-tool-bridge" / "src"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(AI_TOOL_BRIDGE))


class TestJiraPluginStartup:
    """Tests for startup() hook."""

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from plugin import JiraPlugin
        return JiraPlugin()

    @pytest.mark.asyncio
    async def test_startup_connects_connector(self, plugin, mock_jira_client):
        """startup() should connect the connector."""
        with patch("lib.client.get_jira_client", return_value=mock_jira_client):
            await plugin.startup()

        assert plugin._connector._healthy is True

    @pytest.mark.asyncio
    async def test_startup_handles_connection_failure(self, plugin):
        """startup() should handle connection failure gracefully."""
        with patch("lib.client.get_jira_client", side_effect=Exception("Connection refused")):
            # Should not raise - logs warning instead
            await plugin.startup()

        assert plugin._connector._healthy is False


class TestJiraPluginShutdown:
    """Tests for shutdown() hook."""

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from plugin import JiraPlugin
        return JiraPlugin()

    @pytest.mark.asyncio
    async def test_shutdown_disconnects_connector(self, plugin, mock_jira_client):
        """shutdown() should disconnect the connector."""
        # First connect
        plugin._connector._client = mock_jira_client
        plugin._connector._healthy = True

        await plugin.shutdown()

        assert plugin._connector._client is None
        assert plugin._connector._healthy is False

    @pytest.mark.asyncio
    async def test_shutdown_handles_no_connection(self, plugin):
        """shutdown() should handle case when not connected."""
        plugin._connector._client = None
        plugin._connector._healthy = False

        # Should not raise
        await plugin.shutdown()


class TestJiraPluginHealthCheck:
    """Tests for health_check() method."""

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from plugin import JiraPlugin
        return JiraPlugin()

    def test_health_check_not_connected(self, plugin):
        """health_check() should return not_connected when connector unhealthy."""
        plugin._connector._client = None
        plugin._connector._healthy = False
        plugin._connector._circuit_state = "closed"

        result = plugin.health_check()

        assert result["status"] == "not_connected"
        assert result["can_reconnect"] is True

    def test_health_check_connected(self, plugin, mock_jira_client):
        """health_check() should return connected when connector healthy."""
        plugin._connector._client = mock_jira_client
        plugin._connector._healthy = True
        plugin._connector._circuit_state = "closed"

        result = plugin.health_check()

        assert result["status"] == "connected"
        assert result["circuit_state"] == "closed"

    def test_health_check_circuit_open(self, plugin):
        """health_check() should detect open circuit breaker."""
        plugin._connector._client = None
        plugin._connector._healthy = False
        plugin._connector._circuit_state = "open"
        plugin._connector._failure_count = 5
        plugin._connector._last_failure_time = time.time()

        result = plugin.health_check()

        assert result["status"] == "not_connected"
        assert result["circuit_state"] == "open"
        assert result["can_reconnect"] is False
        assert result["failure_count"] == 5


class TestJiraConnector:
    """Tests for JiraConnector."""

    @pytest.fixture
    def connector(self):
        """Create a fresh JiraConnector instance."""
        from connector import JiraConnector
        return JiraConnector()

    def test_name_property(self, connector):
        """Connector name should be 'jira'."""
        assert connector.name == "jira"

    def test_healthy_when_connected(self, connector, mock_jira_client):
        """healthy property should return True when connected."""
        connector._client = mock_jira_client
        connector._healthy = True

        assert connector.healthy is True

    def test_unhealthy_when_not_connected(self, connector):
        """healthy property should return False when not connected."""
        connector._client = None
        connector._healthy = False

        assert connector.healthy is False

    def test_client_raises_when_circuit_open(self, connector, mock_jira_client):
        """client property should raise when circuit breaker is open."""
        connector._client = mock_jira_client
        connector._circuit_state = "open"
        connector._last_failure_time = time.time()  # Keep circuit open

        with pytest.raises(RuntimeError, match="Circuit breaker open"):
            _ = connector.client

    @pytest.mark.asyncio
    async def test_connect_success(self, connector, mock_jira_client):
        """connect() should set client and healthy state."""
        with patch("lib.client.get_jira_client", return_value=mock_jira_client):
            await connector.connect()

        assert connector._client is mock_jira_client
        assert connector._healthy is True
        assert connector._circuit_state == "closed"

    @pytest.mark.asyncio
    async def test_connect_failure_increments_failure_count(self, connector):
        """connect() should increment failure count on error."""
        initial_count = connector._failure_count

        with patch("lib.client.get_jira_client", side_effect=Exception("Connection refused")):
            with pytest.raises(Exception):
                await connector.connect()

        assert connector._failure_count > initial_count
        assert connector._healthy is False

    @pytest.mark.asyncio
    async def test_disconnect_clears_state(self, connector, mock_jira_client):
        """disconnect() should clear client and set unhealthy."""
        connector._client = mock_jira_client
        connector._healthy = True

        await connector.disconnect()

        assert connector._client is None
        assert connector._healthy is False


class TestJiraPluginProperties:
    """Tests for plugin properties."""

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from plugin import JiraPlugin
        return JiraPlugin()

    def test_name_property(self, plugin):
        """Plugin name should be 'jira'."""
        assert plugin.name == "jira"

    def test_version_property(self, plugin):
        """Plugin should have a version."""
        assert plugin.version == "1.1.0"

    def test_description_property(self, plugin):
        """Plugin should have a description."""
        assert "Jira" in plugin.description

    def test_router_property(self, plugin):
        """Plugin should have a FastAPI router."""
        from fastapi import APIRouter
        assert isinstance(plugin.router, APIRouter)

    def test_router_has_routes(self, plugin):
        """Router should have defined routes."""
        router = plugin.router
        route_paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/issue/{key}" in route_paths
        assert "/search" in route_paths
        assert "/transitions/{key}" in route_paths

    def test_connector_property(self, plugin):
        """Plugin should expose connector."""
        from connector import JiraConnector
        assert isinstance(plugin.connector, JiraConnector)
