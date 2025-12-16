"""
Tests for saved filter endpoints.

Endpoints tested:
- GET /filters - List your favorite filters
- GET /filter/{filter_id} - Get filter details including JQL

Note: Due to Jira API limitations, /filters returns only favorites.
Use 'jira filter <id>' to access any filter by ID.
"""

import pytest

from helpers import run_cli, get_data, run_cli_raw


class TestListFilters:
    """Test /filters endpoint (returns favorite filters)."""

    def test_list_filters_basic(self):
        """Should list favorite filters."""
        result = run_cli("jira", "filters")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_filters_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "filters", "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_filters_human_format(self):
        """Should format filters for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "filters", "--format", "human")
        assert code == 0

    def test_list_filters_ai_format(self):
        """Should format filters for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "filters", "--format", "ai")
        assert code == 0

    def test_list_filters_markdown_format(self):
        """Should format filters as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "filters", "--format", "markdown")
        assert code == 0

    def test_list_filters_structure(self):
        """Filters should have expected structure if present."""
        result = run_cli("jira", "filters")
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            filter_obj = data[0]
            # Filters have: id, name, jql, owner
            assert "id" in filter_obj
            assert "name" in filter_obj
            assert "jql" in filter_obj


class TestGetFilter:
    """Test /filter/{filter_id} endpoint."""

    def test_get_filter_invalid_id(self):
        """Should handle non-existent filter gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "filter", "99999999")
        stdout_lower = stdout.lower()
        # Handle both English and German error messages
        # German: "der ausgewählte filter steht ihnen nicht zur verfügung"
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "gefunden" in stdout_lower or
                "konnte" in stdout_lower or "404" in stdout_lower or "500" in stdout_lower or
                "detail" in stdout_lower or "verfügung" in stdout_lower or code != 0)

    def test_get_filter_with_real_id(self):
        """Should get filter details if filters exist."""
        # First get list of filters to find a real ID
        result = run_cli("jira", "filters", expect_success=False)
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            filter_id = str(data[0].get("id", ""))
            if filter_id:
                result = run_cli("jira", "filter", filter_id)
                filter_data = get_data(result)
                assert "id" in filter_data or "name" in filter_data or "jql" in filter_data
        else:
            pytest.skip("No filters found")

    def test_get_filter_json_format(self):
        """Should return JSON format for filter."""
        result = run_cli("jira", "filters", expect_success=False)
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            filter_id = str(data[0].get("id", ""))
            if filter_id:
                result = run_cli("jira", "filter", filter_id, "--format", "json")
                filter_data = get_data(result)
                assert isinstance(filter_data, dict)

    def test_get_filter_human_format(self):
        """Should format filter for human reading."""
        result = run_cli("jira", "filters", expect_success=False)
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            filter_id = str(data[0].get("id", ""))
            if filter_id:
                stdout, stderr, code = run_cli_raw("jira", "filter", filter_id, "--format", "human")
                assert code == 0


class TestFiltersHelp:
    """Test filters help system."""

    def test_filters_help(self):
        """Should show help for filters command."""
        stdout, stderr, code = run_cli_raw("jira", "filters", "--help")
        assert code == 0 or "filters" in stdout.lower()

    def test_filter_help(self):
        """Should show help for filter command."""
        stdout, stderr, code = run_cli_raw("jira", "filter", "--help")
        assert code == 0 or "filter" in stdout.lower()


class TestFilterIntegration:
    """Test filter integration scenarios."""

    def test_filter_jql_content(self):
        """Filters should contain JQL queries."""
        result = run_cli("jira", "filters", expect_success=False)
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            # Check if any filter has JQL
            has_jql = any(f.get("jql") for f in data)
            # JQL might not be in list response, check detail
            if not has_jql:
                filter_id = str(data[0].get("id", ""))
                if filter_id:
                    detail = run_cli("jira", "filter", filter_id, expect_success=False)
                    filter_data = get_data(detail)
                    if isinstance(filter_data, dict):
                        assert "jql" in filter_data or "searchUrl" in filter_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
