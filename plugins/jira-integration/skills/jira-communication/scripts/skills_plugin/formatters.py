"""
Jira-specific formatters.

Uses Rich library for beautiful terminal output with tables, panels, and colors.
Formatters are plugin-local (not imported from bridge).
"""

import json
import os
from io import StringIO
from pathlib import Path
from typing import Any

# Rich imports
from rich.console import Console


# ═══════════════════════════════════════════════════════════════════════════════
# Base Formatter Classes (plugin-local)
# ═══════════════════════════════════════════════════════════════════════════════

class Formatter:
    """Base formatter with default implementations."""

    def format(self, data: Any) -> str:
        """Format data as string. Override in subclasses."""
        return str(data)

    def format_error(self, message: str, hint: str | None = None) -> str:
        """Format error message."""
        if hint:
            return f"Error: {message}\nHint: {hint}"
        return f"Error: {message}"


class JsonFormatter(Formatter):
    """JSON output formatter."""

    def format(self, data: Any) -> str:
        return json.dumps(data, indent=2, default=str)


class HumanFormatter(Formatter):
    """Human-readable output formatter."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict):
            return json.dumps(data, indent=2, default=str)
        return str(data)


class AIFormatter(Formatter):
    """AI-optimized output formatter (compact, structured)."""

    def format(self, data: Any) -> str:
        return json.dumps(data, separators=(",", ":"), default=str)


class MarkdownFormatter(Formatter):
    """Markdown output formatter."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict):
            return f"```json\n{json.dumps(data, indent=2, default=str)}\n```"
        return str(data)


# ═══════════════════════════════════════════════════════════════════════════════
# Plugin-Local Formatter Registry
# ═══════════════════════════════════════════════════════════════════════════════

class FormatterRegistry:
    """Registry for plugin formatters."""

    def __init__(self):
        self._formatters: dict[str, Formatter] = {}

    def register(self, plugin: str, data_type: str, format_name: str, formatter: Formatter):
        """Register a formatter for plugin:data_type:format."""
        key = f"{plugin}:{data_type}:{format_name}"
        self._formatters[key] = formatter

    def get(self, format_name: str, plugin: str | None = None, data_type: str | None = None) -> Formatter | None:
        """Get formatter by format name, optionally filtered by plugin and data_type."""
        if plugin and data_type:
            key = f"{plugin}:{data_type}:{format_name}"
            if key in self._formatters:
                return self._formatters[key]
        # Fallback: try without data_type
        if plugin:
            for key, fmt in self._formatters.items():
                if key.startswith(f"{plugin}:") and key.endswith(f":{format_name}"):
                    return fmt
        return None


# Global plugin-local registry
formatter_registry = FormatterRegistry()
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


# ═══════════════════════════════════════════════════════════════════════════════
# Jira URL for Hyperlinks
# ═══════════════════════════════════════════════════════════════════════════════

def _get_jira_url() -> str:
    """Get Jira base URL from environment or config file."""
    # Try environment first
    url = os.environ.get("JIRA_URL", "")
    if url:
        return url.rstrip("/")

    # Try config file
    env_file = Path.home() / ".env.jira"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("JIRA_URL="):
                url = line.partition("=")[2].strip().strip('"').strip("'")
                return url.rstrip("/")
    return ""


def _make_issue_link(key: str, jira_url: str = "") -> Text:
    """Create a clickable hyperlink to a Jira issue.

    Returns Rich Text object with native link style. This allows Rich to:
    - Calculate cell widths correctly (excluding invisible escape codes)
    - Generate proper OSC 8 sequences itself
    - Handle truncation gracefully

    Args:
        key: Issue key (e.g., "PROJ-123")
        jira_url: Base Jira URL (auto-detected if empty)
    """
    if not jira_url:
        jira_url = _get_jira_url()

    text = Text(key)
    if jira_url:
        url = f"{jira_url}/browse/{key}"
        # Rich native link: "link URL" in style generates proper OSC 8
        text.stylize(f"bold cyan link {url}")
    else:
        text.stylize("bold cyan")
    return text


# ═══════════════════════════════════════════════════════════════════════════════
# Jira Icons & Status Colors
# ═══════════════════════════════════════════════════════════════════════════════

