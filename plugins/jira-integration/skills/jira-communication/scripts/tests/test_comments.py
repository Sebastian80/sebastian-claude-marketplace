"""
Tests for comment endpoints.

Endpoints tested:
- GET /comments/{key} - List comments on issue
- POST /comment/{key} - Add comment (skipped - write operation)
"""

import pytest

from helpers import TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestListComments:
    """Test /comments/{key} endpoint."""

    def test_list_comments_basic(self):
        """Should list comments on an issue."""
        result = run_cli("jira", "comments", TEST_ISSUE)
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_comments_with_limit(self):
        """Should respect limit parameter."""
        result = run_cli("jira", "comments", TEST_ISSUE, "--limit", "2")
        data = get_data(result)
        assert len(data) <= 2

    def test_list_comments_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "comments", TEST_ISSUE, "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_comments_human_format(self):
        """Should format comments for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "comments", TEST_ISSUE, "--format", "human")
        assert code == 0

    def test_list_comments_ai_format(self):
        """Should format comments for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "comments", TEST_ISSUE, "--format", "ai")
        assert code == 0

    def test_list_comments_markdown_format(self):
        """Should format comments as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "comments", TEST_ISSUE, "--format", "markdown")
        assert code == 0

    def test_list_comments_invalid_issue(self):
        """Should handle non-existent issue gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "comments", "NONEXISTENT-99999")
        stdout_lower = stdout.lower()
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "detail" in stdout_lower or code != 0)

    def test_list_comments_structure(self):
        """Comments should have expected structure if present."""
        result = run_cli("jira", "comments", TEST_ISSUE)
        data = get_data(result)
        if len(data) > 0:
            comment = data[0]
            assert "id" in comment or "body" in comment or "author" in comment


class TestCommentHelp:
    """Test comment help system."""

    def test_comments_help(self):
        """Should show help for comments command."""
        stdout, stderr, code = run_cli_raw("jira", "comments", "--help")
        assert code == 0 or "comment" in stdout.lower()

    def test_comment_help(self):
        """Should show comment help with wiki markup guidance."""
        stdout, stderr, code = run_cli_raw("jira", "comment", "--help")
        assert "wiki markup" in stdout.lower() or "Jira" in stdout
        assert code == 0


class TestAddComment:
    """Test /comment/{key} POST endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_add_comment(self):
        """Should add comment to issue."""
        result = run_cli("jira", "comment", TEST_ISSUE,
                        "--text", "[TEST] Auto-generated test comment")
        data = get_data(result)
        assert "id" in data or "self" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
