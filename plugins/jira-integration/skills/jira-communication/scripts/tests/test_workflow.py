"""
Tests for workflow/transition endpoints.

Endpoints tested:
- GET /transitions/{key} - List transitions for issue
- POST /transition/{key} - Execute transition (skipped - write operation)
- GET /workflows - List cached workflows
"""

import pytest

from helpers import TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestTransitions:
    """Test /transitions/{key} endpoint."""

    def test_list_transitions_basic(self):
        """Should list available transitions for an issue."""
        result = run_cli("jira", "transitions", TEST_ISSUE)
        data = get_data(result)
        assert isinstance(data, list)
        if len(data) > 0:
            assert "id" in data[0] or "name" in data[0]

    def test_list_transitions_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "transitions", TEST_ISSUE, "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_transitions_human_format(self):
        """Should format transitions for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "transitions", TEST_ISSUE, "--format", "human")
        assert code == 0

    def test_list_transitions_ai_format(self):
        """Should format transitions for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "transitions", TEST_ISSUE, "--format", "ai")
        assert code == 0

    def test_list_transitions_invalid_issue(self):
        """Should handle non-existent issue gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "transitions", "NONEXISTENT-99999")
        stdout_lower = stdout.lower()
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "detail" in stdout_lower or code != 0)


class TestWorkflows:
    """Test /workflows endpoint."""

    def test_list_workflows_basic(self):
        """Should list cached workflows."""
        result = run_cli("jira", "workflows")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_workflows_human_format(self):
        """Should format workflows for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "workflows", "--format", "human")
        assert code == 0


class TestTransitionHelp:
    """Test transition help system."""

    def test_transitions_help(self):
        """Should show help for transitions command."""
        stdout, stderr, code = run_cli_raw("jira", "transitions", "--help")
        assert code == 0 or "transition" in stdout.lower()

    def test_transition_help(self):
        """Should show help for transition command."""
        stdout, stderr, code = run_cli_raw("jira", "transition", "--help")
        assert code == 0 or "transition" in stdout.lower()


class TestExecuteTransition:
    """Test /transition/{key} POST endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_execute_transition(self):
        """Should execute transition on issue."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
