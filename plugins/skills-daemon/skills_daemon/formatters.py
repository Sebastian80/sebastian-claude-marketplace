"""
Centralized response formatters for skills-daemon.

Provides extensible formatting system where plugins can:
- Register custom formatters for specific data types
- Extend base formatters with custom styling (colors, icons)
- Override standard formatters for their data types

Usage in plugins:

    from skills_daemon.formatters import (
        FormatterRegistry, HumanFormatter, formatter_registry
    )

    class MyIssueFormatter(HumanFormatter):
        # Custom icons
        ICONS = {**HumanFormatter.ICONS, "bug": "🐛", "feature": "✨"}

        def format(self, data):
            if isinstance(data, list):
                return self.format_issues(data)
            return super().format(data)

        def format_issues(self, issues):
            lines = []
            for issue in issues:
                icon = self.ICONS.get(issue.get("type"), "•")
                key = self.colorize(issue["key"], "cyan")
                lines.append(f"{icon} {key}: {issue['summary']}")
            return "\\n".join(lines)

    # Register for plugin
    formatter_registry.register("jira", "issues", "human", MyIssueFormatter)
"""

import json
from abc import ABC, abstractmethod
from typing import Any

from .colors import red, green, yellow, cyan, dim, bold, colored


# ═══════════════════════════════════════════════════════════════════════════════
# Base Formatter Classes
# ═══════════════════════════════════════════════════════════════════════════════

class BaseFormatter(ABC):
    """Abstract base for all formatters."""

    # Override these in subclasses for custom styling
    ICONS = {
        "success": "✓",
        "error": "✗",
        "warning": "⚠",
        "info": "ℹ",
        "bullet": "•",
        "arrow": "→",
    }

    @abstractmethod
    def format(self, data: Any) -> str:
        """Format data to string."""
        pass

    @abstractmethod
    def format_error(self, error: str, hint: str | None = None) -> str:
        """Format error message."""
        pass

    @abstractmethod
    def format_success(self, message: str, data: dict | None = None) -> str:
        """Format success message."""
        pass

    def icon(self, name: str, fallback: str = "•") -> str:
        """Get icon by name."""
        return self.ICONS.get(name, fallback)

    def colorize(self, text: str, color: str) -> str:
        """Apply color to text."""
        return colored(text, color)


class HumanFormatter(BaseFormatter):
    """Terminal-friendly output with ANSI colors and icons.

    Subclass this for plugin-specific human-readable formatting.
    Override ICONS dict for custom icons.
    """

    def format(self, data: Any) -> str:
        if isinstance(data, dict):
            return self._format_dict(data)
        elif isinstance(data, list):
            return self._format_list(data)
        return str(data)

    def _format_dict(self, d: dict, indent: int = 0) -> str:
        lines = []
        prefix = "  " * indent

        for k, v in d.items():
            key_str = bold(f"{k}:")
            if isinstance(v, dict):
                lines.append(f"{prefix}{key_str}")
                lines.append(self._format_dict(v, indent + 1))
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                lines.append(f"{prefix}{key_str} [{len(v)} items]")
            else:
                lines.append(f"{prefix}{key_str} {v}")
        return "\n".join(lines)

    def _format_list(self, items: list) -> str:
        if not items:
            return yellow("No results")

        lines = []
        for item in items:
            if isinstance(item, dict):
                id_val = item.get("id") or item.get("key") or item.get("name")
                label = item.get("title") or item.get("summary") or item.get("label") or item.get("description", "")

                if id_val and label and str(id_val) != str(label):
                    lines.append(f"{self.icon('bullet')} {cyan(str(id_val))}: {label}")
                elif id_val:
                    lines.append(f"{self.icon('bullet')} {id_val}")
                elif label:
                    lines.append(f"{self.icon('bullet')} {label}")
                else:
                    lines.append(f"{self.icon('bullet')} {item}")
            else:
                lines.append(f"{self.icon('bullet')} {item}")
        return "\n".join(lines)

    def format_error(self, error: str, hint: str | None = None) -> str:
        out = f"{red(self.icon('error'))} {red('Error:')} {error}"
        if hint:
            out += f"\n{dim(f'Hint: {hint}')}"
        return out

    def format_success(self, message: str, data: dict | None = None) -> str:
        return f"{green(self.icon('success'))} {message}"


class JsonFormatter(BaseFormatter):
    """Raw JSON output for programmatic use."""

    def format(self, data: Any) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    def format_error(self, error: str, hint: str | None = None) -> str:
        return json.dumps({"success": False, "error": error, "hint": hint}, indent=2)

    def format_success(self, message: str, data: dict | None = None) -> str:
        return json.dumps({"success": True, "message": message, **(data or {})}, indent=2)


