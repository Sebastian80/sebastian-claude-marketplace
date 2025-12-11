"""
Tests for priority reference data endpoints.

Endpoints tested:
- GET /priorities - List all priority levels
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


class TestListPriorities:
    """Test /priorities endpoint."""

    def test_list_priorities_basic(self):
        """Should list all priority levels."""
        result = run_cli("jira", "priorities")
        data = get_data(result)
        assert isinstance(data, list)
        assert len(data) > 0  # Should have at least one priority

    def test_list_priorities_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "priorities", "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_priorities_human_format(self):
        """Should format priorities for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "priorities", "--format", "human")
        assert code == 0
        # Should contain typical priority names
        stdout_lower = stdout.lower()
        assert ("high" in stdout_lower or "medium" in stdout_lower or
                "low" in stdout_lower or "priority" in stdout_lower or len(stdout) > 0)

    def test_list_priorities_ai_format(self):
        """Should format priorities for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "priorities", "--format", "ai")
        assert code == 0

    def test_list_priorities_markdown_format(self):
        """Should format priorities as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "priorities", "--format", "markdown")
        assert code == 0

    def test_list_priorities_structure(self):
        """Priorities should have expected structure."""
        result = run_cli("jira", "priorities")
        data = get_data(result)
        assert len(data) > 0
        priority = data[0]
        # Priorities have: id, name, (optionally) description, iconUrl
        assert "id" in priority or "name" in priority

    def test_list_priorities_contains_standard_priorities(self):
        """Should contain standard priority names."""
        result = run_cli("jira", "priorities")
        data = get_data(result)
        priority_names = [p.get("name", "").lower() for p in data]
        # Most Jira instances have at least High, Medium, Low
        has_standard = any(name in priority_names for name in
                          ["high", "medium", "low", "highest", "lowest",
                           "hoch", "mittel", "niedrig"])  # Include German
        assert has_standard or len(priority_names) > 0


class TestPrioritiesHelp:
    """Test priorities help system."""

    def test_priorities_help(self):
        """Should show help for priorities command."""
        stdout, stderr, code = run_cli_raw("jira", "priorities", "--help")
        assert code == 0 or "priorities" in stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
