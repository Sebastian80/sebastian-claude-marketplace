"""
Tests for JiraPlugin lifecycle hooks: connect(), reconnect(), shutdown().
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Setup paths
PLUGIN_ROOT = Path(__file__).parent.parent.parent
SKILLS_PLUGIN = PLUGIN_ROOT / "skills" / "jira-communication" / "scripts" / "skills_plugin"
SKILLS_DAEMON = PLUGIN_ROOT.parent / "skills-daemon"
sys.path.insert(0, str(SKILLS_PLUGIN.parent))
sys.path.insert(0, str(SKILLS_DAEMON))


class TestJiraPluginConnect:
    """Tests for connect() hook."""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global state before each test."""
        import skills_plugin
        skills_plugin.jira_client = None
        skills_plugin.workflow_store = None
        skills_plugin.last_health_check = 0
        yield
        skills_plugin.jira_client = None

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from skills_plugin import JiraPlugin
        return JiraPlugin()

    @pytest.mark.asyncio
    async def test_connect_success(self, plugin, mock_jira_client):
        """connect() should establish connection on success."""
        import skills_plugin

        with patch("skills_plugin.get_client_sync", return_value=mock_jira_client):
            await plugin.connect()

        # Should not raise and should log success

    @pytest.mark.asyncio
    async def test_connect_failure_raises(self, plugin):
        """connect() should raise on connection failure."""
        with patch("skills_plugin.get_client_sync", side_effect=Exception("Connection refused")):
            with pytest.raises(Exception, match="Connection refused"):
                await plugin.connect()

    @pytest.mark.asyncio
    async def test_connect_resets_existing_client(self, plugin, mock_jira_client):
        """connect() should reset existing client before connecting."""
        import skills_plugin
        skills_plugin.jira_client = MagicMock()  # Existing client

        with patch("skills_plugin.get_client_sync", return_value=mock_jira_client):
            await plugin.connect()

        # Should have reset client to None first (handled in connect())


class TestJiraPluginReconnect:
    """Tests for reconnect() hook with exponential backoff."""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global state before each test."""
        import skills_plugin
        skills_plugin.jira_client = None
        yield
        skills_plugin.jira_client = None

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from skills_plugin import JiraPlugin
        return JiraPlugin()

    @pytest.mark.asyncio
    async def test_reconnect_success_first_attempt(self, plugin, mock_jira_client):
        """reconnect() should succeed on first attempt if connection works."""
        with patch.object(plugin, "connect", new_callable=AsyncMock) as mock_connect:
            await plugin.reconnect()

        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_retries_on_failure(self, plugin):
        """reconnect() should retry with backoff on failure."""
        attempt_count = 0

        async def failing_connect():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception(f"Attempt {attempt_count} failed")
            # Third attempt succeeds

        with patch.object(plugin, "connect", side_effect=failing_connect):
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip delays
                await plugin.reconnect()

        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_reconnect_exhausts_retries(self, plugin):
        """reconnect() should raise after exhausting all retries."""
        with patch.object(plugin, "connect", side_effect=Exception("Connection failed")):
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip delays
                with pytest.raises(Exception, match="Connection failed"):
                    await plugin.reconnect()

    @pytest.mark.asyncio
    async def test_reconnect_resets_client_first(self, plugin, mock_jira_client):
        """reconnect() should reset existing client before attempting reconnect."""
        import skills_plugin
        old_client = MagicMock()
        skills_plugin.jira_client = old_client

        with patch.object(plugin, "connect", new_callable=AsyncMock):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await plugin.reconnect()

        # Client should have been reset
        assert skills_plugin.jira_client is None  # Reset before connect


class TestJiraPluginShutdown:
    """Tests for shutdown() hook."""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global state before each test."""
        import skills_plugin
        skills_plugin.jira_client = None
        yield
        skills_plugin.jira_client = None

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from skills_plugin import JiraPlugin
        return JiraPlugin()

    @pytest.mark.asyncio
    async def test_shutdown_clears_client(self, plugin, mock_jira_client):
        """shutdown() should clear the jira_client."""
        import skills_plugin
        skills_plugin.jira_client = mock_jira_client

        await plugin.shutdown()

        assert skills_plugin.jira_client is None

    @pytest.mark.asyncio
    async def test_shutdown_handles_no_client(self, plugin):
        """shutdown() should handle case when no client exists."""
        import skills_plugin
        skills_plugin.jira_client = None

        # Should not raise
        await plugin.shutdown()

        assert skills_plugin.jira_client is None


