"""
Tests for watcher endpoints.

Endpoints tested:
- GET /watchers/{key} - List watchers on issue
- POST /watcher/{key} - Add watcher (skipped - write operation)
- DELETE /watcher/{key}/{username} - Remove watcher (skipped - write operation)
"""

import pytest

from helpers import TEST_PROJECT, TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestListWatchers:
    """Test /watchers/{key} endpoint."""

    def test_list_watchers_basic(self):
        """Should list watchers on an issue."""
        result = run_cli("jira", "watchers", TEST_ISSUE)
        data = get_data(result)
        # Watchers may be a dict with watchers list or direct list
        assert isinstance(data, (list, dict))

    def test_list_watchers_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "watchers", TEST_ISSUE, "--format", "json")
        data = get_data(result)
        assert isinstance(data, (list, dict))

    def test_list_watchers_human_format(self):
        """Should format watchers for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "watchers", TEST_ISSUE, "--format", "human")
        assert code == 0

    def test_list_watchers_ai_format(self):
        """Should format watchers for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "watchers", TEST_ISSUE, "--format", "ai")
        assert code == 0

    def test_list_watchers_markdown_format(self):
        """Should format watchers as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "watchers", TEST_ISSUE, "--format", "markdown")
        assert code == 0

    def test_list_watchers_structure(self):
        """Watchers response should have expected structure."""
        result = run_cli("jira", "watchers", TEST_ISSUE)
        data = get_data(result)
        # Jira watchers typically return {watchCount, isWatching, watchers: [...]}
        if isinstance(data, dict):
            assert "watchers" in data or "watchCount" in data or "isWatching" in data
        elif isinstance(data, list):
            # Direct list of watchers
            if len(data) > 0:
                watcher = data[0]
                assert "name" in watcher or "displayName" in watcher or "accountId" in watcher

    def test_list_watchers_invalid_issue(self):
        """Should handle non-existent issue gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "watchers", "NONEXISTENT-99999")
        stdout_lower = stdout.lower()
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "detail" in stdout_lower or code != 0)


class TestWatcherHelp:
    """Test watcher help system."""

    def test_watchers_help(self):
        """Should show help for watchers command."""
        stdout, stderr, code = run_cli_raw("jira", "watchers", "--help")
        assert code == 0 or "watchers" in stdout.lower()


class TestAddWatcher:
    """Test /watcher/{key} POST endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_add_watcher(self):
        """Should add watcher to issue."""
        result = run_cli("jira", "watcher", TEST_ISSUE, "--username", "test.user")
        data = get_data(result)
        assert "added" in data or data.get("success") is True


class TestRemoveWatcher:
    """Test /watcher/{key}/{username} DELETE endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_remove_watcher(self):
        """Should remove watcher from issue."""
        pass


class TestWatcherEdgeCases:
    """Test edge cases for watchers."""

    def test_watcher_invalid_key_format(self):
        """Should handle invalid issue key format."""
        stdout, stderr, code = run_cli_raw("jira", "watchers", "invalid-key-format")
        assert ("error" in stdout.lower() or "not found" in stdout.lower() or
                "existiert nicht" in stdout.lower() or code != 0)

    def test_watcher_empty_key(self):
        """Should handle missing issue key."""
        stdout, stderr, code = run_cli_raw("jira", "watchers")
        stdout_lower = stdout.lower()
        assert ("error" in stdout_lower or "required" in stderr.lower() or
                "not found" in stdout_lower or code != 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
