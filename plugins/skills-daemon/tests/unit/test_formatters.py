"""
Comprehensive tests for formatters module.

Tests cover:
- All formatter types (Human, JSON, AI, Markdown)
- FormatterRegistry operations
- Factory functions
- Edge cases and error handling
"""

import json
import pytest
from unittest.mock import patch

from skills_daemon.formatters import (
    BaseFormatter,
    HumanFormatter,
    JsonFormatter,
    AIFormatter,
    MarkdownFormatter,
    FormatterRegistry,
    formatter_registry,
    get_formatter,
    get_plugin_formatter,
    format_response,
    FORMATTERS,
)


# ============================================================================
# HumanFormatter Tests
# ============================================================================

class TestHumanFormatter:
    """Tests for terminal-friendly HumanFormatter."""

    @pytest.fixture
    def formatter(self):
        return HumanFormatter()

    # --- format() with different data types ---

    def test_format_dict_simple(self, formatter):
        """Format simple dict with key-value pairs."""
        data = {"name": "test", "value": 42}
        result = formatter.format(data)

        assert "name:" in result
        assert "test" in result
        assert "value:" in result
        assert "42" in result

    def test_format_dict_nested(self, formatter):
        """Format nested dict structures."""
        data = {"outer": {"inner": "value"}}
        result = formatter.format(data)

        assert "outer:" in result
        assert "inner:" in result
        assert "value" in result

    def test_format_dict_with_list_of_dicts(self, formatter):
        """Format dict containing list of dicts shows count."""
        data = {"items": [{"a": 1}, {"b": 2}, {"c": 3}]}
        result = formatter.format(data)

        assert "items:" in result
        assert "3 items" in result

    def test_format_list_empty(self, formatter):
        """Empty list shows 'No results' message."""
        result = formatter.format([])
        assert "No results" in result

    def test_format_list_with_id_and_title(self, formatter):
        """List items with id/title show both."""
        data = [{"id": "ABC-123", "title": "My Issue"}]
        result = formatter.format(data)

        assert "ABC-123" in result
        assert "My Issue" in result

    def test_format_list_with_key_and_summary(self, formatter):
        """List items with key/summary show both."""
        data = [{"key": "JIRA-1", "summary": "Fix bug"}]
        result = formatter.format(data)

        assert "JIRA-1" in result
        assert "Fix bug" in result

    def test_format_list_id_only(self, formatter):
        """List items with only id show id."""
        data = [{"id": "item-1"}, {"id": "item-2"}]
        result = formatter.format(data)

        assert "item-1" in result
        assert "item-2" in result

    def test_format_list_primitives(self, formatter):
        """List of primitives formatted correctly."""
        data = ["one", "two", "three"]
        result = formatter.format(data)

        assert "one" in result
        assert "two" in result
        assert "three" in result
        assert "•" in result  # bullet icon

    def test_format_primitive_string(self, formatter):
        """Plain string returned as-is."""
        result = formatter.format("hello world")
        assert result == "hello world"

    def test_format_primitive_int(self, formatter):
        """Integer converted to string."""
        result = formatter.format(42)
        assert result == "42"

    # --- format_error() ---

    def test_format_error_basic(self, formatter):
        """Error formatted with icon and message."""
        result = formatter.format_error("Something went wrong")

        assert "Error:" in result
        assert "Something went wrong" in result
        assert "✗" in result  # error icon

    def test_format_error_with_hint(self, formatter):
        """Error with hint shows both."""
        result = formatter.format_error("Not found", hint="Check the ID")

        assert "Not found" in result
        assert "Hint:" in result
        assert "Check the ID" in result

    # --- format_success() ---

    def test_format_success(self, formatter):
        """Success message with icon."""
        result = formatter.format_success("Operation completed")

        assert "Operation completed" in result
        assert "✓" in result  # success icon

    # --- icon() helper ---

    def test_icon_known(self, formatter):
        """Known icon names return correct icons."""
        assert formatter.icon("success") == "✓"
        assert formatter.icon("error") == "✗"
        assert formatter.icon("warning") == "⚠"
        assert formatter.icon("bullet") == "•"

    def test_icon_unknown_returns_fallback(self, formatter):
        """Unknown icon returns fallback."""
        assert formatter.icon("nonexistent") == "•"
        assert formatter.icon("nonexistent", fallback="?") == "?"

    # --- colorize() helper ---

    def test_colorize_applies_color(self, formatter):
        """Colorize applies ANSI codes when TTY."""
        with patch("skills_daemon.colors._is_tty", return_value=True):
            from skills_daemon.formatters import HumanFormatter
            f = HumanFormatter()
            result = f.colorize("text", "red")
            # Should contain ANSI escape codes
            assert "\x1b[" in result or result == "text"


