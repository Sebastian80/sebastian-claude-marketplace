"""
Tests for helper functions: retry decorator, connection handling, response formatting.
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Setup paths
PLUGIN_ROOT = Path(__file__).parent.parent.parent
SKILLS_PLUGIN = PLUGIN_ROOT / "skills" / "jira-communication" / "scripts" / "skills_plugin"
SKILLS_DAEMON = PLUGIN_ROOT.parent / "skills-daemon"
sys.path.insert(0, str(SKILLS_PLUGIN.parent))
sys.path.insert(0, str(SKILLS_DAEMON))

from skills_plugin import (
    is_connection_error,
    with_retry,
    reset_client,
    check_connection,
    get_client_sync,
    success_response,
    error_response,
    formatted_response,
    formatted_error,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Connection Error Detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestIsConnectionError:
    """Tests for is_connection_error()."""

    @pytest.mark.parametrize("error_message", [
        "Connection refused",
        "connection reset by peer",
        "Timeout error",
        "Network unreachable",
        "Socket error",
        "Broken pipe",
        "EOF occurred",
        "Service unavailable",
    ])
    def test_detects_connection_errors(self, error_message):
        """Should detect various connection error messages."""
        error = Exception(error_message)
        assert is_connection_error(error) is True

    @pytest.mark.parametrize("error_message", [
        "Invalid JQL syntax",
        "Issue not found",
        "Permission denied",
        "Field 'summary' is required",
        "Invalid project key",
    ])
    def test_ignores_non_connection_errors(self, error_message):
        """Should not flag non-connection errors."""
        error = Exception(error_message)
        assert is_connection_error(error) is False

    def test_case_insensitive(self):
        """Should match regardless of case."""
        assert is_connection_error(Exception("CONNECTION REFUSED")) is True
        assert is_connection_error(Exception("TIMEOUT")) is True


# ═══════════════════════════════════════════════════════════════════════════════
# Retry Decorator
# ═══════════════════════════════════════════════════════════════════════════════

class TestWithRetry:
    """Tests for the @with_retry decorator."""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global state."""
        import skills_plugin
        skills_plugin.jira_client = None
        yield
        skills_plugin.jira_client = None

    def test_no_retry_on_success(self):
        """Should not retry if function succeeds."""
        call_count = 0

        @with_retry(retries=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retries_on_connection_error(self):
        """Should retry on connection errors."""
        call_count = 0

        @with_retry(retries=3, delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Connection refused")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        """Should raise after exhausting retries."""
        @with_retry(retries=3, delay=0.01)
        def failing_func():
            raise Exception("Connection timeout")

        with pytest.raises(Exception, match="timeout"):
            failing_func()

    def test_no_retry_on_non_connection_error(self):
        """Should not retry on non-connection errors."""
        call_count = 0

        @with_retry(retries=3)
        def business_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(ValueError):
            business_error_func()

        assert call_count == 1  # No retries


# ═══════════════════════════════════════════════════════════════════════════════
# Connection Management
# ═══════════════════════════════════════════════════════════════════════════════

class TestResetClient:
    """Tests for reset_client()."""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global state."""
        import skills_plugin
        skills_plugin.jira_client = None
        yield
        skills_plugin.jira_client = None

    def test_resets_client_to_none(self):
        """Should set jira_client to None."""
        import skills_plugin
        skills_plugin.jira_client = MagicMock()

        reset_client()

        assert skills_plugin.jira_client is None


class TestCheckConnection:
    """Tests for check_connection()."""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global state."""
        import skills_plugin
        skills_plugin.jira_client = None
        skills_plugin.last_health_check = 0
        yield
        skills_plugin.jira_client = None

    def test_returns_false_when_no_client(self):
        """Should return False when no client exists."""
        assert check_connection() is False

    def test_returns_true_when_recently_checked(self):
        """Should return True if recently checked (skip re-check)."""
        import skills_plugin
        skills_plugin.jira_client = MagicMock()
        skills_plugin.last_health_check = time.time()  # Just now

        assert check_connection() is True

    def test_calls_myself_when_check_needed(self, mock_jira_client):
        """Should call myself() when check is stale."""
        import skills_plugin
        skills_plugin.jira_client = mock_jira_client
        skills_plugin.last_health_check = 0  # Very stale

        result = check_connection()

        assert result is True
        mock_jira_client.myself.assert_called_once()

    def test_resets_client_on_failure(self):
        """Should reset client if connection check fails."""
        import skills_plugin
        mock_client = MagicMock()
        mock_client.myself.side_effect = Exception("Connection lost")
        skills_plugin.jira_client = mock_client
        skills_plugin.last_health_check = 0

        result = check_connection()

        assert result is False
        assert skills_plugin.jira_client is None


# ═══════════════════════════════════════════════════════════════════════════════
# Response Formatting
# ═══════════════════════════════════════════════════════════════════════════════

class TestSuccessResponse:
    """Tests for success_response()."""

    def test_wraps_data(self):
        """Should wrap data in JSONResponse."""
        import json
        from fastapi.responses import JSONResponse
        result = success_response({"key": "TEST-1"})

        assert isinstance(result, JSONResponse)
        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == {"key": "TEST-1"}

    def test_handles_list_data(self):
        """Should handle list data."""
        import json
        result = success_response([1, 2, 3])

        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == [1, 2, 3]

    def test_handles_string_data(self):
        """Should handle string data."""
        import json
        result = success_response("hello")

        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == "hello"


class TestErrorResponse:
    """Tests for error_response()."""

    def test_creates_error_response(self):
        """Should create error response with message."""
        from fastapi.responses import JSONResponse
        result = error_response("Something went wrong")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    def test_includes_hint_when_provided(self):
        """Should include hint when provided."""
        result = error_response("Error", hint="Try this")

        # Check that hint is in the response body
        import json
        body = json.loads(result.body)
        assert body["hint"] == "Try this"

    def test_custom_status_code(self):
        """Should use custom status code."""
        result = error_response("Not found", status=404)
        assert result.status_code == 404


class TestFormattedResponse:
    """Tests for formatted_response()."""

    def test_json_format_returns_json_response(self):
        """JSON format should return JSONResponse with proper serialization."""
        import json
        from fastapi.responses import JSONResponse
        result = formatted_response({"key": "TEST-1"}, "json")

        assert isinstance(result, JSONResponse)
        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == {"key": "TEST-1"}

    def test_human_format_returns_plaintext(self):
        """Human format should return PlainTextResponse."""
        from fastapi.responses import PlainTextResponse
        result = formatted_response({"key": "TEST-1"}, "human")

        assert isinstance(result, PlainTextResponse)


class TestFormattedError:
    """Tests for formatted_error()."""

    def test_json_format_returns_json_response(self):
        """JSON format should return JSONResponse."""
        from fastapi.responses import JSONResponse
        result = formatted_error("Error message", fmt="json")

        assert isinstance(result, JSONResponse)

    def test_human_format_returns_plaintext(self):
        """Human format should return PlainTextResponse."""
        from fastapi.responses import PlainTextResponse
        result = formatted_error("Error message", fmt="human")

        assert isinstance(result, PlainTextResponse)

    def test_includes_hint(self):
        """Should include hint in formatted error."""
        from fastapi.responses import PlainTextResponse
        result = formatted_error("Error", hint="Try this", fmt="human")

        assert isinstance(result, PlainTextResponse)
        assert b"Try this" in result.body or "Try this" in str(result.body)


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge case tests for helper functions."""

    def test_is_connection_error_with_empty_message(self):
        """Should handle empty error message."""
        assert is_connection_error(Exception("")) is False

    def test_is_connection_error_with_none_message(self):
        """Should handle None-like error message."""
        assert is_connection_error(Exception()) is False

    def test_success_response_with_none(self):
        """Should handle None data."""
        import json
        result = success_response(None)
        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] is None

    def test_success_response_with_empty_dict(self):
        """Should handle empty dict."""
        import json
        result = success_response({})
        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == {}
