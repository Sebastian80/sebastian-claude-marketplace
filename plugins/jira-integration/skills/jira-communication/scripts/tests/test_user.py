"""
Tests for user endpoints.

Endpoints tested:
- GET /user/me - Get current authenticated user
"""

import pytest

from helpers import run_cli, get_data, run_cli_raw


class TestCurrentUser:
    """Test /user/me endpoint."""

    def test_get_current_user_basic(self):
        """Should return authenticated user info."""
        result = run_cli("jira", "user/me")
        data = get_data(result)
        assert "name" in data or "displayName" in data
        assert "emailAddress" in data

    def test_get_current_user_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "user/me", "--format", "json")
        data = get_data(result)
        assert isinstance(data, dict)

    def test_get_current_user_human_format(self):
        """Should format user for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "user/me", "--format", "human")
        assert code == 0

    def test_get_current_user_ai_format(self):
        """Should format user for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "user/me", "--format", "ai")
        assert code == 0

    def test_get_current_user_structure(self):
        """User should have expected structure."""
        result = run_cli("jira", "user/me")
        data = get_data(result)
        # Users typically have: name/displayName, emailAddress, accountId
        assert "emailAddress" in data or "accountId" in data


class TestUserHelp:
    """Test user help system."""

    def test_user_help(self):
        """Should show help for user command."""
        stdout, stderr, code = run_cli_raw("jira", "user", "--help")
        assert code == 0 or "user" in stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