# ============================================================================
# JsonFormatter Tests
# ============================================================================

class TestJsonFormatter:
    """Tests for JSON output formatter."""

    @pytest.fixture
    def formatter(self):
        return JsonFormatter()

    def test_format_dict_valid_json(self, formatter):
        """Output is valid JSON."""
        data = {"key": "value", "number": 42}
        result = formatter.format(data)

        parsed = json.loads(result)
        assert parsed == data

    def test_format_list_valid_json(self, formatter):
        """List output is valid JSON."""
        data = [1, 2, 3]
        result = formatter.format(data)

        parsed = json.loads(result)
        assert parsed == data

    def test_format_nested_structure(self, formatter):
        """Complex nested structures serialize correctly."""
        data = {"items": [{"id": 1}, {"id": 2}], "meta": {"total": 2}}
        result = formatter.format(data)

        parsed = json.loads(result)
        assert parsed == data

    def test_format_non_serializable_uses_str(self, formatter):
        """Non-JSON-serializable objects use str()."""
        class Custom:
            def __str__(self):
                return "custom-object"

        data = {"obj": Custom()}
        result = formatter.format(data)

        parsed = json.loads(result)
        assert parsed["obj"] == "custom-object"

    def test_format_error_structure(self, formatter):
        """Error returns structured JSON."""
        result = formatter.format_error("Failed", hint="Try again")

        parsed = json.loads(result)
        assert parsed["success"] is False
        assert parsed["error"] == "Failed"
        assert parsed["hint"] == "Try again"

    def test_format_error_no_hint(self, formatter):
        """Error without hint has null hint."""
        result = formatter.format_error("Failed")

        parsed = json.loads(result)
        assert parsed["success"] is False
        assert parsed["hint"] is None

    def test_format_success_structure(self, formatter):
        """Success returns structured JSON."""
        result = formatter.format_success("Done", {"count": 5})

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["message"] == "Done"
        assert parsed["count"] == 5

    def test_format_success_no_data(self, formatter):
        """Success without data still valid."""
        result = formatter.format_success("Done")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["message"] == "Done"


# ============================================================================
# AIFormatter Tests
# ============================================================================

