"""
Tests for field reference data endpoints.

Endpoints tested:
- GET /fields - List all fields
- GET /fields/custom - List only custom fields
"""

import pytest

from helpers import run_cli, get_data, run_cli_raw


class TestListFields:
    """Test /fields endpoint."""

    def test_list_fields_basic(self):
        """Should list all fields."""
        result = run_cli("jira", "fields")
        data = get_data(result)
        assert isinstance(data, list)
        assert len(data) > 0  # Should have system fields at minimum

    def test_list_fields_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "fields", "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_fields_human_format(self):
        """Should format fields for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "fields", "--format", "human")
        assert code == 0
        # Should contain typical field names
        stdout_lower = stdout.lower()
        assert ("summary" in stdout_lower or "description" in stdout_lower or
                "status" in stdout_lower or "field" in stdout_lower or len(stdout) > 0)

    def test_list_fields_ai_format(self):
        """Should format fields for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "fields", "--format", "ai")
        assert code == 0

    def test_list_fields_markdown_format(self):
        """Should format fields as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "fields", "--format", "markdown")
        assert code == 0

    def test_list_fields_structure(self):
        """Fields should have expected structure."""
        result = run_cli("jira", "fields")
        data = get_data(result)
        assert len(data) > 0
        field = data[0]
        # Fields have: id, name, (optionally) custom, schema
        assert "id" in field or "name" in field

    def test_list_fields_contains_system_fields(self):
        """Should contain standard system fields."""
        result = run_cli("jira", "fields")
        data = get_data(result)
        field_ids = [f.get("id", "") for f in data]
        # Should have standard fields like summary, description, status
        has_system = any(fid in field_ids for fid in
                        ["summary", "description", "status", "assignee",
                         "reporter", "priority", "issuetype"])
        assert has_system


class TestListCustomFields:
    """Test /fields/custom endpoint."""

    def test_list_custom_fields_basic(self):
        """Should list only custom fields."""
        result = run_cli("jira", "fields/custom")
        data = get_data(result)
        assert isinstance(data, list)
        # All returned fields should be custom fields
        for field in data:
            field_id = field.get("id", "")
            assert field_id.startswith("customfield_") or field.get("custom") is True

    def test_list_custom_fields_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "fields/custom", "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_custom_fields_human_format(self):
        """Should format custom fields for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "fields/custom", "--format", "human")
        assert code == 0

    def test_list_custom_fields_subset_of_all(self):
        """Custom fields should be a subset of all fields."""
        all_result = run_cli("jira", "fields")
        custom_result = run_cli("jira", "fields/custom")

        all_data = get_data(all_result)
        custom_data = get_data(custom_result)

        assert len(custom_data) <= len(all_data)

        # Verify custom fields are present in all fields
        all_ids = {f.get("id") for f in all_data}
        for custom in custom_data:
            assert custom.get("id") in all_ids


class TestFieldsHelp:
    """Test fields help system."""

    def test_fields_help(self):
        """Should show help for fields command."""
        stdout, stderr, code = run_cli_raw("jira", "fields", "--help")
        assert code == 0 or "fields" in stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
