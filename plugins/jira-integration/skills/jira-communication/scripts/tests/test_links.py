"""
Tests for link endpoints.

Endpoints tested:
- GET /link/types - List available link types
- POST /link - Create issue link (skipped - write operation)
- GET /weblinks/{key} - List web links on issue
- POST /weblink/{key} - Add web link (skipped - write operation)
"""

import pytest

from helpers import TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestLinkTypes:
    """Test /link/types endpoint."""

    def test_list_link_types_basic(self):
        """Should list available link types."""
        result = run_cli("jira", "link/types")
        data = get_data(result)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_link_types_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "link/types", "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_link_types_human_format(self):
        """Should format link types for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "link/types", "--format", "human")
        assert code == 0

    def test_list_link_types_structure(self):
        """Link types should have expected structure."""
        result = run_cli("jira", "link/types")
        data = get_data(result)
        assert len(data) > 0
        link_type = data[0]
        assert "name" in link_type or "id" in link_type


class TestWebLinks:
    """Test /weblinks/{key} endpoint."""

    def test_list_weblinks_basic(self):
        """Should list web links on an issue."""
        result = run_cli("jira", "weblinks", TEST_ISSUE)
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_weblinks_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "weblinks", TEST_ISSUE, "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_weblinks_human_format(self):
        """Should format web links for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "weblinks", TEST_ISSUE, "--format", "human")
        assert code == 0

    def test_list_weblinks_invalid_issue(self):
        """Should handle non-existent issue gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "weblinks", "NONEXISTENT-99999")
        stdout_lower = stdout.lower()
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "detail" in stdout_lower or code != 0)


class TestLinkHelp:
    """Test link help system."""

    def test_link_help(self):
        """Should show link command help with aliases."""
        stdout, stderr, code = run_cli_raw("jira", "link", "--help")
        assert "--from" in stdout
        assert "--to" in stdout
        assert "--type" in stdout
        assert "Examples:" in stdout
        assert code == 0

    def test_weblinks_help(self):
        """Should show help for weblinks command."""
        stdout, stderr, code = run_cli_raw("jira", "weblinks", "--help")
        assert code == 0 or "weblink" in stdout.lower()


class TestCreateLink:
    """Test /link POST endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_create_link(self):
        """Should create issue link."""
        pass


class TestCreateWebLink:
    """Test /weblink/{key} POST endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_create_weblink(self):
        """Should create web link on issue."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
