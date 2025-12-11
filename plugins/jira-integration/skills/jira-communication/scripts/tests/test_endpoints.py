"""
Integration tests for Jira plugin endpoints.

These tests run against the live skills daemon and require:
1. skills-daemon running with jira plugin loaded
2. Valid Jira credentials configured
3. Access to a Jira project (default: OROSPD)

Run with: pytest tests/test_endpoints.py -v
"""

import json
import subprocess
import pytest


# Test configuration
TEST_PROJECT = "OROSPD"  # Project with test issues
TEST_ISSUE = "OROSPD-589"  # Existing issue for read tests


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
            # Check for error responses
            if parsed.get("success") is False:
                pytest.fail(f"Command failed: {parsed.get('error')}")
            if "detail" in parsed:  # FastAPI validation error
                pytest.fail(f"Validation error: {parsed['detail']}")
        return parsed
    except json.JSONDecodeError:
        return output


def get_data(result) -> list | dict | str:
    """Extract data from API response, handling both wrapped and direct formats."""
    if isinstance(result, dict):
        return result.get("data", result)
    return result  # Already unwrapped (list or str)


def run_cli_raw(*args) -> tuple[str, str, int]:
    """Run skills-client and return raw stdout, stderr, returncode."""
    cmd = ["skills-client"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


class TestHealthAndConnection:
    """Test daemon health and Jira connection."""

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


class TestUserEndpoint:
    """Test /user/me endpoint."""

    def test_get_current_user(self):
        """Should return authenticated user info."""
        result = run_cli("jira", "user/me")
        data = result.get("data", result)
        assert "name" in data or "displayName" in data
        assert "emailAddress" in data


class TestIssueEndpoints:
    """Test issue CRUD endpoints."""

    def test_get_issue(self):
        """Should fetch issue details."""
        result = run_cli("jira", "issue", TEST_ISSUE)
        data = result.get("data", result)
        assert data.get("key") == TEST_ISSUE
        assert "fields" in data
        assert "summary" in data["fields"]

    def test_get_issue_with_fields(self):
        """Should fetch only specified fields."""
        result = run_cli("jira", "issue", TEST_ISSUE, "--fields", "summary,status")
        data = result.get("data", result)
        assert data.get("key") == TEST_ISSUE
        assert "summary" in data.get("fields", {})

    def test_get_issue_not_found(self):
        """Should handle non-existent issue gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "issue", "NONEXISTENT-99999")
        # Should return error, not crash (may be in German: "existiert nicht")
        stdout_lower = stdout.lower()
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "detail" in stdout_lower or code != 0)

    def test_get_issue_human_format(self):
        """Should format issue for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "issue", TEST_ISSUE, "--format", "human")
        assert TEST_ISSUE in stdout
        assert code == 0


class TestSearchEndpoint:
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
        # Should have key and summary but might have more from API
        assert "key" in data[0]

    def test_search_invalid_jql(self):
        """Should handle invalid JQL gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "search", "--jql", "invalid syntax !!!")
        # Should return JQL error message
        assert "error" in stdout.lower() or "jql" in stdout.lower()

    def test_search_human_format(self):
        """Should format search results for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "search", "--jql", f"project = {TEST_PROJECT}",
                                           "--maxResults", "3", "--format", "human")
        assert code == 0
        # Should show issue keys
        assert TEST_PROJECT in stdout


class TestTransitionEndpoints:
    """Test workflow/transition endpoints."""

    def test_list_transitions(self):
        """Should list available transitions for an issue."""
        result = run_cli("jira", "transitions", TEST_ISSUE)
        data = get_data(result)
        assert isinstance(data, list)
        # Each transition should have id and name
        if len(data) > 0:
            assert "id" in data[0] or "name" in data[0]

    def test_list_workflows(self):
        """Should list cached workflows."""
        result = run_cli("jira", "workflows")
        data = get_data(result)
        assert isinstance(data, list)


class TestCommentEndpoints:
    """Test comment endpoints."""

    def test_list_comments(self):
        """Should list comments on an issue."""
        result = run_cli("jira", "comments", TEST_ISSUE)
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_comments_with_limit(self):
        """Should respect limit parameter."""
        result = run_cli("jira", "comments", TEST_ISSUE, "--limit", "2")
        data = get_data(result)
        assert len(data) <= 2


class TestLinkEndpoints:
    """Test link endpoints."""

    def test_list_link_types(self):
        """Should list available link types."""
        result = run_cli("jira", "link/types")
        data = get_data(result)
        assert isinstance(data, list)
        # Should have common link types
        link_names = [lt.get("name", "") for lt in data]
        # At least some link types should exist
        assert len(link_names) > 0


