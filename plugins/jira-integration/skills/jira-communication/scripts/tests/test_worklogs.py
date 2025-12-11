"""
Tests for worklog endpoints (time tracking).

Endpoints tested:
- GET /worklogs/{key} - List worklogs on issue
- POST /worklog/{key} - Add worklog (skipped - write operation)
- GET /worklog/{key}/{worklog_id} - Get specific worklog
"""

import pytest

from helpers import TEST_PROJECT, TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestListWorklogs:
    """Test /worklogs/{key} endpoint."""

    def test_list_worklogs_basic(self):
        """Should list worklogs on an issue."""
        result = run_cli("jira", "worklogs", TEST_ISSUE)
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_worklogs_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "worklogs", TEST_ISSUE, "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_worklogs_human_format(self):
        """Should format worklogs for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "worklogs", TEST_ISSUE, "--format", "human")
        assert code == 0

    def test_list_worklogs_ai_format(self):
        """Should format worklogs for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "worklogs", TEST_ISSUE, "--format", "ai")
        assert code == 0

    def test_list_worklogs_markdown_format(self):
        """Should format worklogs as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "worklogs", TEST_ISSUE, "--format", "markdown")
        assert code == 0

    def test_list_worklogs_structure(self):
        """Worklogs should have expected structure if present."""
        result = run_cli("jira", "worklogs", TEST_ISSUE)
        data = get_data(result)
        if len(data) > 0:
            worklog = data[0]
            # Worklogs typically have: id, author, timeSpent, started
            assert ("id" in worklog or "timeSpent" in worklog or
                    "timeSpentSeconds" in worklog or "author" in worklog)

    def test_list_worklogs_invalid_issue(self):
        """Should handle non-existent issue gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "worklogs", "NONEXISTENT-99999")
        stdout_lower = stdout.lower()
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "404" in stdout_lower or code != 0)


class TestGetWorklog:
    """Test /worklog/{key}/{worklog_id} endpoint."""

    def test_get_worklog_invalid_id(self):
        """Should handle non-existent worklog gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "worklog", TEST_ISSUE, "99999999")
        stdout_lower = stdout.lower()
        # Handle both English and German error messages, and API errors
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "gefunden" in stdout_lower or
                "konnte" in stdout_lower or "404" in stdout_lower or
                "detail" in stdout_lower or "missing" in stdout_lower or code != 0)


class TestWorklogHelp:
    """Test worklog help system."""

    def test_worklogs_help(self):
        """Should show help for worklogs command."""
        stdout, stderr, code = run_cli_raw("jira", "worklogs", "--help")
        assert code == 0 or "worklogs" in stdout.lower()

    def test_worklog_help(self):
        """Should show help for worklog command."""
        stdout, stderr, code = run_cli_raw("jira", "worklog", "--help")
        assert code == 0 or "worklog" in stdout.lower() or "time" in stdout.lower()


class TestAddWorklog:
    """Test /worklog/{key} POST endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_add_worklog(self):
        """Should add worklog to issue."""
        result = run_cli("jira", "worklog", TEST_ISSUE, "--timeSpent", "1h")
        data = get_data(result)
        assert "id" in data or data.get("success") is True

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_add_worklog_with_comment(self):
        """Should add worklog with comment."""
        result = run_cli("jira", "worklog", TEST_ISSUE,
                        "--timeSpent", "30m", "--comment", "Test work")
        data = get_data(result)
        assert "id" in data or data.get("success") is True


class TestWorklogEdgeCases:
    """Test edge cases for worklogs."""

    def test_worklog_invalid_key_format(self):
        """Should handle invalid issue key format."""
        stdout, stderr, code = run_cli_raw("jira", "worklogs", "invalid-key-format")
        assert ("error" in stdout.lower() or "not found" in stdout.lower() or
                "existiert nicht" in stdout.lower() or code != 0)

    def test_worklog_empty_key(self):
        """Should handle missing issue key."""
        stdout, stderr, code = run_cli_raw("jira", "worklogs")
        stdout_lower = stdout.lower()
        assert ("error" in stdout_lower or "required" in stderr.lower() or
                "not found" in stdout_lower or code != 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