class AIFormatter(BaseFormatter):
    """Optimized for LLM consumption - concise, no decoration."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict):
            return self._format_dict(data)
        elif isinstance(data, list):
            return self._format_list(data)
        return str(data)

    def _format_dict(self, d: dict, prefix: str = "") -> str:
        lines = []
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"{prefix}{k}:")
                lines.append(self._format_dict(v, prefix + "  "))
            elif isinstance(v, list):
                lines.append(f"{prefix}{k}: [{len(v)} items]")
            else:
                lines.append(f"{prefix}{k}: {v}")
        return "\n".join(lines)

    def _format_list(self, items: list) -> str:
        if not items:
            return "NO_RESULTS"

        lines = [f"RESULTS: {len(items)} items"]
        for item in items[:20]:
            if isinstance(item, dict):
                key = item.get("id") or item.get("key") or item.get("name") or "?"
                label = (item.get("title") or item.get("summary") or item.get("label") or "")[:60]
                if label and str(label) != str(key):
                    lines.append(f"- {key}: {label}")
                else:
                    lines.append(f"- {key}")
            else:
                lines.append(f"- {item}")

        if len(items) > 20:
            lines.append(f"... and {len(items) - 20} more")
        return "\n".join(lines)

    def format_error(self, error: str, hint: str | None = None) -> str:
        return f"ERROR: {error}" + (f" (hint: {hint})" if hint else "")

    def format_success(self, message: str, data: dict | None = None) -> str:
        return f"OK: {message}"


class MarkdownFormatter(BaseFormatter):
    """Markdown tables for documentation."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict):
            return self._format_dict(data)
        elif isinstance(data, list):
            return self._format_list(data)
        return str(data)

    def _format_dict(self, d: dict) -> str:
        lines = ["| Field | Value |", "|-------|-------|"]
        for k, v in d.items():
            if not isinstance(v, (dict, list)):
                v_str = str(v).replace("|", "\\|")
                lines.append(f"| {k} | {v_str} |")
        return "\n".join(lines)

    def _format_list(self, items: list) -> str:
        if not items:
            return "*No results*"

        if items and isinstance(items[0], dict):
            keys = list(items[0].keys())[:5]
            header = "| " + " | ".join(keys) + " |"
            sep = "|" + "|".join(["---"] * len(keys)) + "|"
            lines = [header, sep]

            for item in items[:50]:
                values = [str(item.get(k, ""))[:30].replace("|", "\\|") for k in keys]
                lines.append("| " + " | ".join(values) + " |")
            return "\n".join(lines)

        return "\n".join(f"- {item}" for item in items)

    def format_error(self, error: str, hint: str | None = None) -> str:
        return f"**Error:** {error}" + (f"\n\n> Hint: {hint}" if hint else "")

    def format_success(self, message: str, data: dict | None = None) -> str:
        return f"✓ **{message}**"


# ═══════════════════════════════════════════════════════════════════════════════
# Formatter Registry
# ═══════════════════════════════════════════════════════════════════════════════

class FormatterRegistry:
    """Registry for plugin-specific formatters.

    Key format: "{plugin}:{data_type}:{format}"
    Example: "jira:issues:human"

    Usage:
        formatter_registry.register("jira", "issues", "human", JiraIssueFormatter)
        formatter = formatter_registry.get("jira", "issues", "human")
    """

    def __init__(self):
        self._formatters: dict[str, type[BaseFormatter]] = {}

    def register(
        self,
        plugin: str,
        data_type: str,
        format_name: str,
        formatter_class: type[BaseFormatter],
    ) -> None:
        """Register a formatter for plugin/data_type/format."""
        key = f"{plugin}:{data_type}:{format_name}"
        self._formatters[key] = formatter_class

    def unregister(self, plugin: str, data_type: str, format_name: str) -> bool:
        """Unregister a formatter. Returns True if removed."""
        key = f"{plugin}:{data_type}:{format_name}"
        if key in self._formatters:
            del self._formatters[key]
            return True
        return False

    def get(self, plugin: str, data_type: str, format_name: str = "human") -> BaseFormatter:
        """Get formatter instance, falls back to base formatter."""
        # Exact match
        key = f"{plugin}:{data_type}:{format_name}"
        if key in self._formatters:
            return self._formatters[key]()

        # Plugin-wide formatter (any data type)
        key = f"{plugin}:*:{format_name}"
        if key in self._formatters:
            return self._formatters[key]()

        # Base formatter
        return get_formatter(format_name)

    def list_registered(self, plugin: str = None) -> list[str]:
        """List registered formatter keys."""
        if plugin:
            return [k for k in self._formatters.keys() if k.startswith(f"{plugin}:")]
        return list(self._formatters.keys())

    def clear(self, plugin: str = None) -> int:
        """Clear formatters, returns count removed."""
        if plugin:
            keys = [k for k in self._formatters.keys() if k.startswith(f"{plugin}:")]
            for k in keys:
                del self._formatters[k]
            return len(keys)
        count = len(self._formatters)
        self._formatters.clear()
        return count


# Global registry
formatter_registry = FormatterRegistry()


# ═══════════════════════════════════════════════════════════════════════════════
# Factory Functions
# ═══════════════════════════════════════════════════════════════════════════════

FORMATTERS = {
    "human": HumanFormatter,
    "json": JsonFormatter,
    "ai": AIFormatter,
    "markdown": MarkdownFormatter,
}


def get_formatter(format_name: str = "human") -> BaseFormatter:
    """Get base formatter instance by name."""
    return FORMATTERS.get(format_name.lower(), HumanFormatter)()


def get_plugin_formatter(plugin: str, data_type: str, format_name: str = "human") -> BaseFormatter:
    """Get plugin-specific formatter or base formatter."""
    return formatter_registry.get(plugin, data_type, format_name)


def format_response(
    data: Any,
    format_name: str = "json",
    plugin: str = None,
    data_type: str = None
) -> str:
    """Format response data with appropriate formatter."""
    if plugin and data_type:
        formatter = get_plugin_formatter(plugin, data_type, format_name)
    else:
        formatter = get_formatter(format_name)

    # Handle wrapped responses
    if isinstance(data, dict):
        if data.get("success") is False or "error" in data:
            return formatter.format_error(data.get("error", "Unknown error"), data.get("hint"))
        if "data" in data:
            return formatter.format(data["data"])

    return formatter.format(data)