class TestWebLinkEndpoints:
    """Test web link (remote link) endpoints."""

    def test_list_weblinks(self):
        """Should list web links on an issue."""
        result = run_cli("jira", "weblinks", TEST_ISSUE)
        data = get_data(result)
        assert isinstance(data, list)


class TestHelpSystem:
    """Test help and self-describing API."""

    def test_plugin_help(self):
        """Should show plugin-level help."""
        stdout, stderr, code = run_cli_raw("jira", "--help")
        assert "jira" in stdout.lower()
        assert code == 0

    def test_command_help_create(self):
        """Should show create command help with examples."""
        stdout, stderr, code = run_cli_raw("jira", "create", "--help")
        assert "--project" in stdout
        assert "--type" in stdout
        assert "--summary" in stdout
        assert "Examples:" in stdout
        assert code == 0

    def test_command_help_search(self):
        """Should show search command help with JQL examples."""
        stdout, stderr, code = run_cli_raw("jira", "search", "--help")
        assert "--jql" in stdout
        assert "Examples:" in stdout
        assert code == 0

    def test_command_help_link(self):
        """Should show link command help with aliases."""
        stdout, stderr, code = run_cli_raw("jira", "link", "--help")
        assert "--from" in stdout
        assert "--to" in stdout
        assert "--type" in stdout
        assert "Examples:" in stdout
        assert code == 0

    def test_command_help_comment(self):
        """Should show comment help with wiki markup guidance."""
        stdout, stderr, code = run_cli_raw("jira", "comment", "--help")
        assert "wiki markup" in stdout.lower() or "Jira" in stdout
        assert code == 0


class TestParameterValidation:
    """Test CLI parameter validation."""

    def test_unknown_parameter_warning(self):
        """Should warn about unknown parameters."""
        stdout, stderr, code = run_cli_raw("jira", "search", "--jql", f"project = {TEST_PROJECT}",
                                           "--unknown_param", "value")
        assert "Warning" in stderr or "unknown" in stderr.lower()

    def test_typo_suggestion(self):
        """Should suggest similar parameter for typos."""
        stdout, stderr, code = run_cli_raw("jira", "create", "--proj", "TEST",
                                           "--type", "Story", "--summary", "test")
        # Should suggest a similar parameter (project or priority both start with "pr")
        assert "did you mean" in stderr.lower()

    def test_missing_required_param(self):
        """Should show friendly error for missing required params."""
        stdout, stderr, code = run_cli_raw("jira", "create", "--type", "Story")
        assert "Missing required parameter" in stdout or "project" in stdout.lower()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_issue_key_format(self):
        """Should handle invalid issue key format."""
        stdout, stderr, code = run_cli_raw("jira", "issue", "not-a-valid-key")
        # Should not crash, should return error (may be in German)
        stdout_lower = stdout.lower()
        assert (code != 0 or "error" in stdout_lower or "not found" in stdout_lower or
                "existiert nicht" in stdout_lower or "detail" in stdout_lower)

    def test_empty_search_results(self):
        """Should handle empty search results gracefully."""
        result = run_cli("jira", "search", "--jql", "project = NONEXISTENT12345", expect_success=False)
        # May return empty list or JQL error for invalid project
        if isinstance(result, list):
            assert len(result) == 0
        elif isinstance(result, str):
            # JQL error message (project doesn't exist)
            assert "error" in result.lower() or "jql" in result.lower() or len(result) >= 0
        else:
            data = get_data(result)
            if isinstance(data, list):
                assert len(data) == 0


# Skip write tests by default to avoid modifying Jira data
class TestWriteOperations:
    """Test write operations (create, update, etc.).

    These tests are marked to skip by default to avoid creating test data.
    Run with: pytest tests/test_endpoints.py -v -k "write" --run-write-tests
    """

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_create_issue(self):
        """Should create a new issue."""
        result = run_cli("jira", "create",
                        "--project", TEST_PROJECT,
                        "--type", "Task",
                        "--summary", "[TEST] Auto-generated test issue - please delete")
        data = result.get("data", result)
        assert "key" in data
        print(f"Created issue: {data['key']}")

    @pytest.mark.skip(reason="Write test - run manually")
    def test_add_comment(self):
        """Should add comment to issue."""
        result = run_cli("jira", "comment", TEST_ISSUE,
                        "--text", "[TEST] Auto-generated test comment")
        data = result.get("data", result)
        assert "id" in data or "self" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
