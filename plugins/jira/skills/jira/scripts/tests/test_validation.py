"""
Tests for CLI parameter validation.

Cross-cutting tests that verify parameter validation, typo suggestions,
and helpful error messages work correctly.
"""

import pytest

from helpers import TEST_PROJECT, run_cli_raw


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
        combined_lower = (stdout + stderr).lower()
        assert "missing required parameter" in combined_lower or "project" in combined_lower


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_command(self):
        """Should handle invalid command gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "nonexistent_command_12345")
        stdout_lower = stdout.lower()
        # Should return error or help or "not found"
        assert code != 0 or "error" in stdout_lower or "available" in stdout_lower or "not found" in stdout_lower


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
