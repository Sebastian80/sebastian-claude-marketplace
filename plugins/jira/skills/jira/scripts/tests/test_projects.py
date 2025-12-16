"""
Tests for project endpoints.

Endpoints tested:
- GET /projects - List all projects
- GET /project/{key} - Get project details
- GET /project/{key}/components - Get project components
- GET /project/{key}/versions - Get project versions
"""

import pytest

from helpers import TEST_PROJECT, TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestListProjects:
    """Test /projects endpoint."""

    def test_list_projects_basic(self):
        """Should list all accessible projects."""
        result = run_cli("jira", "projects")
        data = get_data(result)
        assert isinstance(data, list)
        assert len(data) > 0  # Should have at least one project

    def test_list_projects_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "projects", "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_projects_human_format(self):
        """Should format projects for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "projects", "--format", "human")
        assert code == 0
        assert TEST_PROJECT in stdout or len(stdout) > 0

    def test_list_projects_ai_format(self):
        """Should format projects for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "projects", "--format", "ai")
        assert code == 0

    def test_list_projects_markdown_format(self):
        """Should format projects as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "projects", "--format", "markdown")
        assert code == 0

    def test_list_projects_structure(self):
        """Projects should have expected structure."""
        result = run_cli("jira", "projects")
        data = get_data(result)
        assert len(data) > 0
        project = data[0]
        # Projects have: key, name, (optionally) id, projectTypeKey
        assert "key" in project or "name" in project

    def test_list_projects_contains_test_project(self):
        """Should contain our test project."""
        result = run_cli("jira", "projects")
        data = get_data(result)
        project_keys = [p.get("key") for p in data]
        assert TEST_PROJECT in project_keys


class TestGetProject:
    """Test /project/{key} endpoint."""

    def test_get_project_basic(self):
        """Should get project details."""
        result = run_cli("jira", "project", TEST_PROJECT)
        data = get_data(result)
        assert isinstance(data, dict)
        assert data.get("key") == TEST_PROJECT

    def test_get_project_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "project", TEST_PROJECT, "--format", "json")
        data = get_data(result)
        assert isinstance(data, dict)

    def test_get_project_human_format(self):
        """Should format project for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "project", TEST_PROJECT, "--format", "human")
        assert code == 0
        assert TEST_PROJECT in stdout

    def test_get_project_ai_format(self):
        """Should format project for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "project", TEST_PROJECT, "--format", "ai")
        assert code == 0

    def test_get_project_structure(self):
        """Project should have expected structure."""
        result = run_cli("jira", "project", TEST_PROJECT)
        data = get_data(result)
        assert "key" in data
        assert "name" in data

    def test_get_project_not_found(self):
        """Should handle non-existent project gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "project", "NONEXISTENT12345")
        stdout_lower = stdout.lower()
        # Handle both English and German error messages
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "gefunden" in stdout_lower or
                "konnte" in stdout_lower or "404" in stdout_lower or code != 0)


class TestProjectComponents:
    """Test /components/{project} endpoint (accessed via project)."""

    def test_project_components_basic(self):
        """Should get project components via components endpoint."""
        result = run_cli("jira", "components", TEST_PROJECT, expect_success=False)
        data = get_data(result)
        assert isinstance(data, (list, dict, str))

    def test_project_components_human_format(self):
        """Should format components for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "components", TEST_PROJECT,
                                           "--format", "human")
        assert code == 0

    def test_project_components_structure(self):
        """Components should have expected structure if present."""
        result = run_cli("jira", "components", TEST_PROJECT, expect_success=False)
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            component = data[0]
            assert "id" in component or "name" in component


class TestProjectVersions:
    """Test /versions/{project} endpoint (accessed via project)."""

    def test_project_versions_basic(self):
        """Should get project versions via versions endpoint."""
        result = run_cli("jira", "versions", TEST_PROJECT, expect_success=False)
        data = get_data(result)
        assert isinstance(data, (list, dict, str))

    def test_project_versions_human_format(self):
        """Should format versions for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "versions", TEST_PROJECT,
                                           "--format", "human")
        assert code == 0

    def test_project_versions_structure(self):
        """Versions should have expected structure if present."""
        result = run_cli("jira", "versions", TEST_PROJECT, expect_success=False)
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            version = data[0]
            assert "id" in version or "name" in version


class TestProjectHelp:
    """Test project help system."""

    def test_projects_help(self):
        """Should show help for projects command."""
        stdout, stderr, code = run_cli_raw("jira", "projects", "--help")
        assert code == 0 or "projects" in stdout.lower()

    def test_project_help(self):
        """Should show help for project command."""
        stdout, stderr, code = run_cli_raw("jira", "project", "--help")
        assert code == 0 or "project" in stdout.lower()


class TestProjectEdgeCases:
    """Test edge cases for projects."""

    def test_project_invalid_key_case(self):
        """Should handle lowercase project key."""
        # Jira project keys are typically uppercase
        stdout, stderr, code = run_cli_raw("jira", "project", TEST_PROJECT.lower())
        combined_lower = (stdout + stderr).lower()
        # May work (Jira sometimes accepts lowercase) or return error
        assert code == 0 or "not found" in combined_lower or "error" in combined_lower

    def test_project_empty_key(self):
        """Should handle missing project key."""
        stdout, stderr, code = run_cli_raw("jira", "project")
        combined_lower = (stdout + stderr).lower()
        # Should error - missing required parameter or return not found
        assert ("error" in combined_lower or "required" in combined_lower or
                "not found" in combined_lower or code != 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