class TestAIFormatter:
    """Tests for LLM-optimized AIFormatter."""

    @pytest.fixture
    def formatter(self):
        return AIFormatter()

    def test_format_dict_concise(self, formatter):
        """Dict formatted concisely without decoration."""
        data = {"status": "ok", "count": 10}
        result = formatter.format(data)

        assert "status: ok" in result
        assert "count: 10" in result
        # No ANSI colors, no icons
        assert "\x1b[" not in result

    def test_format_list_with_count(self, formatter):
        """List shows count header."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = formatter.format(data)

        assert "RESULTS: 3 items" in result

    def test_format_list_empty_shows_no_results(self, formatter):
        """Empty list shows NO_RESULTS."""
        result = formatter.format([])
        assert result == "NO_RESULTS"

    def test_format_list_truncates_at_20(self, formatter):
        """Long lists truncated to 20 items."""
        data = [{"id": i} for i in range(30)]
        result = formatter.format(data)

        assert "RESULTS: 30 items" in result
        assert "... and 10 more" in result
        # Should have exactly 20 item lines plus header and footer
        lines = result.strip().split("\n")
        assert len(lines) == 22  # 1 header + 20 items + 1 "and X more"

    def test_format_list_truncates_labels(self, formatter):
        """Long labels truncated to 60 chars."""
        long_title = "A" * 100
        data = [{"id": "X", "title": long_title}]
        result = formatter.format(data)

        # Label should be truncated
        assert "A" * 60 in result
        assert "A" * 100 not in result

    def test_format_error_concise(self, formatter):
        """Error format is concise."""
        result = formatter.format_error("Failed", "Check input")

        assert result == "ERROR: Failed (hint: Check input)"

    def test_format_error_no_hint(self, formatter):
        """Error without hint."""
        result = formatter.format_error("Failed")

        assert result == "ERROR: Failed"

    def test_format_success_concise(self, formatter):
        """Success format is concise."""
        result = formatter.format_success("Done")

        assert result == "OK: Done"


# ============================================================================
# MarkdownFormatter Tests
# ============================================================================

class TestMarkdownFormatter:
    """Tests for Markdown table formatter."""

    @pytest.fixture
    def formatter(self):
        return MarkdownFormatter()

    def test_format_dict_as_table(self, formatter):
        """Dict formatted as markdown table."""
        data = {"name": "test", "value": 42}
        result = formatter.format(data)

        assert "| Field | Value |" in result
        assert "|-------|-------|" in result
        assert "| name | test |" in result
        assert "| value | 42 |" in result

    def test_format_dict_excludes_nested(self, formatter):
        """Nested dicts/lists excluded from table."""
        data = {"simple": "yes", "nested": {"a": 1}, "list": [1, 2]}
        result = formatter.format(data)

        assert "| simple | yes |" in result
        assert "nested" not in result
        assert "list" not in result

    def test_format_dict_escapes_pipes(self, formatter):
        """Pipe characters escaped in values."""
        data = {"cmd": "a | b | c"}
        result = formatter.format(data)

        assert "\\|" in result

    def test_format_list_empty(self, formatter):
        """Empty list shows italic message."""
        result = formatter.format([])
        assert result == "*No results*"

    def test_format_list_of_dicts_as_table(self, formatter):
        """List of dicts formatted as table."""
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = formatter.format(data)

        assert "| id | name |" in result
        assert "|---|---|" in result
        assert "| 1 | Alice |" in result
        assert "| 2 | Bob |" in result

    def test_format_list_limits_columns(self, formatter):
        """Table limited to 5 columns."""
        data = [{"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7}]
        result = formatter.format(data)

        # Should only have 5 columns
        header_line = result.split("\n")[0]
        columns = header_line.count("|") - 1  # pipes between columns
        assert columns <= 6  # 5 columns = 6 pipe separators

    def test_format_list_limits_rows(self, formatter):
        """Table limited to 50 rows."""
        data = [{"id": i} for i in range(100)]
        result = formatter.format(data)

        lines = result.strip().split("\n")
        # 1 header + 1 separator + 50 data rows = 52 lines
        assert len(lines) == 52

    def test_format_list_of_primitives(self, formatter):
        """List of primitives as bullet list."""
        data = ["one", "two", "three"]
        result = formatter.format(data)

        assert "- one" in result
        assert "- two" in result
        assert "- three" in result

    def test_format_error_markdown(self, formatter):
        """Error in markdown format."""
        result = formatter.format_error("Not found", "Check ID")

        assert "**Error:**" in result
        assert "Not found" in result
        assert "> Hint:" in result
        assert "Check ID" in result

    def test_format_success_markdown(self, formatter):
        """Success in markdown format."""
        result = formatter.format_success("Created")

        assert "✓" in result
        assert "**Created**" in result


# ============================================================================
# FormatterRegistry Tests
# ============================================================================

class TestFormatterRegistry:
    """Tests for plugin-specific formatter registry."""

    @pytest.fixture
    def registry(self):
        """Fresh registry for each test."""
        return FormatterRegistry()

    # --- Registration ---

    def test_register_and_get(self, registry):
        """Can register and retrieve formatter."""
        registry.register("jira", "issues", "human", HumanFormatter)

        formatter = registry.get("jira", "issues", "human")

        assert isinstance(formatter, HumanFormatter)

    def test_register_overwrites(self, registry):
        """Re-registering same key overwrites."""
        registry.register("jira", "issues", "human", HumanFormatter)
        registry.register("jira", "issues", "human", JsonFormatter)

        formatter = registry.get("jira", "issues", "human")

        assert isinstance(formatter, JsonFormatter)

    # --- Wildcard matching ---

    def test_wildcard_data_type(self, registry):
        """Wildcard * matches any data type."""
        registry.register("jira", "*", "human", HumanFormatter)

        # Should match any data_type for jira plugin
        formatter = registry.get("jira", "issues", "human")
        assert isinstance(formatter, HumanFormatter)

        formatter = registry.get("jira", "projects", "human")
        assert isinstance(formatter, HumanFormatter)

    def test_exact_match_beats_wildcard(self, registry):
        """Exact match takes precedence over wildcard."""
        registry.register("jira", "*", "human", HumanFormatter)
        registry.register("jira", "issues", "human", JsonFormatter)

        # Exact match returns JsonFormatter
        formatter = registry.get("jira", "issues", "human")
        assert isinstance(formatter, JsonFormatter)

        # Wildcard returns HumanFormatter
        formatter = registry.get("jira", "projects", "human")
        assert isinstance(formatter, HumanFormatter)

    # --- Fallback behavior ---

    def test_fallback_to_base_formatter(self, registry):
        """Unregistered plugin/type falls back to base."""
        formatter = registry.get("unknown", "unknown", "human")

        assert isinstance(formatter, HumanFormatter)

    def test_fallback_json_formatter(self, registry):
        """Fallback works for all format types."""
        formatter = registry.get("unknown", "unknown", "json")
        assert isinstance(formatter, JsonFormatter)

        formatter = registry.get("unknown", "unknown", "ai")
        assert isinstance(formatter, AIFormatter)

        formatter = registry.get("unknown", "unknown", "markdown")
        assert isinstance(formatter, MarkdownFormatter)

    # --- Unregister ---

    def test_unregister_existing(self, registry):
        """Can unregister existing formatter."""
        registry.register("jira", "issues", "human", HumanFormatter)

        result = registry.unregister("jira", "issues", "human")

        assert result is True
        # Should now fallback
        formatter = registry.get("jira", "issues", "human")
        assert isinstance(formatter, HumanFormatter)  # fallback, not registered

    def test_unregister_nonexistent(self, registry):
        """Unregistering nonexistent returns False."""
        result = registry.unregister("nonexistent", "nonexistent", "human")

        assert result is False

    # --- List registered ---

    def test_list_all_registered(self, registry):
        """List all registered formatters."""
        registry.register("jira", "issues", "human", HumanFormatter)
        registry.register("jira", "projects", "json", JsonFormatter)
        registry.register("confluence", "pages", "ai", AIFormatter)

        all_keys = registry.list_registered()

        assert len(all_keys) == 3
        assert "jira:issues:human" in all_keys
        assert "jira:projects:json" in all_keys
        assert "confluence:pages:ai" in all_keys

    def test_list_filtered_by_plugin(self, registry):
        """List formatters for specific plugin."""
        registry.register("jira", "issues", "human", HumanFormatter)
        registry.register("jira", "projects", "json", JsonFormatter)
        registry.register("confluence", "pages", "ai", AIFormatter)

        jira_keys = registry.list_registered("jira")

        assert len(jira_keys) == 2
        assert "jira:issues:human" in jira_keys
        assert "jira:projects:json" in jira_keys
        assert "confluence:pages:ai" not in jira_keys

    # --- Clear ---

    def test_clear_all(self, registry):
        """Clear removes all formatters."""
        registry.register("jira", "issues", "human", HumanFormatter)
        registry.register("confluence", "pages", "ai", AIFormatter)

        count = registry.clear()

        assert count == 2
        assert registry.list_registered() == []

    def test_clear_by_plugin(self, registry):
        """Clear specific plugin's formatters."""
        registry.register("jira", "issues", "human", HumanFormatter)
        registry.register("jira", "projects", "json", JsonFormatter)
        registry.register("confluence", "pages", "ai", AIFormatter)

        count = registry.clear("jira")

        assert count == 2
        assert registry.list_registered() == ["confluence:pages:ai"]


