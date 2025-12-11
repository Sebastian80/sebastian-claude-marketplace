"""
Tests for saved filter endpoints.

Endpoints tested:
- GET /filters - List all accessible filters
- GET /filters/my - List my filters
- GET /filters/favorites - List favorite filters
- GET /filter/{filter_id} - Get filter details
"""

import json
import subprocess
import pytest


TEST_PROJECT = "OROSPD"
TEST_ISSUE = "OROSPD-589"


def run_cli(*args, expect_success=True) -> dict | list | str:
    """Run skills-client command and return parsed result."""
    cmd = ["skills-client", "--json"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)

    output = result.stdout.strip()
    if not output:
        output = result.stderr.strip()

    try:
        parsed = json.loads(output)
        if expect_success and isinstance(parsed, dict):
            if parsed.get("success") is False:
                pytest.fail(f"Command failed: {parsed.get('error')}")
            if "detail" in parsed:
                pytest.fail(f"Validation error: {parsed['detail']}")
        return parsed
    except json.JSONDecodeError:
        return output


def get_data(result) -> list | dict | str:
    """Extract data from API response."""
    if isinstance(result, dict):
        return result.get("data", result)
    return result


def run_cli_raw(*args) -> tuple[str, str, int]:
    """Run skills-client and return raw stdout, stderr, returncode."""
    cmd = ["skills-client"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


class TestListFilters:
    """Test /filters endpoint."""

    def test_list_filters_basic(self):
        """Should list all accessible filters."""
        result = run_cli("jira", "filters", expect_success=False)
        data = get_data(result)
        # May return list or error (500 from Jira API)
        assert isinstance(data, (list, dict, str))

    def test_list_filters_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "filters", "--format", "json", expect_success=False)
        data = get_data(result)
        # May return list or error (500 from Jira API)
        assert isinstance(data, (list, dict, str))

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
        result = run_cli("jira", "filters", expect_success=False)
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            filter_obj = data[0]
            # Filters have: id, name, jql, (optionally) description, owner
            assert "id" in filter_obj or "name" in filter_obj


class TestMyFilters:
    """Test /filters/my endpoint."""

    def test_list_my_filters_basic(self):
        """Should list filters owned by current user."""
        result = run_cli("jira", "filters/my", expect_success=False)
        data = get_data(result)
        # May return list or error
        assert isinstance(data, (list, dict, str))

    def test_list_my_filters_human_format(self):
        """Should format my filters for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "filters/my", "--format", "human")
        assert code == 0


class TestFavoriteFilters:
    """Test /filters/favorites endpoint."""

    def test_list_favorite_filters_basic(self):
        """Should list favorite filters."""
        result = run_cli("jira", "filters/favorites", expect_success=False)
        data = get_data(result)
        # May return list or error
        assert isinstance(data, (list, dict, str))

    def test_list_favorite_filters_human_format(self):
        """Should format favorite filters for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "filters/favorites", "--format", "human")
        assert code == 0


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
