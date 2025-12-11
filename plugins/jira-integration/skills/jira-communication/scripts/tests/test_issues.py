"""
Tests for issue endpoints.

Endpoints tested:
- GET /issue/{key} - Get issue details
- POST /create - Create issue (skipped - write operation)
- PUT /issue/{key} - Update issue (skipped - write operation)
"""

import pytest

from helpers import TEST_PROJECT, TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestGetIssue:
    """Test /issue/{key} endpoint."""

    def test_get_issue_basic(self):
        """Should fetch issue details."""
        result = run_cli("jira", "issue", TEST_ISSUE)
        data = get_data(result)
        assert data.get("key") == TEST_ISSUE
        assert "fields" in data
        assert "summary" in data["fields"]

    def test_get_issue_with_fields(self):
        """Should fetch only specified fields."""
        result = run_cli("jira", "issue", TEST_ISSUE, "--fields", "summary,status")
        data = get_data(result)
        assert data.get("key") == TEST_ISSUE
        assert "summary" in data.get("fields", {})

    def test_get_issue_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "issue", TEST_ISSUE, "--format", "json")
        data = get_data(result)
        assert data.get("key") == TEST_ISSUE

    def test_get_issue_human_format(self):
        """Should format issue for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "issue", TEST_ISSUE, "--format", "human")
        assert TEST_ISSUE in stdout
        assert code == 0

    def test_get_issue_ai_format(self):
        """Should format issue for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "issue", TEST_ISSUE, "--format", "ai")
        assert code == 0

    def test_get_issue_markdown_format(self):
        """Should format issue as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "issue", TEST_ISSUE, "--format", "markdown")
        assert code == 0

    def test_get_issue_not_found(self):
        """Should handle non-existent issue gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "issue", "NONEXISTENT-99999")
        stdout_lower = stdout.lower()
        # Handle both English and German error messages
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "detail" in stdout_lower or code != 0)

    def test_get_issue_invalid_key_format(self):
        """Should handle invalid issue key format."""
        stdout, stderr, code = run_cli_raw("jira", "issue", "not-a-valid-key")
        stdout_lower = stdout.lower()
        assert (code != 0 or "error" in stdout_lower or "not found" in stdout_lower or
                "existiert nicht" in stdout_lower or "detail" in stdout_lower)


class TestIssueHelp:
    """Test issue help system."""

    def test_issue_help(self):
        """Should show help for issue command."""
        stdout, stderr, code = run_cli_raw("jira", "issue", "--help")
        assert code == 0 or "issue" in stdout.lower()


class TestCreateIssue:
    """Test /create endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_create_issue(self):
        """Should create a new issue."""
        result = run_cli("jira", "create",
                        "--project", TEST_PROJECT,
                        "--type", "Task",
                        "--summary", "[TEST] Auto-generated test issue - please delete")
        data = get_data(result)
        assert "key" in data
        print(f"Created issue: {data['key']}")

    def test_create_help(self):
        """Should show create command help with examples."""
        stdout, stderr, code = run_cli_raw("jira", "create", "--help")
        assert "--project" in stdout
        assert "--type" in stdout
        assert "--summary" in stdout
        assert "Examples:" in stdout
        assert code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
