"""
Centralized response formatters for skills-daemon.

Plugins can register custom formatters for their data types.
The daemon handles format selection via query param: ?format=human|json|ai|markdown

Architecture:
- Base formatters here (error, success, generic)
- Plugins register type-specific formatters via registry
- CLI requests format via Accept header or query param
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Type, Callable
from functools import wraps

from .colors import red, green, yellow, cyan, dim, bold, colored


# ═══════════════════════════════════════════════════════════════════════════════
# Format Registry
# ═══════════════════════════════════════════════════════════════════════════════

class FormatterRegistry:
    """Registry for plugin-specific formatters."""

    def __init__(self):
        self._formatters: Dict[str, Dict[str, Type["BaseFormatter"]]] = {}
        # plugin_name -> {data_type -> formatter_class}

    def register(self, plugin: str, data_type: str, formatter_class: Type["BaseFormatter"]):
        """Register a formatter for a plugin's data type."""
        if plugin not in self._formatters:
            self._formatters[plugin] = {}
        self._formatters[plugin][data_type] = formatter_class

    def get(self, plugin: str, data_type: str) -> Optional[Type["BaseFormatter"]]:
        """Get formatter for plugin's data type."""
        return self._formatters.get(plugin, {}).get(data_type)

    def list_types(self, plugin: str) -> list:
        """List registered data types for a plugin."""
        return list(self._formatters.get(plugin, {}).keys())


# Global registry
registry = FormatterRegistry()


# ═══════════════════════════════════════════════════════════════════════════════
# Base Formatter Classes
# ═══════════════════════════════════════════════════════════════════════════════

class BaseFormatter(ABC):
    """Abstract base for all formatters."""

    @abstractmethod
    def format(self, data: Any) -> str:
        """Format data to string."""
        pass

    @abstractmethod
    def format_error(self, error: str, hint: Optional[str] = None) -> str:
        """Format error message."""
        pass

    @abstractmethod
    def format_success(self, message: str, data: Optional[dict] = None) -> str:
        """Format success message."""
        pass


class HumanFormatter(BaseFormatter):
    """Terminal-friendly output with ANSI colors.

    Provides color constants as class attributes for subclasses:
    RED, GREEN, YELLOW, CYAN, DIM, BOLD, RESET
    """

    # ANSI color codes (always enabled - CLI handles TTY detection)
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    def format(self, data: Any) -> str:
        if isinstance(data, dict):
            return self._format_dict(data)
        elif isinstance(data, list):
            return self._format_list(data)
        return str(data)

    def _format_dict(self, d: dict) -> str:
        lines = []
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"{bold(k + ':')}")
                for k2, v2 in v.items():
                    lines.append(f"  {k2}: {v2}")
            else:
                lines.append(f"{bold(k + ':')} {v}")
        return "\n".join(lines)

    def _format_list(self, items: list) -> str:
        if not items:
            return yellow("No results")
        lines = []
        for item in items:
            if isinstance(item, dict):
                # Generic - no domain-specific assumptions
                id_val = item.get("id", item.get("name", ""))
                label = item.get("title", item.get("label", item.get("name", "")))
                if id_val and label and id_val != label:
                    lines.append(f"{cyan(id_val)}: {label}")
                elif id_val:
                    lines.append(f"• {id_val}")
                elif label:
                    lines.append(f"• {label}")
                else:
                    lines.append(str(item))
            else:
                lines.append(str(item))
        return "\n".join(lines)

    def format_error(self, error: str, hint: Optional[str] = None) -> str:
        out = f"{red('Error:')} {error}"
        if hint:
            out += f"\n{dim(f'Hint: {hint}')}"
        return out

    def format_success(self, message: str, data: Optional[dict] = None) -> str:
        return f"{green('✓')} {message}"