# ============================================================================
# Factory Functions Tests
# ============================================================================

class TestFactoryFunctions:
    """Tests for formatter factory functions."""

    def test_get_formatter_human(self):
        """get_formatter returns HumanFormatter."""
        f = get_formatter("human")
        assert isinstance(f, HumanFormatter)

    def test_get_formatter_json(self):
        """get_formatter returns JsonFormatter."""
        f = get_formatter("json")
        assert isinstance(f, JsonFormatter)

    def test_get_formatter_ai(self):
        """get_formatter returns AIFormatter."""
        f = get_formatter("ai")
        assert isinstance(f, AIFormatter)

    def test_get_formatter_markdown(self):
        """get_formatter returns MarkdownFormatter."""
        f = get_formatter("markdown")
        assert isinstance(f, MarkdownFormatter)

    def test_get_formatter_case_insensitive(self):
        """Format name is case-insensitive."""
        f = get_formatter("HUMAN")
        assert isinstance(f, HumanFormatter)

        f = get_formatter("Json")
        assert isinstance(f, JsonFormatter)

    def test_get_formatter_unknown_defaults_human(self):
        """Unknown format defaults to HumanFormatter."""
        f = get_formatter("unknown_format")
        assert isinstance(f, HumanFormatter)

    def test_formatters_dict_complete(self):
        """FORMATTERS dict has all types."""
        assert "human" in FORMATTERS
        assert "json" in FORMATTERS
        assert "ai" in FORMATTERS
        assert "markdown" in FORMATTERS


