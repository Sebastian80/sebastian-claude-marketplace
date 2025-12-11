"""
Tests for daemon health and Jira plugin connection.

Endpoints tested:
- skills-client health - Daemon health
- GET /health - Jira plugin health

Cross-cutting tests that verify the skills daemon and Jira plugin are operational.
"""

import pytest

from helpers import run_cli, run_cli_raw, get_data


class TestDaemonHealth:
    """Test daemon health endpoints."""

    def test_daemon_health(self):
        """Daemon should be running and healthy."""
        result = run_cli("health")
        assert result.get("status") == "running"
        assert "jira" in result.get("plugins", [])

    def test_jira_plugin_connected(self):
        """Jira plugin should be connected."""
        result = run_cli("health")
        jira_health = result.get("plugin_health", {}).get("jira", {})
        assert jira_health.get("status") in ("connected", "reconnected")

    def test_plugins_list(self):
        """Should list jira in available plugins."""
        result = run_cli("plugins")
        plugin_names = [p["name"] for p in result.get("plugins", [])]
        assert "jira" in plugin_names


class TestJiraHealth:
    """Test Jira plugin /health endpoint."""

    def test_jira_health_basic(self):
        """Should return Jira connection health."""
        result = run_cli("jira", "health")
        data = get_data(result)
        assert data.get("status") == "healthy"
        assert data.get("connected") is True

    def test_jira_health_user_info(self):
        """Health should include user info."""
        result = run_cli("jira", "health")
        data = get_data(result)
        assert "user" in data
        assert data.get("user") is not None

    def test_jira_health_server_info(self):
        """Health should include server URL."""
        result = run_cli("jira", "health")
        data = get_data(result)
        assert "server" in data
        assert "jira" in data.get("server", "").lower()

    def test_jira_health_formats(self):
        """Should support multiple output formats."""
        for fmt in ["json", "human", "ai", "markdown"]:
            stdout, stderr, code = run_cli_raw("jira", "health", "--format", fmt)
            assert code == 0


class TestPluginHelp:
    """Test plugin-level help system."""

    def test_plugin_help(self):
        """Should show plugin-level help."""
        stdout, stderr, code = run_cli_raw("jira", "--help")
        assert "jira" in stdout.lower()
        assert code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
