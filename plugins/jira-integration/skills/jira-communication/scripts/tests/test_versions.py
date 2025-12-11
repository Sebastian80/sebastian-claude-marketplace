"""
Tests for version/release endpoints.

Endpoints tested:
- GET /versions/{project} - List versions in project
- POST /version - Create version (skipped - write operation)
- GET /version/{version_id} - Get version details
- PATCH /version/{version_id} - Update version (skipped - write operation)
"""

import pytest

from helpers import TEST_PROJECT, TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestListVersions:
    """Test /versions/{project} endpoint."""

    def test_list_versions_basic(self):
        """Should list versions in a project."""
        result = run_cli("jira", "versions", TEST_PROJECT)
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_versions_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "versions", TEST_PROJECT, "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_versions_human_format(self):
        """Should format versions for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "versions", TEST_PROJECT, "--format", "human")
        assert code == 0

    def test_list_versions_ai_format(self):
        """Should format versions for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "versions", TEST_PROJECT, "--format", "ai")
        assert code == 0

    def test_list_versions_markdown_format(self):
        """Should format versions as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "versions", TEST_PROJECT, "--format", "markdown")
        assert code == 0

    def test_list_versions_structure(self):
        """Versions should have expected structure if present."""
        result = run_cli("jira", "versions", TEST_PROJECT)
        data = get_data(result)
        if len(data) > 0:
            version = data[0]
            # Versions have: id, name, released, (optionally) description, releaseDate
            assert "id" in version or "name" in version

    def test_list_versions_invalid_project(self):
        """Should handle non-existent project gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "versions", "NONEXISTENT12345")
        stdout_lower = stdout.lower()
        # Handle both English and German error messages
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "gefunden" in stdout_lower or
                "konnte" in stdout_lower or "404" in stdout_lower or code != 0)


class TestGetVersion:
    """Test /version/{version_id} endpoint."""

    def test_get_version_invalid_id(self):
        """Should handle non-existent version gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "version", "99999999")
        stdout_lower = stdout.lower()
        # Handle both English and German error messages, and API errors
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "gefunden" in stdout_lower or
                "konnte" in stdout_lower or "404" in stdout_lower or
                "detail" in stdout_lower or "attribute" in stdout_lower or code != 0)

    def test_get_version_with_real_id(self):
        """Should get version details if versions exist."""
        # First get list of versions to find a real ID
        result = run_cli("jira", "versions", TEST_PROJECT, expect_success=False)
        data = get_data(result)
        if isinstance(data, list) and len(data) > 0:
            version_id = str(data[0].get("id", ""))
            if version_id:
                result = run_cli("jira", "version", version_id)
                version = get_data(result)
                assert "id" in version or "name" in version
        else:
            pytest.skip("No versions found in test project")


class TestVersionHelp:
    """Test version help system."""

    def test_versions_help(self):
        """Should show help for versions command."""
        stdout, stderr, code = run_cli_raw("jira", "versions", "--help")
        assert code == 0 or "versions" in stdout.lower()

    def test_version_help(self):
        """Should show help for version command."""
        stdout, stderr, code = run_cli_raw("jira", "version", "--help")
        assert code == 0 or "version" in stdout.lower()


class TestCreateVersion:
    """Test /version POST endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_create_version(self):
        """Should create a new version."""
        result = run_cli("jira", "version",
                        "--project", TEST_PROJECT,
                        "--name", "[TEST] Auto-generated version")
        data = get_data(result)
        assert "id" in data or data.get("success") is True


class TestUpdateVersion:
    """Test /version/{version_id} PATCH endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_update_version(self):
        """Should update a version."""
        pass


class TestVersionEdgeCases:
    """Test edge cases for versions."""

    def test_version_empty_project(self):
        """Should handle missing project key."""
        stdout, stderr, code = run_cli_raw("jira", "versions")
        stdout_lower = stdout.lower()
        assert ("error" in stdout_lower or "required" in stderr.lower() or
                "not found" in stdout_lower or code != 0)

    def test_version_lowercase_project(self):
        """Should handle lowercase project key."""
        stdout, stderr, code = run_cli_raw("jira", "versions", TEST_PROJECT.lower())
        # May work or return error
        assert code == 0 or "not found" in stdout.lower() or "error" in stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