TYPE_ICONS = {
    # Bugs
    "bug": "🐛", "problem": "🐛", "fehler": "🐛", "defect": "🐛",
    # Tasks
    "task": "☑️", "aufgabe": "☑️",
    "technical task": "🔧", "sub: technical task": "🔧",
    # Stories & Features
    "story": "📗", "user story": "📗", "anforderung": "📗", "anforderung / user story": "📗",
    "new feature": "✨", "feature": "✨",
    # Epics
    "epic": "⚡",
    # Sub-tasks
    "subtask": "📎", "sub-task": "📎", "unteraufgabe": "📎",
    # Improvements
    "improvement": "💡", "verbesserung": "💡", "enhancement": "💡",
    # Research & Analysis
    "analyse": "🔬", "analysis": "🔬", "spike": "🔬", "research": "🔬",
    "investigation": "🔍", "sub: investigation": "🔍",
    # Operations
    "deployment": "🚀", "release": "🚀",
    # Training & Docs
    "training-education": "📚", "training": "📚", "documentation": "📝",
    # Support
    "support": "🎧", "question": "❓", "incident": "🚨",
}

STATUS_STYLES = {
    # Done (green)
    "done": ("✓", "green"), "fertig": ("✓", "green"), "closed": ("✓", "green"),
    "geschlossen": ("✓", "green"), "resolved": ("✓", "green"), "released": ("✓", "green"),
    "ready for deployment": ("✓", "green"),
    # In Progress (yellow)
    "in progress": ("►", "yellow"), "in arbeit": ("►", "yellow"),
    "in review": ("►", "yellow"), "in entwicklung": ("►", "yellow"),
    "development": ("►", "yellow"),
    # Waiting (yellow dim)
    "waiting": ("◦", "yellow"), "wartend": ("◦", "yellow"),
    "waiting for qa": ("◦", "yellow"), "awaiting approval": ("◦", "yellow"),
    # Blocked (red)
    "blocked": ("✗", "red"), "blockiert": ("✗", "red"),
    # Open/To Do (cyan)
    "to do": ("○", "cyan"), "zu erledigen": ("○", "cyan"), "open": ("○", "cyan"),
    "offen": ("○", "cyan"), "new": ("○", "cyan"), "neu": ("○", "cyan"),
    "backlog": ("·", "dim"),
    # Review
    "review": ("◎", "yellow"), "code review": ("◎", "yellow"),
    "analyse": ("◎", "cyan"),
}

PRIORITY_STYLES = {
    "blocker": ("▲▲", "bold red"), "critical": ("▲▲", "bold red"),
    "highest": ("▲", "red"), "high": ("▲", "yellow"),
    "medium": ("─", "dim"), "low": ("▼", "dim"), "lowest": ("▼▼", "dim"),
}


def _get_type_icon(type_name: str) -> str:
    if not type_name:
        return "•"
    return TYPE_ICONS.get(type_name.lower(), "•")


def _get_status_style(status_name: str) -> tuple[str, str]:
    if not status_name:
        return ("?", "dim")
    return STATUS_STYLES.get(status_name.lower(), ("•", "dim"))


def _get_priority_style(priority_name: str) -> tuple[str, str]:
    if not priority_name:
        return ("", "dim")
    return PRIORITY_STYLES.get(priority_name.lower(), ("", "dim"))


def _render_to_string(renderable) -> str:
    """Render a Rich object to ANSI string."""
    console = Console(file=StringIO(), force_terminal=True, width=80)
    console.print(renderable)
    return console.file.getvalue().rstrip()