class JsonFormatter(BaseFormatter):
    """Raw JSON output for programmatic use."""

    def format(self, data: Any) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    def format_error(self, error: str, hint: Optional[str] = None) -> str:
        return json.dumps({"error": error, "hint": hint}, indent=2)

    def format_success(self, message: str, data: Optional[dict] = None) -> str:
        return json.dumps({"success": True, "message": message, **(data or {})}, indent=2)


class AIFormatter(BaseFormatter):
    """Optimized for LLM consumption - concise, structured, no decoration."""

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
        for item in items[:20]:  # Limit for LLM context
            if isinstance(item, dict):
                # Generic key detection - no domain-specific assumptions
                key = item.get("id", item.get("name", "?"))
                # Generic label detection
                label = item.get("title", item.get("label", item.get("name", "")))[:60]
                if label and label != key:
                    lines.append(f"- {key}: {label}")
                else:
                    lines.append(f"- {key}")
            else:
                lines.append(f"- {item}")
        if len(items) > 20:
            lines.append(f"... and {len(items) - 20} more")
        return "\n".join(lines)

    def format_error(self, error: str, hint: Optional[str] = None) -> str:
        return f"ERROR: {error}" + (f" (hint: {hint})" if hint else "")

    def format_success(self, message: str, data: Optional[dict] = None) -> str:
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
                lines.append(f"| {k} | {v} |")
        return "\n".join(lines)

    def _format_list(self, items: list) -> str:
        if not items:
            return "*No results*"

        # Try to auto-detect columns from first item
        if items and isinstance(items[0], dict):
            keys = list(items[0].keys())[:5]  # Max 5 columns
            header = "| " + " | ".join(keys) + " |"
            sep = "|" + "|".join(["---"] * len(keys)) + "|"
            lines = [header, sep]
            for item in items[:50]:  # Limit rows
                row = "| " + " | ".join(str(item.get(k, ""))[:30] for k in keys) + " |"
                lines.append(row)
            return "\n".join(lines)

        return "\n".join(f"- {item}" for item in items)

    def format_error(self, error: str, hint: Optional[str] = None) -> str:
        return f"**Error:** {error}" + (f"\n\n> Hint: {hint}" if hint else "")

    def format_success(self, message: str, data: Optional[dict] = None) -> str:
        return f"✓ **{message}**"


# ═══════════════════════════════════════════════════════════════════════════════
# Formatter Factory
# ═══════════════════════════════════════════════════════════════════════════════

FORMATTERS = {
    "human": HumanFormatter,
    "json": JsonFormatter,
    "ai": AIFormatter,
    "markdown": MarkdownFormatter,
}


def get_formatter(format_name: str = "human") -> BaseFormatter:
    """Get formatter instance by name."""
    formatter_class = FORMATTERS.get(format_name.lower(), HumanFormatter)
    return formatter_class()


def get_plugin_formatter(plugin: str, data_type: str, format_name: str = "human") -> BaseFormatter:
    """Get plugin-specific formatter or fall back to base."""
    # Check if plugin has custom formatter for this type
    custom_class = registry.get(plugin, data_type)
    if custom_class:
        return custom_class()
    # Fall back to base formatter
    return get_formatter(format_name)


# ═══════════════════════════════════════════════════════════════════════════════
# Response Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def format_response(data: Any, format_name: str = "json", plugin: str = None, data_type: str = None) -> str:
    """Format response data.

    Args:
        data: The data to format
        format_name: One of human, json, ai, markdown
        plugin: Optional plugin name for custom formatters
        data_type: Optional data type for plugin-specific formatting
    """
    if plugin and data_type:
        formatter = get_plugin_formatter(plugin, data_type, format_name)
    else:
        formatter = get_formatter(format_name)

    # Handle wrapped responses
    if isinstance(data, dict):
        if data.get("success") is False or "error" in data:
            return formatter.format_error(
                data.get("error", "Unknown error"),
                data.get("hint")
            )
        if "data" in data:
            return formatter.format(data["data"])

    return formatter.format(data)
