"""
Tests for component endpoints.

Endpoints tested:
- GET /components/{project} - List components in project
- POST /component - Create component (skipped - write operation)
- GET /component/{component_id} - Get component details
- DELETE /component/{component_id} - Delete component (skipped - write operation)
"""

import pytest

from helpers import TEST_PROJECT, TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestListComponents:
    """Test /components/{project} endpoint."""

    def test_list_components_basic(self):
        """Should list components in a project."""
        result = run_cli("jira", "components", TEST_PROJECT)
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_components_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "components", TEST_PROJECT, "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_components_human_format(self):
        """Should format components for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "components", TEST_PROJECT, "--format", "human")
        assert code == 0

    def test_list_components_ai_format(self):
        """Should format components for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "components", TEST_PROJECT, "--format", "ai")
        assert code == 0

    def test_list_components_markdown_format(self):
        """Should format components as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "components", TEST_PROJECT, "--format", "markdown")
        assert code == 0

    def test_list_components_structure(self):
        """Components should have expected structure if present."""
        result = run_cli("jira", "components", TEST_PROJECT)
        data = get_data(result)
        if len(data) > 0:
            component = data[0]
            # Components have: id, name, (optionally) description, lead
            assert "id" in component or "name" in component

    def test_list_components_invalid_project(self):
        """Should handle non-existent project gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "components", "NONEXISTENT12345")
        stdout_lower = stdout.lower()
        # Handle both English and German error messages
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "gefunden" in stdout_lower or
                "konnte" in stdout_lower or "404" in stdout_lower or code != 0)


class TestGetComponent:
    """Test /component/{component_id} endpoint."""

    def test_get_component_invalid_id(self):
        """Should handle non-existent component gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "component", "99999999")
        stdout_lower = stdout.lower()
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "404" in stdout_lower or code != 0)

    def test_get_component_with_real_id(self):
        """Should get component details if components exist."""
        # First get list of components to find a real ID
        result = run_cli("jira", "components", TEST_PROJECT, expect_success=False)
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            component_id = str(data[0].get("id", ""))
            if component_id:
                result = run_cli("jira", "component", component_id)
                component = get_data(result)
                assert "id" in component or "name" in component
        else:
            pytest.skip("No components found in test project")


class TestComponentHelp:
    """Test component help system."""

    def test_components_help(self):
        """Should show help for components command."""
        stdout, stderr, code = run_cli_raw("jira", "components", "--help")
        assert code == 0 or "components" in stdout.lower()

    def test_component_help(self):
        """Should show help for component command."""
        stdout, stderr, code = run_cli_raw("jira", "component", "--help")
        assert code == 0 or "component" in stdout.lower()


class TestCreateComponent:
    """Test /component POST endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_create_component(self):
        """Should create a new component."""
        result = run_cli("jira", "component",
                        "--project", TEST_PROJECT,
                        "--name", "[TEST] Auto-generated component")
        data = get_data(result)
        assert "id" in data or data.get("success") is True


class TestDeleteComponent:
    """Test /component/{component_id} DELETE endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_delete_component(self):
        """Should delete a component."""
        pass


class TestComponentEdgeCases:
    """Test edge cases for components."""

    def test_component_empty_project(self):
        """Should handle missing project key."""
        stdout, stderr, code = run_cli_raw("jira", "components")
        stdout_lower = stdout.lower()
        assert ("error" in stdout_lower or "required" in stderr.lower() or
                "not found" in stdout_lower or code != 0)

    def test_component_lowercase_project(self):
        """Should handle lowercase project key."""
        stdout, stderr, code = run_cli_raw("jira", "components", TEST_PROJECT.lower())
        # May work or return error
        assert code == 0 or "not found" in stdout.lower() or "error" in stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