# ═══════════════════════════════════════════════════════════════════════════════
# Jira Issue Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraIssueHumanFormatter(HumanFormatter):
    """Human-friendly issue formatting using Rich panels."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict) and "fields" in data:
            return self._format_issue(data)
        return super().format(data)

    def _format_issue(self, issue: dict) -> str:
        f = issue.get("fields", {})
        key = issue.get("key", "?")
        type_name = f.get("issuetype", {}).get("name", "?")
        status_name = f.get("status", {}).get("name", "?")
        priority_name = f.get("priority", {}).get("name", "")
        summary = f.get("summary", "?")

        type_icon = _get_type_icon(type_name)
        status_icon, status_style = _get_status_style(status_name)
        priority_icon, priority_style = _get_priority_style(priority_name)

        # Build content with summary
        from rich.console import Group
        parts = []

        # Summary
        parts.append(Text(summary, style="bold"))
        parts.append(Text(""))  # Blank line

        # Metadata grid
        meta = Table(show_header=False, box=None, padding=(0, 2), expand=False)
        meta.add_column("Field", style="bold dim", width=10)
        meta.add_column("Value")

        # Status with icon and color
        status_text = Text(f"{status_icon} {status_name}", style=status_style)
        meta.add_row("Status", status_text)

        # Priority with icon
        if priority_name:
            priority_text = Text(f"{priority_icon} {priority_name}", style=priority_style)
            meta.add_row("Priority", priority_text)

        # Assignee
        if f.get("assignee"):
            meta.add_row("Assignee", Text(f["assignee"].get("displayName", "?"), style="cyan"))

        # Reporter
        if f.get("reporter"):
            meta.add_row("Reporter", Text(f["reporter"].get("displayName", "?"), style="dim"))

        # Labels
        if f.get("labels"):
            meta.add_row("Labels", Text(", ".join(f["labels"][:5]), style="magenta"))

        parts.append(meta)

        # Add description if present
        if f.get("description"):
            parts.append(Text(""))  # Blank line
            parts.append(Text("Description", style="bold dim"))
            desc = f["description"][:500]
            if len(f["description"]) > 500:
                desc += "..."
            parts.append(Text(desc, style="dim"))

        # Create panel with title (clickable issue key via Rich Text)
        title = Text.assemble(
            (f"{type_icon}  ", ""),
            _make_issue_link(key),
            (f"  {type_name}", "dim"),
        )

        panel = Panel(
            Group(*parts),
            title=title,
            title_align="left",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(1, 2),
        )

        return _render_to_string(panel)


class JiraIssueAIFormatter(AIFormatter):
    """AI-optimized issue formatting."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict) and "fields" in data:
            return self._format_issue(data)
        return super().format(data)

    def _format_issue(self, issue: dict) -> str:
        f = issue.get("fields", {})
        lines = [
            f"ISSUE: {issue.get('key')}",
            f"type: {f.get('issuetype', {}).get('name')}",
            f"status: {f.get('status', {}).get('name')}",
            f"priority: {f.get('priority', {}).get('name')}",
            f"summary: {f.get('summary')}",
        ]
        if f.get("assignee"):
            lines.append(f"assignee: {f['assignee'].get('displayName')}")
        if f.get("description"):
            lines.append(f"description: {f['description'][:600]}")
        return "\n".join(lines)


class JiraIssueMarkdownFormatter(MarkdownFormatter):
    """Markdown issue formatting."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict) and "fields" in data:
            return self._format_issue(data)
        return super().format(data)

    def _format_issue(self, issue: dict) -> str:
        f = issue.get("fields", {})
        lines = [
            f"## {issue.get('key')}: {f.get('summary', '?')}",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Type | {f.get('issuetype', {}).get('name', '?')} |",
            f"| Status | {f.get('status', {}).get('name', '?')} |",
            f"| Priority | {f.get('priority', {}).get('name', '?')} |",
        ]
        if f.get("assignee"):
            lines.append(f"| Assignee | {f['assignee'].get('displayName', '?')} |")
        if f.get("description"):
            lines.extend(["", "### Description", "", f.get("description", "")[:600]])
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Jira Search Results Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraSearchHumanFormatter(HumanFormatter):
    """Human-friendly search results using Rich tables."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "fields" in data[0]:
            return self._format_search(data)
        return super().format(data)

    def _format_search(self, issues: list) -> str:
        if not issues:
            return _render_to_string(Text("No issues found", style="yellow"))

        table = Table(
            title=f"Search Results ({len(issues)} issues)",
            box=box.ROUNDED,
            header_style="bold",
            border_style="dim",
            title_style="bold",
        )

        # no_wrap=True prevents emoji from wrapping incorrectly
        table.add_column("", width=3, justify="center", no_wrap=True)  # Type icon (emoji width)
        table.add_column("Key", min_width=12, no_wrap=True)  # Clickable links
        table.add_column("Status", min_width=16, no_wrap=True)
        table.add_column("Summary", max_width=40)

        for i in issues:
            f = i.get("fields", {})
            key = i.get("key", "?")
            type_name = f.get("issuetype", {}).get("name", "")
            status_name = f.get("status", {}).get("name", "?")
            summary = f.get("summary", "?")[:40]

            type_icon = _get_type_icon(type_name)
            status_icon, status_style = _get_status_style(status_name)

            status_text = Text(f"{status_icon} {status_name}", style=status_style)

            # Use Rich native link style - Rich handles OSC 8 generation and cell width
            table.add_row(type_icon, _make_issue_link(key), status_text, summary)

        return _render_to_string(table)


