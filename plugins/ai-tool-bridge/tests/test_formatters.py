"""Tests for formatter registry and builtins."""

import pytest

from ai_tool_bridge.builtins.formatters import (
    AIFormatter,
    HumanFormatter,
    JsonFormatter,
    MarkdownFormatter,
    register_builtin_formatters,
)
from ai_tool_bridge.formatters import FormatterRegistry


class TestFormatterRegistry:
    """Test formatter registry operations."""

    def test_register_global_formatter(self):
        """Can register a global formatter."""
        registry = FormatterRegistry()
        formatter = JsonFormatter()

        registry.register_global("json", formatter)

        assert registry.get("json") is formatter

    def test_register_plugin_specific_formatter(self):
        """Can register plugin-specific formatter."""
        registry = FormatterRegistry()
        global_formatter = JsonFormatter()
        plugin_formatter = JsonFormatter()

        registry.register_global("json", global_formatter)
        registry.register("jira", "issue", "json", plugin_formatter)

        # Global lookup
        assert registry.get("json") is global_formatter
        # Specific lookup
        assert registry.get("json", plugin="jira", data_type="issue") is plugin_formatter

    def test_fallback_to_global(self):
        """Falls back to global formatter when specific not found."""
        registry = FormatterRegistry()
        global_formatter = JsonFormatter()
        registry.register_global("json", global_formatter)

        # No specific formatter for jira/issue, should return global
        result = registry.get("json", plugin="jira", data_type="issue")

        assert result is global_formatter

    def test_available_formats(self):
        """List all registered global formats."""
        registry = FormatterRegistry()
        registry.register_global("json", JsonFormatter())
        registry.register_global("human", HumanFormatter())

        formats = registry.available_formats()

        assert "json" in formats
        assert "human" in formats


class TestJsonFormatter:
    """Test JSON formatter."""

    def test_format_dict(self):
        """Formats dict as JSON."""
        formatter = JsonFormatter()
        data = {"key": "value", "number": 42}

        result = formatter.format(data)

        assert '"key": "value"' in result
        assert '"number": 42' in result

    def test_format_list(self):
        """Formats list of items."""
        formatter = JsonFormatter()
        items = [{"id": 1}, {"id": 2}]

        result = formatter.format_list(items)

        assert "[" in result
        assert '"id": 1' in result

    def test_format_error(self):
        """Formats error message."""
        formatter = JsonFormatter()

        result = formatter.format_error("Something went wrong", "test_error")

        assert "test_error" in result
        assert "Something went wrong" in result


class TestHumanFormatter:
    """Test human-readable formatter."""

    def test_format_dict(self):
        """Formats dict with readable output."""
        formatter = HumanFormatter()
        data = {"name": "Test", "status": "active"}

        result = formatter.format(data)

        assert "name" in result.lower() or "Test" in result
        assert "status" in result.lower() or "active" in result

    def test_format_list(self):
        """Formats list with numbered items."""
        formatter = HumanFormatter()
        items = [{"name": "Item 1"}, {"name": "Item 2"}]

        result = formatter.format_list(items)

        assert "Item 1" in result or "1" in result


class TestAIFormatter:
    """Test AI-optimized formatter."""

    def test_format_with_labels(self):
        """Uses name/title/summary fields as labels."""
        formatter = AIFormatter()
        data = {"name": "Test Issue", "id": 123, "status": "open"}

        result = formatter.format(data)

        # Should include name prominently
        assert "Test Issue" in result

    def test_format_list_extracts_labels(self):
        """Format list extracts name field for labels."""
        formatter = AIFormatter()
        items = [
            {"name": "First", "id": 1},
            {"name": "Second", "id": 2},
        ]

        result = formatter.format_list(items)

        assert "First" in result
        assert "Second" in result


class TestMarkdownFormatter:
    """Test Markdown formatter."""

    def test_format_dict(self):
        """Formats dict as markdown."""
        formatter = MarkdownFormatter()
        data = {"key": "value"}

        result = formatter.format(data)

        # Should contain some markdown formatting
        assert "key" in result
        assert "value" in result

    def test_format_list_as_table(self):
        """Formats list as markdown table."""
        formatter = MarkdownFormatter()
        items = [{"col1": "a", "col2": "b"}]

        result = formatter.format_list(items)

        assert "col1" in result
        assert "col2" in result


class TestBuiltinRegistration:
    """Test builtin formatter registration."""

    def test_register_builtins(self):
        """Registers all builtin formatters."""
        from ai_tool_bridge.formatters import formatter_registry

        # Clear existing
        formatter_registry.clear()

        register_builtin_formatters()

        assert formatter_registry.get("json") is not None
        assert formatter_registry.get("human") is not None
        assert formatter_registry.get("ai") is not None
        assert formatter_registry.get("markdown") is not None
