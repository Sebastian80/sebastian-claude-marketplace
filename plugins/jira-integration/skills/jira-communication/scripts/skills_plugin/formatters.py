"""
Jira-specific formatters for skills-daemon.

These extend the base formatters with Jira-aware formatting for:
- Issues
- Search results
- Transitions
- Comments
- Workflows
"""

import sys
from pathlib import Path
from typing import Any

# Import base formatters from daemon
SKILLS_DAEMON = Path(__file__).parent.parent.parent.parent.parent.parent / "skills-daemon"
if str(SKILLS_DAEMON) not in sys.path:
    sys.path.insert(0, str(SKILLS_DAEMON))

from skills_daemon.formatters import (
    BaseFormatter, HumanFormatter, JsonFormatter, AIFormatter, MarkdownFormatter,
    formatter_registry
)
from skills_daemon.colors import red, green, yellow, cyan, dim, bold


# ═══════════════════════════════════════════════════════════════════════════════
# Jira Issue Formatters
# ═══════════════════════════════════════════════════════════════════════════════

class JiraIssueHumanFormatter(HumanFormatter):
    """Human-friendly issue formatting."""

    def format(self, data: Any) -> str:
        if isinstance(data, dict) and "fields" in data:
            return self._format_issue(data)
        return super().format(data)

    def _format_issue(self, issue: dict) -> str:
        f = issue.get("fields", {})
        lines = [
            f"{bold('Key:')} {cyan(issue.get('key', '?'))}",
            f"{bold('Type:')} {f.get('issuetype', {}).get('name', '?')} | "
            f"{bold('Status:')} {f.get('status', {}).get('name', '?')} | "
            f"{bold('Priority:')} {f.get('priority', {}).get('name', '?')}",
            f"{bold('Summary:')} {f.get('summary', '?')}",
        ]
        if f.get("assignee"):
            lines.append(f"{bold('Assignee:')} {f['assignee'].get('displayName', '?')}")
        if f.get("description"):
            desc = f["description"][:400]
            if len(f["description"]) > 400:
                desc += "..."
            lines.append(f"{bold('Description:')}\n{desc}")
        return "\n".join(lines)


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
    """Human-friendly search results."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "fields" in data[0]:
            return self._format_search(data)
        return super().format(data)

    def _format_search(self, issues: list) -> str:
        if not issues:
            return yellow("No issues found")
        lines = []
        for i in issues:
            f = i.get("fields", {})
            key = i.get("key", "?")
            status = f.get("status", {}).get("name", "?")
            summary = f.get("summary", "?")[:50]
            lines.append(f"{cyan(f'{key:15}')} {status:15} {summary}")
        return "\n".join(lines)


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
    """Human-friendly transitions list."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "to" in data[0]:
            return self._format_transitions(data)
        return super().format(data)

    def _format_transitions(self, transitions: list) -> str:
        if not transitions:
            return yellow("No transitions available")
        lines = []
        for t in transitions:
            lines.append(f"  {t.get('id'):5} {t.get('name'):25} {dim('→')} {t.get('to', '?')}")
        return "\n".join(lines)


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
    """Human-friendly comments list."""

    def format(self, data: Any) -> str:
        if isinstance(data, list) and data and "author" in data[0]:
            return self._format_comments(data)
        return super().format(data)

    def _format_comments(self, comments: list) -> str:
        if not comments:
            return yellow("No comments")
        lines = []
        for c in comments:
            author = c.get("author", {}).get("displayName", "?")
            created = c.get("created", "?")[:10]
            body = c.get("body", "")[:120].replace("\n", " ")
            lines.append(f"{dim(created)} {cyan(author)}: {body}")
        return "\n".join(lines)


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
# Register Formatters
# ═══════════════════════════════════════════════════════════════════════════════

def register_jira_formatters():
    """Register all Jira formatters with the daemon.

    Uses 4-arg API: formatter_registry.register(plugin, data_type, format, FormatterClass)
    """
    # Issues
    formatter_registry.register("jira", "issue", "human", JiraIssueHumanFormatter)
    formatter_registry.register("jira", "issue", "ai", JiraIssueAIFormatter)
    formatter_registry.register("jira", "issue", "markdown", JiraIssueMarkdownFormatter)

    # Search
    formatter_registry.register("jira", "search", "human", JiraSearchHumanFormatter)
    formatter_registry.register("jira", "search", "ai", JiraSearchAIFormatter)
    formatter_registry.register("jira", "search", "markdown", JiraSearchMarkdownFormatter)

    # Transitions
    formatter_registry.register("jira", "transitions", "human", JiraTransitionsHumanFormatter)
    formatter_registry.register("jira", "transitions", "ai", JiraTransitionsAIFormatter)

    # Comments
    formatter_registry.register("jira", "comments", "human", JiraCommentsHumanFormatter)
    formatter_registry.register("jira", "comments", "ai", JiraCommentsAIFormatter)


# Auto-register on import
register_jira_formatters()
