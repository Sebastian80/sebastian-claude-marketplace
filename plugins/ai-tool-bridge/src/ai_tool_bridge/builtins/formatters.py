"""
Built-in Formatters - Default output format implementations.

Provides four standard formats:
- json: Raw JSON (for parsing)
- human: Colored terminal output (for humans)
- ai: Structured output (for LLM consumption)
- markdown: Markdown tables (for documentation)
"""

import json
from typing import Any

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


class JsonFormatter:
    """Raw JSON output formatter."""

    @property
    def name(self) -> str:
        return "json"

    @property
    def content_type(self) -> str:
        return "application/json"

    def format(self, data: Any) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    def format_error(self, error: str, hint: str | None = None) -> str:
        result = {"error": error}
        if hint:
            result["hint"] = hint
        return json.dumps(result, indent=2)

    def format_list(self, items: list[Any], item_type: str | None = None) -> str:
        return json.dumps(items, indent=2, ensure_ascii=False, default=str)


class HumanFormatter:
    """Human-readable colored terminal output."""

    @property
    def name(self) -> str:
        return "human"

    @property
    def content_type(self) -> str:
        return "text/plain"

    def format(self, data: Any) -> str:
        if data is None:
            return f"{GREEN}OK{RESET}"
        if isinstance(data, str):
            return data
        if isinstance(data, list):
            return self.format_list(data)
        if isinstance(data, dict):
            return self._format_dict(data)
        return str(data)

    def format_error(self, error: str, hint: str | None = None) -> str:
        result = f"{RED}Error:{RESET} {error}"
        if hint:
            result += f"\n{DIM}Hint: {hint}{RESET}"
        return result

    def format_list(self, items: list[Any], item_type: str | None = None) -> str:
        if not items:
            return f"{YELLOW}No results{RESET}"

        lines = []
        for item in items:
            if isinstance(item, dict):
                # Try to find a reasonable label
                label = (
                    item.get("key")
                    or item.get("name")
                    or item.get("id")
                    or item.get("title")
                    or "?"
                )
                desc = (
                    item.get("summary")
                    or item.get("description")
                    or item.get("value")
                    or ""
                )
                if isinstance(desc, str) and len(desc) > 60:
                    desc = desc[:57] + "..."
                lines.append(f"{CYAN}{label:30}{RESET} {DIM}{desc}{RESET}")
            else:
                lines.append(str(item))
        return "\n".join(lines)

    def _format_dict(self, data: dict) -> str:
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{BOLD}{key}:{RESET}")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            elif isinstance(value, list):
                lines.append(f"{BOLD}{key}:{RESET} [{len(value)} items]")
            else:
                lines.append(f"{BOLD}{key}:{RESET} {value}")
        return "\n".join(lines)


class AIFormatter:
    """Structured output optimized for LLM consumption.

    Features:
    - Prefixed keys for easy parsing
    - Concise format (no unnecessary whitespace)
    - Names instead of IDs where possible
    """

    @property
    def name(self) -> str:
        return "ai"

    @property
    def content_type(self) -> str:
        return "text/plain"

    def format(self, data: Any) -> str:
        if data is None:
            return "OK"
        if isinstance(data, str):
            return data
        if isinstance(data, list):
            return self.format_list(data)
        if isinstance(data, dict):
            return self._format_dict(data)
        return str(data)

    def format_error(self, error: str, hint: str | None = None) -> str:
        result = f"ERROR: {error}"
        if hint:
            result += f"\nHINT: {hint}"
        return result

    def format_list(self, items: list[Any], item_type: str | None = None) -> str:
        if not items:
            return "EMPTY_RESULT: No items found"

        prefix = item_type.upper() if item_type else "ITEM"
        lines = [f"FOUND: {len(items)} {item_type or 'items'}"]

        for i, item in enumerate(items[:20], 1):  # Limit to 20 items
            if isinstance(item, dict):
                # Extract key identifiers - check 'name' field for labels
                key = (
                    item.get("key")
                    or item.get("id")
                    or item.get("name")
                    or str(i)
                )
                # Get label/description - FIXED: check 'name' field
                label = (
                    item.get("name")  # Added: check name first
                    or item.get("title")
                    or item.get("summary")
                    or item.get("label")
                    or item.get("description")
                    or ""
                )
                if label:
                    lines.append(f"{prefix}[{key}]: {label}")
                else:
                    lines.append(f"{prefix}[{key}]")
            else:
                lines.append(f"{prefix}[{i}]: {item}")

        if len(items) > 20:
            lines.append(f"... and {len(items) - 20} more")

        return "\n".join(lines)

    def _format_dict(self, data: dict) -> str:
        lines = []
        for key, value in data.items():
            prefix = key.upper().replace("_", "-")
            if isinstance(value, dict):
                # Flatten nested dict
                for k, v in value.items():
                    lines.append(f"{prefix}-{k.upper()}: {v}")
            elif isinstance(value, list):
                lines.append(f"{prefix}: [{len(value)} items]")
            else:
                lines.append(f"{prefix}: {value}")
        return "\n".join(lines)


class MarkdownFormatter:
    """Markdown table output."""

    @property
    def name(self) -> str:
        return "markdown"

    @property
    def content_type(self) -> str:
        return "text/markdown"

    def format(self, data: Any) -> str:
        if data is None:
            return "*OK*"
        if isinstance(data, str):
            return data
        if isinstance(data, list):
            return self.format_list(data)
        if isinstance(data, dict):
            return self._format_dict(data)
        return str(data)

    def format_error(self, error: str, hint: str | None = None) -> str:
        result = f"**Error:** {error}"
        if hint:
            result += f"\n\n*Hint: {hint}*"
        return result

    def format_list(self, items: list[Any], item_type: str | None = None) -> str:
        if not items:
            return "*No results*"

        if not isinstance(items[0], dict):
            return "\n".join(f"- {item}" for item in items)

        # Get all keys from first few items
        keys = set()
        for item in items[:5]:
            if isinstance(item, dict):
                keys.update(item.keys())

        # Prioritize common keys
        priority = ["key", "id", "name", "summary", "status", "type"]
        columns = [k for k in priority if k in keys]
        columns.extend(k for k in sorted(keys) if k not in columns)
        columns = columns[:6]  # Limit columns

        # Build table
        lines = []
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")

        for item in items[:50]:  # Limit rows
            if isinstance(item, dict):
                row = []
                for col in columns:
                    val = item.get(col, "")
                    if isinstance(val, dict):
                        val = val.get("name", val.get("key", str(val)))
                    val = str(val).replace("|", "\\|")[:50]
                    row.append(val)
                lines.append("| " + " | ".join(row) + " |")

        if len(items) > 50:
            lines.append(f"\n*... and {len(items) - 50} more rows*")

        return "\n".join(lines)

    def _format_dict(self, data: dict) -> str:
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"**{key}:**")
                for k, v in value.items():
                    lines.append(f"- {k}: {v}")
            elif isinstance(value, list):
                lines.append(f"**{key}:** {len(value)} items")
            else:
                lines.append(f"**{key}:** {value}")
        return "\n".join(lines)


def register_builtin_formatters() -> None:
    """Register all built-in formatters with the global registry.

    Call this during bridge startup.
    """
    from ..formatters import formatter_registry

    formatter_registry.register_global("json", JsonFormatter())
    formatter_registry.register_global("human", HumanFormatter())
    formatter_registry.register_global("ai", AIFormatter())
    formatter_registry.register_global("markdown", MarkdownFormatter())
