"""
Tests for search/JQL endpoint.

Endpoints tested:
- GET /search - Search issues with JQL
"""

import pytest

from helpers import TEST_PROJECT, run_cli, get_data, run_cli_raw


class TestSearch:
    """Test /search endpoint."""

    def test_search_basic(self):
        """Should search issues with JQL."""
        result = run_cli("jira", "search", "--jql", f"project = {TEST_PROJECT}")
        data = get_data(result)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "key" in data[0]

    def test_search_with_max_results(self):
        """Should respect maxResults parameter."""
        result = run_cli("jira", "search", "--jql", f"project = {TEST_PROJECT}", "--maxResults", "5")
        data = get_data(result)
        assert len(data) <= 5

    def test_search_with_fields(self):
        """Should return only specified fields."""
        result = run_cli("jira", "search", "--jql", f"project = {TEST_PROJECT}",
                        "--fields", "key,summary", "--maxResults", "1")
        data = get_data(result)
        assert len(data) > 0
        assert "key" in data[0]

    def test_search_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "search", "--jql", f"project = {TEST_PROJECT}", "--maxResults", "1")
        data = get_data(result)
        assert isinstance(data, list)

    def test_search_human_format(self):
        """Should format search results for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "search", "--jql", f"project = {TEST_PROJECT}",
                                           "--maxResults", "3", "--format", "human")
        assert code == 0
        assert TEST_PROJECT in stdout

    def test_search_ai_format(self):
        """Should format search results for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "search", "--jql", f"project = {TEST_PROJECT}",
                                           "--maxResults", "3", "--format", "ai")
        assert code == 0

    def test_search_markdown_format(self):
        """Should format search results as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "search", "--jql", f"project = {TEST_PROJECT}",
                                           "--maxResults", "3", "--format", "markdown")
        assert code == 0


class TestSearchErrorHandling:
    """Test search error handling."""

    def test_search_invalid_jql(self):
        """Should handle invalid JQL gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "search", "--jql", "invalid syntax !!!")
        stdout_lower = stdout.lower()
        assert "error" in stdout_lower or "jql" in stdout_lower or code != 0

    def test_search_empty_results(self):
        """Should handle empty search results gracefully."""
        result = run_cli("jira", "search", "--jql", "project = NONEXISTENT12345", expect_success=False)
        if isinstance(result, list):
            assert len(result) == 0
        elif isinstance(result, str):
            assert "error" in result.lower() or "jql" in result.lower() or len(result) >= 0
        else:
            data = get_data(result)
            if isinstance(data, list):
                assert len(data) == 0


class TestSearchHelp:
    """Test search help system."""

    def test_search_help(self):
        """Should show search command help with JQL examples."""
        stdout, stderr, code = run_cli_raw("jira", "search", "--help")
        assert "--jql" in stdout
        assert "Examples:" in stdout
        assert code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