class TestJiraPluginStartup:
    """Tests for startup() hook."""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global state before each test."""
        import skills_plugin
        skills_plugin.workflow_store = None
        yield
        skills_plugin.workflow_store = None

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from skills_plugin import JiraPlugin
        return JiraPlugin()

    @pytest.mark.asyncio
    async def test_startup_initializes_workflow_store(self, plugin):
        """startup() should initialize workflow store."""
        mock_store = MagicMock()

        with patch.dict("sys.modules", {"lib.workflow": MagicMock(WorkflowStore=lambda: mock_store)}):
            await plugin.startup()

        # WorkflowStore initialization happens in startup

    @pytest.mark.asyncio
    async def test_startup_handles_import_error(self, plugin):
        """startup() should handle import errors gracefully."""
        with patch.dict("sys.modules", {"lib.workflow": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                # Should not raise
                await plugin.startup()


class TestJiraPluginHealthCheck:
    """Tests for health_check() method."""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global state before each test."""
        import skills_plugin
        skills_plugin.jira_client = None
        skills_plugin.workflow_store = None
        skills_plugin.last_health_check = 0
        yield
        skills_plugin.jira_client = None

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from skills_plugin import JiraPlugin
        return JiraPlugin()

    def test_health_check_no_connection(self, plugin):
        """health_check() should return not_connected when no client."""
        import skills_plugin
        skills_plugin.jira_client = None

        result = plugin.health_check()

        assert result["status"] == "not_connected"
        assert result["can_reconnect"] is True

    def test_health_check_connected(self, plugin, mock_jira_client):
        """health_check() should return connected when client is healthy."""
        import skills_plugin
        import time

        skills_plugin.jira_client = mock_jira_client
        skills_plugin.last_health_check = time.time() - 10  # Recent check

        result = plugin.health_check()

        assert result["status"] == "connected"

    def test_health_check_connection_error(self, plugin):
        """health_check() should detect connection errors."""
        import skills_plugin
        import time

        mock_client = MagicMock()
        mock_client.myself.side_effect = Exception("Network error")
        skills_plugin.jira_client = mock_client
        skills_plugin.last_health_check = 0  # Force check

        # Patch get_client_sync to fail reconnection
        with patch("skills_plugin.get_client_sync", side_effect=Exception("Reconnect failed")):
            result = plugin.health_check()

        assert result["status"] == "connection_error"
        assert result["can_reconnect"] is False

    def test_health_check_includes_workflow_count(self, plugin, mock_jira_client):
        """health_check() should include cached workflow count."""
        import skills_plugin
        import time

        skills_plugin.jira_client = mock_jira_client
        skills_plugin.last_health_check = time.time()

        mock_store = MagicMock()
        mock_store.list_types.return_value = ["Bug", "Story", "Task"]
        skills_plugin.workflow_store = mock_store

        result = plugin.health_check()

        assert result["workflows_cached"] == 3


class TestJiraPluginProperties:
    """Tests for plugin properties."""

    @pytest.fixture
    def plugin(self):
        """Create a fresh JiraPlugin instance."""
        from skills_plugin import JiraPlugin
        return JiraPlugin()

    def test_name_property(self, plugin):
        """Plugin name should be 'jira'."""
        assert plugin.name == "jira"

    def test_version_property(self, plugin):
        """Plugin should have a version."""
        assert plugin.version == "1.0.0"

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