class JiraSearchAIFormatter(AIFormatter):
    """AI-optimized search results."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and isinstance(data[0], dict) and "fields" in data[0]:
            return self._format_search(data)
        return super().format(data)

    def _format_search(self, issues: list) -> str:
        if not issues:
            return "NO_ISSUES_FOUND"
        lines = [f"FOUND: {len(issues)} issues"]
        for i in issues[:30]:
            f = i.get("fields", {})
            status = f.get("status", {}).get("name", "?")
            summary = f.get("summary", "?")[:60]
            lines.append(f"- {i.get('key')}: [{status}] {summary}")
        if len(issues) > 30:
            lines.append(f"... and {len(issues) - 30} more")
        return "\n".join(lines)


class JiraSearchMarkdownFormatter(MarkdownFormatter):
    """Markdown search results table."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and isinstance(data[0], dict) and "fields" in data[0]:
            return self._format_search(data)
        return super().format(data)

    def _format_search(self, issues: list) -> str:
        if not issues:
            return "*No issues found*"
        lines = [
            "| Key | Status | Priority | Summary |",
            "|-----|--------|----------|---------|",
        ]
        for i in issues[:50]:
            f = i.get("fields", {})
            lines.append(
                f"| {i.get('key')} | {f.get('status', {}).get('name', '?')} | "
                f"{f.get('priority', {}).get('name', '?')} | {f.get('summary', '?')[:40]} |"
            )
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Jira Transitions Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraTransitionsHumanFormatter(HumanFormatter):
    """Human-friendly transitions using Rich tables."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "to" in data[0]:
            return self._format_transitions(data)
        return super().format(data)

    def _format_transitions(self, transitions: list) -> str:
        if not transitions:
            return _render_to_string(Text("No transitions available", style="yellow"))

        table = Table(
            title="Available Transitions",
            box=box.SIMPLE,
            header_style="bold",
            title_style="bold",
        )

        table.add_column("Action", style="cyan", min_width=25)
        table.add_column("→", justify="center", width=3)
        table.add_column("Target Status", min_width=20)

        for t in transitions:
            name = t.get('name', '?')
            to_status = t.get('to', '?')
            status_icon, status_style = _get_status_style(to_status)
            status_text = Text(f"{status_icon} {to_status}", style=status_style)

            table.add_row(name, "→", status_text)

        return _render_to_string(table)


class JiraTransitionsAIFormatter(AIFormatter):
    """AI-optimized transitions."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "to" in data[0]:
            return self._format_transitions(data)
        return super().format(data)

    def _format_transitions(self, transitions: list) -> str:
        if not transitions:
            return "NO_TRANSITIONS_AVAILABLE"
        lines = ["AVAILABLE_TRANSITIONS:"]
        for t in transitions:
            lines.append(f"- {t.get('name')} (id:{t.get('id')}) -> {t.get('to')}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Jira Comments Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraCommentsHumanFormatter(HumanFormatter):
    """Human-friendly comments using Rich panels."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "author" in data[0]:
            return self._format_comments(data)
        return super().format(data)

    def _format_comments(self, comments: list) -> str:
        if not comments:
            return _render_to_string(Text("No comments", style="yellow"))

        output = []
        output.append(_render_to_string(Text(f"Comments ({len(comments)})", style="bold")))
        output.append("")

        for c in comments:
            author = c.get("author", {}).get("displayName", "?")
            created = c.get("created", "?")[:10]
            body = c.get("body", "")[:300]
            if len(c.get("body", "")) > 300:
                body += "..."

            # Create mini panel for each comment
            title = Text()
            title.append(author, style="cyan bold")
            title.append(f"  {created}", style="dim")

            panel = Panel(
                body,
                title=title,
                title_align="left",
                box=box.SIMPLE,
                padding=(0, 1),
            )
            output.append(_render_to_string(panel))

        return "\n".join(output)


class JiraCommentsAIFormatter(AIFormatter):
    """AI-optimized comments."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "author" in data[0]:
            return self._format_comments(data)
        return super().format(data)

    def _format_comments(self, comments: list) -> str:
        if not comments:
            return "NO_COMMENTS"
        lines = [f"COMMENTS: {len(comments)}"]
        for c in comments[:10]:
            author = c.get("author", {}).get("displayName", "?")
            body = c.get("body", "")[:100].replace("\n", " ")
            lines.append(f"- {author}: {body}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Link Types Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraLinkTypesHumanFormatter(HumanFormatter):
    """Human-friendly link types using Rich tables."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "inward" in data[0]:
            return self._format_linktypes(data)
        return super().format(data)

    def _format_linktypes(self, types: list) -> str:
        if not types:
            return _render_to_string(Text("No link types found", style="yellow"))

        table = Table(
            title=f"Link Types ({len(types)})",
            box=box.ROUNDED,
            header_style="bold",
            border_style="dim",
        )

        table.add_column("Name", style="cyan bold", min_width=15)
        table.add_column("Outward", min_width=20)
        table.add_column("Inward", min_width=20)

        for lt in types:
            table.add_row(
                lt.get("name", "?"),
                lt.get("outward", "?"),
                lt.get("inward", "?"),
            )

        return _render_to_string(table)


class JiraLinkTypesAIFormatter(AIFormatter):
    """AI-optimized link types."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "inward" in data[0]:
            return self._format_linktypes(data)
        return super().format(data)

    def _format_linktypes(self, types: list) -> str:
        if not types:
            return "NO_LINK_TYPES"
        lines = [f"LINK_TYPES: {len(types)}"]
        for lt in types:
            lines.append(f"- {lt.get('name')}: {lt.get('outward')} / {lt.get('inward')}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Issue Links Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraLinksHumanFormatter(HumanFormatter):
    """Human-friendly issue links using Rich tables."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and (not data or "type" in data[0] if data else True):
            return self._format_links(data)
        return super().format(data)

    def _format_links(self, links: list) -> str:
        if not links:
            return _render_to_string(Text("No links found", style="yellow"))

        table = Table(
            title=f"Issue Links ({len(links)})",
            box=box.ROUNDED,
            header_style="bold",
            border_style="dim",
        )

        table.add_column("Relationship", min_width=20)
        table.add_column("Issue", style="cyan", min_width=12)
        table.add_column("Summary", max_width=35)
        table.add_column("Status", min_width=12)

        for link in links:
            link_type = link.get("type", {})

            # Determine direction and get linked issue
            if "outwardIssue" in link:
                direction = link_type.get("outward", "?")
                linked = link.get("outwardIssue", {})
            else:
                direction = link_type.get("inward", "?")
                linked = link.get("inwardIssue", {})

            key = linked.get("key", "?")
            summary = linked.get("fields", {}).get("summary", "?")[:35]
            status = linked.get("fields", {}).get("status", {}).get("name", "?")
            status_icon, status_style = _get_status_style(status)

            table.add_row(
                direction,
                _make_issue_link(key),
                summary,
                Text(f"{status_icon} {status}", style=status_style),
            )

        return _render_to_string(table)


class JiraLinksAIFormatter(AIFormatter):
    """AI-optimized issue links."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and (not data or "type" in data[0] if data else True):
            return self._format_links(data)
        return super().format(data)

    def _format_links(self, links: list) -> str:
        if not links:
            return "NO_LINKS"
        lines = [f"LINKS: {len(links)}"]
        for link in links:
            link_type = link.get("type", {})
            if "outwardIssue" in link:
                direction = link_type.get("outward", "?")
                linked = link.get("outwardIssue", {})
            else:
                direction = link_type.get("inward", "?")
                linked = link.get("inwardIssue", {})
            key = linked.get("key", "?")
            summary = linked.get("fields", {}).get("summary", "?")[:50]
            lines.append(f"- {direction} {key}: {summary}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Watchers Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraWatchersHumanFormatter(HumanFormatter):
    """Human-friendly watchers list."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict) and "watchers" in data:
            return self._format_watchers(data)
        return super().format(data)

    def _format_watchers(self, data: dict) -> str:
        watchers = data.get("watchers", [])
        count = data.get("watchCount", len(watchers))

        if not watchers:
            return _render_to_string(Text(f"No watchers (count: {count})", style="yellow"))

        table = Table(
            title=f"Watchers ({count})",
            box=box.SIMPLE,
            header_style="bold",
        )

        table.add_column("Name", style="cyan", min_width=25)
        table.add_column("Username", style="dim", min_width=20)

        for w in watchers:
            table.add_row(
                w.get("displayName", "?"),
                w.get("name", w.get("key", "?")),
            )

        return _render_to_string(table)


class JiraWatchersAIFormatter(AIFormatter):
    """AI-optimized watchers list."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict) and "watchers" in data:
            return self._format_watchers(data)
        return super().format(data)

    def _format_watchers(self, data: dict) -> str:
        watchers = data.get("watchers", [])
        count = data.get("watchCount", len(watchers))
        if not watchers:
            return f"WATCHERS: 0 (count: {count})"
        lines = [f"WATCHERS: {count}"]
        for w in watchers:
            lines.append(f"- {w.get('displayName', '?')} ({w.get('name', '?')})")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Attachments Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraAttachmentsHumanFormatter(HumanFormatter):
    """Human-friendly attachments list."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and (not data or "filename" in data[0] if data else True):
            return self._format_attachments(data)
        return super().format(data)

    def _format_attachments(self, attachments: list) -> str:
        if not attachments:
            return _render_to_string(Text("No attachments", style="yellow"))

        table = Table(
            title=f"Attachments ({len(attachments)})",
            box=box.SIMPLE,
            header_style="bold",
        )

        table.add_column("ID", style="dim", width=8)
        table.add_column("Filename", style="cyan", min_width=25)
        table.add_column("Size", justify="right", width=10)
        table.add_column("Author", min_width=15)

        for a in attachments:
            size = a.get("size", 0)
            if size > 1024 * 1024:
                size_str = f"{size / (1024*1024):.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"

            table.add_row(
                str(a.get("id", "?")),
                a.get("filename", "?"),
                size_str,
                a.get("author", {}).get("displayName", "?"),
            )

        return _render_to_string(table)


class JiraAttachmentsAIFormatter(AIFormatter):
    """AI-optimized attachments list."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and (not data or "filename" in data[0] if data else True):
            return self._format_attachments(data)
        return super().format(data)

    def _format_attachments(self, attachments: list) -> str:
        if not attachments:
            return "NO_ATTACHMENTS"
        lines = [f"ATTACHMENTS: {len(attachments)}"]
        for a in attachments:
            lines.append(f"- {a.get('filename', '?')} (id:{a.get('id')}, {a.get('size', 0)} bytes)")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Web Links Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraWebLinksHumanFormatter(HumanFormatter):
    """Human-friendly web links list."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and (not data or "object" in data[0] if data else True):
            return self._format_weblinks(data)
        return super().format(data)

    def _format_weblinks(self, links: list) -> str:
        if not links:
            return _render_to_string(Text("No web links", style="yellow"))

        table = Table(
            title=f"Web Links ({len(links)})",
            box=box.SIMPLE,
            header_style="bold",
        )

        table.add_column("ID", style="dim", width=8)
        table.add_column("Title", style="cyan", min_width=30)
        table.add_column("URL", max_width=60, overflow="fold")

        for link in links:
            obj = link.get("object", {})
            table.add_row(
                str(link.get("id", "?")),
                obj.get("title", "?"),
                obj.get("url", "?"),  # No truncation - let Rich handle overflow
            )

        return _render_to_string(table)


class JiraWebLinksAIFormatter(AIFormatter):
    """AI-optimized web links list."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and (not data or "object" in data[0] if data else True):
            return self._format_weblinks(data)
        return super().format(data)

    def _format_weblinks(self, links: list) -> str:
        if not links:
            return "NO_WEBLINKS"
        lines = [f"WEBLINKS: {len(links)}"]
        for link in links:
            obj = link.get("object", {})
            lines.append(f"- {obj.get('title', '?')}: {obj.get('url', '?')}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Worklogs Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraWorklogsHumanFormatter(HumanFormatter):
    """Human-friendly worklogs list."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and (not data or "timeSpent" in data[0] if data else True):
            return self._format_worklogs(data)
        return super().format(data)

    def _format_worklogs(self, worklogs: list) -> str:
        if not worklogs:
            return _render_to_string(Text("No worklogs", style="yellow"))

        table = Table(
            title=f"Worklogs ({len(worklogs)})",
            box=box.SIMPLE,
            header_style="bold",
        )

        table.add_column("ID", style="dim", width=8)
        table.add_column("Author", style="cyan", min_width=20)
        table.add_column("Time", min_width=10)
        table.add_column("Date", min_width=12)
        table.add_column("Comment", max_width=30)

        for w in worklogs:
            table.add_row(
                str(w.get("id", "?")),
                w.get("author", {}).get("displayName", "?"),
                w.get("timeSpent", "?"),
                w.get("started", "?")[:10],
                (w.get("comment", "") or "")[:30],
            )

        return _render_to_string(table)


class JiraWorklogsAIFormatter(AIFormatter):
    """AI-optimized worklogs list."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and (not data or "timeSpent" in data[0] if data else True):
            return self._format_worklogs(data)
        return super().format(data)

    def _format_worklogs(self, worklogs: list) -> str:
        if not worklogs:
            return "NO_WORKLOGS"
        lines = [f"WORKLOGS: {len(worklogs)}"]
        for w in worklogs:
            author = w.get("author", {}).get("displayName", "?")
            time = w.get("timeSpent", "?")
            date = w.get("started", "?")[:10]
            lines.append(f"- {author}: {time} on {date}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Register Formatters
# ═══════════════════════════════════════════════════════════════════════════════

def register_jira_formatters():
    """Register all Jira formatters with the bridge."""
    # Issue formatters
    formatter_registry.register("jira", "issue", "human", JiraIssueHumanFormatter())
    formatter_registry.register("jira", "issue", "ai", JiraIssueAIFormatter())
    formatter_registry.register("jira", "issue", "markdown", JiraIssueMarkdownFormatter())

    # Search formatters
    formatter_registry.register("jira", "search", "human", JiraSearchHumanFormatter())
    formatter_registry.register("jira", "search", "ai", JiraSearchAIFormatter())
    formatter_registry.register("jira", "search", "markdown", JiraSearchMarkdownFormatter())

    # Transitions formatters
    formatter_registry.register("jira", "transitions", "human", JiraTransitionsHumanFormatter())
    formatter_registry.register("jira", "transitions", "ai", JiraTransitionsAIFormatter())

    # Comments formatters
    formatter_registry.register("jira", "comments", "human", JiraCommentsHumanFormatter())
    formatter_registry.register("jira", "comments", "ai", JiraCommentsAIFormatter())

    # Link types formatters
    formatter_registry.register("jira", "linktypes", "human", JiraLinkTypesHumanFormatter())
    formatter_registry.register("jira", "linktypes", "ai", JiraLinkTypesAIFormatter())

    # Issue links formatters
    formatter_registry.register("jira", "links", "human", JiraLinksHumanFormatter())
    formatter_registry.register("jira", "links", "ai", JiraLinksAIFormatter())

    # Watchers formatters
    formatter_registry.register("jira", "watchers", "human", JiraWatchersHumanFormatter())
    formatter_registry.register("jira", "watchers", "ai", JiraWatchersAIFormatter())

    # Attachments formatters
    formatter_registry.register("jira", "attachments", "human", JiraAttachmentsHumanFormatter())
    formatter_registry.register("jira", "attachments", "ai", JiraAttachmentsAIFormatter())

    # Web links formatters
    formatter_registry.register("jira", "weblinks", "human", JiraWebLinksHumanFormatter())
    formatter_registry.register("jira", "weblinks", "ai", JiraWebLinksAIFormatter())

    # Worklogs formatters
    formatter_registry.register("jira", "worklogs", "human", JiraWorklogsHumanFormatter())
    formatter_registry.register("jira", "worklogs", "ai", JiraWorklogsAIFormatter())
