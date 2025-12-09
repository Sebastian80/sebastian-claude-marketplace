"""
Output formatters for Serena CLI.

Provides consistent, colorized output formatting for different result types.
Supports both human-readable and JSON output modes.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}

# Symbol kind names
KIND_NAMES = {
    1: "File",
    2: "Module",
    3: "Namespace",
    4: "Package",
    5: "Class",
    6: "Method",
    7: "Property",
    8: "Field",
    9: "Constructor",
    10: "Enum",
    11: "Interface",
    12: "Function",
    13: "Variable",
    14: "Constant",
}

# Short kind names for compact display
KIND_SHORT = {
    3: "ns",
    5: "class",
    6: "method",
    7: "prop",
    11: "iface",
    12: "func",
    13: "var",
    14: "const",
}


def _color(text: str, color: str) -> str:
    """Apply color to text if stdout is a TTY."""
    if not sys.stdout.isatty():
        return text
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def _bold(text: str) -> str:
    """Make text bold."""
    return _color(text, "bold")


def _dim(text: str) -> str:
    """Make text dim."""
    return _color(text, "dim")


class OutputFormatter:
    """
    Formats Serena results for terminal output.

    Supports both human-readable formatted output and JSON mode
    for scripting and piping.

    Attributes:
        json_mode: If True, output raw JSON instead of formatted text.
    """

    def __init__(self, json_mode: bool = False):
        """
        Initialize formatter.

        Args:
            json_mode: Output JSON instead of formatted text.
        """
        self.json_mode = json_mode

    def format_symbols(self, symbols: list[dict], show_body: bool = False) -> str:
        """
        Format symbol search results.

        Groups symbols by src/vendor and bundle for readability.

        Args:
            symbols: List of symbol dictionaries.
            show_body: Include symbol body in output.

        Returns:
            Formatted string.
        """
        if self.json_mode:
            return json.dumps(symbols, indent=2)

        if not symbols:
            return _dim("No symbols found")

        lines = []

        # Group by src vs vendor
        src_symbols = [s for s in symbols if not s.get("relative_path", "").startswith("vendor/")]
        vendor_symbols = [s for s in symbols if s.get("relative_path", "").startswith("vendor/")]

        for group_name, group_symbols in [("src", src_symbols), ("vendor", vendor_symbols)]:
            if not group_symbols:
                continue

            lines.append("")
            lines.append(_color(f"=== {group_name} ===", "cyan"))

            # Group by bundle (second path component)
            bundles: dict[str, list[dict]] = {}
            for sym in group_symbols:
                path = sym.get("relative_path", "")
                parts = path.split("/")
                if len(parts) >= 3:
                    bundle = "/".join(parts[1:3])
                else:
                    bundle = parts[0] if parts else "unknown"
                bundles.setdefault(bundle, []).append(sym)

            for bundle, bundle_symbols in sorted(bundles.items()):
                lines.append(_color(f"{bundle}/", "yellow"))

                for sym in bundle_symbols[:12]:  # Limit per bundle
                    kind = sym.get("kind", 0)
                    kind_str = KIND_SHORT.get(kind, str(kind)).ljust(8)
                    name = sym.get("name_path", "?")[:35].ljust(35)
                    path = sym.get("relative_path", "")
                    loc = sym.get("body_location", {})
                    line = loc.get("start_line", "?")

                    # Short path (last 2 components)
                    short_path = "/".join(path.split("/")[-2:])

                    lines.append(f"  {kind_str} {name} {_dim(f'{short_path}:{line}')}")

                    # Show body preview if requested
                    if show_body and sym.get("body"):
                        body_lines = sym["body"].strip().split("\n")[:3]
                        for bl in body_lines:
                            lines.append(f"    {_dim(bl[:80])}")

                if len(bundle_symbols) > 12:
                    lines.append(_dim(f"    ... +{len(bundle_symbols) - 12} more"))

        return "\n".join(lines)

    def format_refs(self, refs: list[dict], symbol: str, show_all: bool = False) -> str:
        """
        Format reference search results.

        Args:
            refs: List of reference dictionaries.
            symbol: The symbol being referenced.
            show_all: Show all references (default truncates).

        Returns:
            Formatted string.
        """
        if self.json_mode:
            return json.dumps(refs, indent=2)

        if not refs:
            return _dim(f"No references found for '{symbol}'")

        lines = [f"{len(refs)} references to '{_bold(symbol)}'", ""]

        # Group by file
        by_file: dict[str, list[dict]] = {}
        for ref in refs:
            path = ref.get("relative_path", "unknown")
            by_file.setdefault(path, []).append(ref)

        max_files = len(by_file) if show_all else 10
        for i, (path, file_refs) in enumerate(list(by_file.items())[:max_files]):
            lines.append(f"  {_color(path, 'cyan')}:")

            for ref in file_refs[:3]:
                loc = ref.get("body_location", {})
                line = loc.get("start_line", "?")
                ctx = ref.get("content_around_reference", "")

                # Extract highlighted line
                ctx_lines = [l.strip() for l in ctx.split("\n") if ">" in l[:5]]
                ctx_short = ctx_lines[0][4:64] if ctx_lines else ""

                if ctx_short:
                    lines.append(f"    :{line}  {ctx_short}")
                else:
                    lines.append(f"    :{line}")

            if len(file_refs) > 3:
                lines.append(_dim(f"    ... +{len(file_refs) - 3} more in this file"))

        remaining = len(by_file) - max_files
        if remaining > 0:
            lines.append("")
            lines.append(_dim(f"  ... +{remaining} more files (use --all to show all)"))

        return "\n".join(lines)

    def format_overview(self, symbols: list[dict], file: str) -> str:
        """
        Format file overview.

        Args:
            symbols: List of symbol dictionaries.
            file: File path being analyzed.

        Returns:
            Formatted string.
        """
        if self.json_mode:
            return json.dumps(symbols, indent=2)

        if not symbols:
            return _dim(f"No symbols found in '{file}'")

        lines = [f"{_bold(file)} ({len(symbols)} symbols)", ""]

        # Group by kind
        by_kind: dict[int, list[dict]] = {}
        for sym in symbols:
            kind = sym.get("kind", 0)
            by_kind.setdefault(kind, []).append(sym)

        # Order: classes, interfaces, functions, methods, properties, constants
        kind_order = [5, 11, 12, 6, 7, 14]

        for kind in kind_order:
            if kind not in by_kind:
                continue

            kind_symbols = by_kind[kind]
            kind_name = KIND_NAMES.get(kind, f"Kind {kind}")

            lines.append(f"  {_color(kind_name.upper(), 'yellow')}:")

            for sym in kind_symbols[:10]:
                name = sym.get("name_path", sym.get("name", "?"))
                loc = sym.get("body_location", {})
                start = loc.get("start_line", "?")
                end = loc.get("end_line")

                line_str = f":{start}-{end}" if end and end != start else f":{start}"
                lines.append(f"    {name}{_dim(line_str)}")

            if len(kind_symbols) > 10:
                lines.append(_dim(f"    ... +{len(kind_symbols) - 10} more"))

        return "\n".join(lines)

    def format_search(self, results: dict[str, list[str]], pattern: str) -> str:
        """
        Format search results.

        Args:
            results: Dict mapping file paths to matching lines.
            pattern: The search pattern.

        Returns:
            Formatted string.
        """
        if self.json_mode:
            return json.dumps(results, indent=2)

        if not results:
            return _dim(f"No matches for '{pattern}'")

        total = sum(len(v) for v in results.values())
        lines = [
            f"Pattern: '{_bold(pattern)}'",
            f"Found {total} matches in {len(results)} files",
            "",
        ]

        for path, matches in list(results.items())[:15]:
            lines.append(f"  {_color(path, 'cyan')}:")

            for match in matches[:5]:
                lines.append(f"    {match.strip()[:80]}")

            if len(matches) > 5:
                lines.append(_dim(f"    ... +{len(matches) - 5} more matches"))

        if len(results) > 15:
            lines.append("")
            lines.append(_dim(f"  ... +{len(results) - 15} more files"))

        return "\n".join(lines)

    def format_status(self, config: dict) -> str:
        """
        Format status output.

        Args:
            config: Configuration dictionary.

        Returns:
            Formatted string.
        """
        if self.json_mode:
            return json.dumps(config, indent=2)

        lines = [
            _bold("Serena Status"),
            "─" * 30,
            f"Project: {config.get('project', 'not activated')}",
            f"Root: {config.get('root', 'N/A')}",
        ]

        if "languages" in config:
            lines.append(f"Languages: {', '.join(config['languages'])}")

        if "indexed_files" in config:
            lines.append(f"Indexed files: {config['indexed_files']}")

        return "\n".join(lines)

    def format_memory_list(self, memories: list[str]) -> str:
        """Format memory list."""
        if self.json_mode:
            return json.dumps(memories, indent=2)

        if not memories:
            return _dim("No memories found")

        return "\n".join(f"  {m}" for m in memories)

    def format_error(self, message: str, hint: Optional[str] = None) -> str:
        """Format error message."""
        if self.json_mode:
            return json.dumps({"error": message, "hint": hint}, indent=2)

        lines = [_color(f"Error: {message}", "red")]
        if hint:
            lines.append(_dim(f"Hint: {hint}"))
        return "\n".join(lines)

    def format_success(self, message: str) -> str:
        """Format success message."""
        if self.json_mode:
            return json.dumps({"success": message}, indent=2)
        return _color(f"✓ {message}", "green")