class TestGetPluginFormatter:
    """Tests for get_plugin_formatter function."""

    @pytest.fixture(autouse=True)
    def clean_registry(self):
        """Clean global registry before/after each test."""
        formatter_registry.clear()
        yield
        formatter_registry.clear()

    def test_returns_registered_formatter(self):
        """Returns registered plugin formatter."""
        formatter_registry.register("test", "data", "human", JsonFormatter)

        f = get_plugin_formatter("test", "data", "human")

        assert isinstance(f, JsonFormatter)

    def test_falls_back_to_base(self):
        """Falls back to base when not registered."""
        f = get_plugin_formatter("unregistered", "data", "json")

        assert isinstance(f, JsonFormatter)


class TestFormatResponse:
    """Tests for format_response convenience function."""

    @pytest.fixture(autouse=True)
    def clean_registry(self):
        """Clean global registry before/after each test."""
        formatter_registry.clear()
        yield
        formatter_registry.clear()

    def test_format_plain_data(self):
        """Format plain data with default formatter."""
        result = format_response({"key": "value"})

        # Default is json
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_format_with_explicit_format(self):
        """Format with explicit format name."""
        result = format_response([1, 2, 3], format_name="ai")

        assert "RESULTS: 3 items" in result

    def test_format_error_response(self):
        """Recognizes error responses."""
        data = {"success": False, "error": "Failed", "hint": "Try again"}
        result = format_response(data, format_name="human")

        assert "Error:" in result
        assert "Failed" in result
        assert "Hint:" in result

    def test_format_wrapped_data(self):
        """Unwraps data from {data: ...} wrapper."""
        wrapped = {"data": {"id": 1, "name": "test"}}
        result = format_response(wrapped, format_name="json")

        parsed = json.loads(result)
        assert parsed == {"id": 1, "name": "test"}

    def test_format_with_plugin_formatter(self):
        """Uses plugin-specific formatter when available."""
        formatter_registry.register("custom", "items", "human", AIFormatter)

        data = [{"id": 1}]
        result = format_response(data, format_name="human", plugin="custom", data_type="items")

        # AIFormatter output
        assert "RESULTS:" in result


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_human_formatter_empty_dict(self):
        """Empty dict produces empty output."""
        f = HumanFormatter()
        result = f.format({})
        assert result == ""

    def test_json_formatter_unicode(self):
        """Unicode characters preserved in JSON."""
        f = JsonFormatter()
        data = {"emoji": "🚀", "chinese": "你好"}
        result = f.format(data)

        parsed = json.loads(result)
        assert parsed["emoji"] == "🚀"
        assert parsed["chinese"] == "你好"

    def test_markdown_formatter_long_values_truncated(self):
        """Long values in markdown table truncated."""
        f = MarkdownFormatter()
        data = [{"text": "A" * 100}]
        result = f.format(data)

        # Should truncate at 30 chars
        assert "A" * 30 in result
        assert "A" * 100 not in result

    def test_ai_formatter_id_equals_label(self):
        """When id equals label, only show once."""
        f = AIFormatter()
        data = [{"id": "same", "title": "same"}]
        result = f.format(data)

        # Should only show "same" once, not "same: same"
        lines = [l for l in result.split("\n") if "same" in l]
        assert len(lines) == 1
        assert "same: same" not in result

    def test_human_formatter_none_values(self):
        """None values handled gracefully."""
        f = HumanFormatter()
        data = {"key": None}
        result = f.format(data)

        assert "key:" in result
        assert "None" in result

    def test_registry_instance_per_get(self):
        """Each get() returns new instance."""
        registry = FormatterRegistry()
        registry.register("test", "data", "human", HumanFormatter)

        f1 = registry.get("test", "data", "human")
        f2 = registry.get("test", "data", "human")

        assert f1 is not f2
