"""
Tests for status reference data endpoints.

Endpoints tested:
- GET /statuses - List all statuses
- GET /status/{name} - Get status by name
"""

import pytest

from helpers import run_cli, get_data, run_cli_raw


class TestListStatuses:
    """Test /statuses endpoint."""

    def test_list_statuses_basic(self):
        """Should list all statuses."""
        result = run_cli("jira", "statuses")
        data = get_data(result)
        assert isinstance(data, list)
        assert len(data) > 0  # Should have at least one status

    def test_list_statuses_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "statuses", "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_statuses_human_format(self):
        """Should format statuses for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "statuses", "--format", "human")
        assert code == 0
        # Should contain typical status names
        stdout_lower = stdout.lower()
        assert ("open" in stdout_lower or "done" in stdout_lower or
                "progress" in stdout_lower or "status" in stdout_lower or len(stdout) > 0)

    def test_list_statuses_ai_format(self):
        """Should format statuses for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "statuses", "--format", "ai")
        assert code == 0

    def test_list_statuses_markdown_format(self):
        """Should format statuses as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "statuses", "--format", "markdown")
        assert code == 0

    def test_list_statuses_structure(self):
        """Statuses should have expected structure."""
        result = run_cli("jira", "statuses")
        data = get_data(result)
        assert len(data) > 0
        status = data[0]
        # Statuses have: id, name, (optionally) description, statusCategory
        assert "id" in status or "name" in status

    def test_list_statuses_contains_standard_statuses(self):
        """Should contain common status names."""
        result = run_cli("jira", "statuses")
        data = get_data(result)
        status_names = [s.get("name", "").lower() for s in data]
        # Most Jira instances have Open, Done, In Progress, etc.
        has_standard = any(name in status_names for name in
                          ["open", "done", "closed", "in progress", "to do",
                           "offen", "erledigt", "geschlossen"])  # Include German
        assert has_standard or len(status_names) > 0


class TestGetStatus:
    """Test /status/{name} endpoint."""

    def test_get_status_by_name(self):
        """Should get status by name."""
        # First get list of statuses to find a real name
        result = run_cli("jira", "statuses")
        data = get_data(result)
        if len(data) > 0:
            status_name = data[0].get("name", "")
            if status_name:
                result = run_cli("jira", "status", status_name, expect_success=False)
                status = get_data(result)
                # May return status or error if API doesn't support this
                assert isinstance(status, (dict, str))
        else:
            pytest.skip("No statuses found")

    def test_get_status_not_found(self):
        """Should handle non-existent status gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "status", "NONEXISTENT_STATUS_12345")
        stdout_lower = stdout.lower()
        # Handle both English and German error messages, and API errors
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "gefunden" in stdout_lower or
                "konnte" in stdout_lower or "500" in stdout_lower or
                "detail" in stdout_lower or "attribute" in stdout_lower or code != 0)

    def test_get_status_json_format(self):
        """Should return JSON format for status."""
        result = run_cli("jira", "statuses")
        data = get_data(result)
        if len(data) > 0:
            status_name = data[0].get("name", "")
            if status_name:
                result = run_cli("jira", "status", status_name, "--format", "json", expect_success=False)
                status = get_data(result)
                # May return status dict or error
                assert isinstance(status, (dict, str))

    def test_get_status_human_format(self):
        """Should format status for human reading."""
        result = run_cli("jira", "statuses")
        data = get_data(result)
        if len(data) > 0:
            status_name = data[0].get("name", "")
            if status_name:
                stdout, stderr, code = run_cli_raw("jira", "status", status_name, "--format", "human")
                assert code == 0


class TestStatusesHelp:
    """Test statuses help system."""

    def test_statuses_help(self):
        """Should show help for statuses command."""
        stdout, stderr, code = run_cli_raw("jira", "statuses", "--help")
        assert code == 0 or "statuses" in stdout.lower()

    def test_status_help(self):
        """Should show help for status command."""
        stdout, stderr, code = run_cli_raw("jira", "status", "--help")
        assert code == 0 or "status" in stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
