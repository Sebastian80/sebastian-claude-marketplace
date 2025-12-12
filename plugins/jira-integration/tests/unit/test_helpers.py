"""
Tests for response formatting utilities.
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.responses import JSONResponse, PlainTextResponse

# Setup paths
PLUGIN_ROOT = Path(__file__).parent.parent.parent
SKILLS_PLUGIN = PLUGIN_ROOT / "skills" / "jira-communication" / "scripts" / "skills_plugin"
AI_TOOL_BRIDGE = PLUGIN_ROOT.parent / "ai-tool-bridge" / "src"
sys.path.insert(0, str(SKILLS_PLUGIN.parent))
sys.path.insert(0, str(AI_TOOL_BRIDGE))

from skills_plugin.response import success, error, formatted, formatted_error


class TestSuccess:
    """Tests for success()."""

    def test_wraps_data(self):
        """Should wrap data in JSONResponse."""
        result = success({"key": "TEST-1"})

        assert isinstance(result, JSONResponse)
        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == {"key": "TEST-1"}

    def test_handles_list_data(self):
        """Should handle list data."""
        result = success([1, 2, 3])

        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == [1, 2, 3]

    def test_handles_string_data(self):
        """Should handle string data."""
        result = success("hello")

        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == "hello"

    def test_handles_none(self):
        """Should handle None data."""
        result = success(None)
        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] is None

    def test_handles_empty_dict(self):
        """Should handle empty dict."""
        result = success({})
        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == {}


class TestError:
    """Tests for error()."""

    def test_creates_error_response(self):
        """Should create error response with message."""
        result = error("Something went wrong")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    def test_includes_hint_when_provided(self):
        """Should include hint when provided."""
        result = error("Error", hint="Try this")

        body = json.loads(result.body)
        assert body["hint"] == "Try this"

    def test_custom_status_code(self):
        """Should use custom status code."""
        result = error("Not found", status=404)
        assert result.status_code == 404

    def test_error_message_in_body(self):
        """Should include error message in body."""
        result = error("Test error message")
        body = json.loads(result.body)
        assert body["success"] is False
        assert body["error"] == "Test error message"


class TestFormatted:
    """Tests for formatted()."""

    def test_json_format_returns_json_response(self):
        """JSON format should return JSONResponse with proper serialization."""
        result = formatted({"key": "TEST-1"}, "json")

        assert isinstance(result, JSONResponse)
        body = json.loads(result.body)
        assert body["success"] is True
        assert body["data"] == {"key": "TEST-1"}

    def test_human_format_returns_plaintext(self):
        """Human format should return PlainTextResponse."""
        result = formatted({"key": "TEST-1"}, "human")

        assert isinstance(result, PlainTextResponse)

    def test_unknown_format_falls_back_to_json(self):
        """Unknown format should fallback to JSON."""
        result = formatted({"key": "TEST-1"}, "unknown_format")

        assert isinstance(result, JSONResponse)


class TestFormattedError:
    """Tests for formatted_error()."""

    def test_json_format_returns_json_response(self):
        """JSON format should return JSONResponse."""
        result = formatted_error("Error message", fmt="json")

        assert isinstance(result, JSONResponse)

    def test_human_format_returns_plaintext(self):
        """Human format should return PlainTextResponse."""
        result = formatted_error("Error message", fmt="human")

        assert isinstance(result, PlainTextResponse)

    def test_includes_hint(self):
        """Should include hint in formatted error."""
        result = formatted_error("Error", hint="Try this", fmt="human")

        assert isinstance(result, PlainTextResponse)
        assert b"Try this" in result.body or "Try this" in str(result.body)
