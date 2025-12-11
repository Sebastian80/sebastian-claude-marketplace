"""
Formatters - Output formatting system.

The formatters module provides the registry mechanism.
Actual formatter implementations are in builtins/formatters.py.

Example:
    from ai_tool_bridge.formatters import formatter_registry, format_response

    # Format with global formatter
    output = format_response(data, "human")

    # Format with plugin-specific formatter
    output = format_response(data, "ai", plugin="jira", data_type="issue")
"""

from .registry import FormatterRegistry, format_response, formatter_registry

__all__ = [
    "FormatterRegistry",
    "formatter_registry",
    "format_response",
]
