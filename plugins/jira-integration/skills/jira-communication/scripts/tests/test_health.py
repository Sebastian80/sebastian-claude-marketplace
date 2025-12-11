"""
Tests for daemon health and plugin connection.

Cross-cutting tests that verify the skills daemon and Jira plugin are operational.
"""

import pytest

from helpers import run_cli, run_cli_raw


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


class TestPluginHelp:
    """Test plugin-level help system."""

    def test_plugin_help(self):
        """Should show plugin-level help."""
        stdout, stderr, code = run_cli_raw("jira", "--help")
        assert "jira" in stdout.lower()
        assert code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
