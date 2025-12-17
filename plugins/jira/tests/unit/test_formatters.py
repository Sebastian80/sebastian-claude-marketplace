"""
Tests for Jira-specific formatters.
"""

import sys
from pathlib import Path

import pytest

# Setup paths
PLUGIN_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PLUGIN_ROOT / "skills" / "jira" / "scripts"
AI_TOOL_BRIDGE = PLUGIN_ROOT.parent / "ai-tool-bridge" / "src"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(AI_TOOL_BRIDGE))

from formatters import (
    JiraIssueHumanFormatter,
    JiraIssueAIFormatter,
    JiraIssueMarkdownFormatter,
    JiraSearchHumanFormatter,
    JiraSearchAIFormatter,
    JiraSearchMarkdownFormatter,
    JiraTransitionsHumanFormatter,
    JiraTransitionsAIFormatter,
    JiraCommentsHumanFormatter,
    JiraCommentsAIFormatter,
    register_jira_formatters,
)
from ai_tool_bridge.formatters import formatter_registry


# ═══════════════════════════════════════════════════════════════════════════════
# Issue Formatter Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestJiraIssueHumanFormatter:
    """Tests for human-readable issue formatting."""

    @pytest.fixture
    def formatter(self):
        return JiraIssueHumanFormatter()

    def test_format_issue_basic(self, formatter, sample_issue):
        """Should format issue with key, type, status, priority."""
        result = formatter.format(sample_issue)

        assert "TEST-123" in result
        assert "Story" in result
        assert "In Progress" in result
        assert "High" in result

    def test_format_issue_includes_summary(self, formatter, sample_issue):
        """Should include issue summary."""
        result = formatter.format(sample_issue)
        assert "Sample test issue summary" in result

    def test_format_issue_includes_assignee(self, formatter, sample_issue):
        """Should include assignee name."""
        result = formatter.format(sample_issue)
        assert "John Doe" in result

    def test_format_issue_includes_description(self, formatter, sample_issue):
        """Should include truncated description."""
        result = formatter.format(sample_issue)
        assert "detailed description" in result

    def test_format_issue_without_assignee(self, formatter):
        """Should handle missing assignee."""
        issue = {
            "key": "TEST-1",
            "fields": {
                "summary": "No assignee",
                "status": {"name": "Open"},
                "issuetype": {"name": "Bug"},
                "priority": {"name": "Low"},
            }
        }
        result = formatter.format(issue)
        assert "TEST-1" in result
        assert "Assignee" not in result

    def test_format_non_issue_data(self, formatter):
        """Should fall back to base formatter for non-issue data."""
        result = formatter.format({"key": "value"})
        assert "key" in result.lower()


class TestJiraIssueAIFormatter:
    """Tests for AI-optimized issue formatting."""

    @pytest.fixture
    def formatter(self):
        return JiraIssueAIFormatter()

    def test_format_issue_concise(self, formatter, sample_issue):
        """Should produce concise output for AI consumption."""
        result = formatter.format(sample_issue)

        assert "ISSUE: TEST-123" in result
        assert "type: Story" in result
        assert "status: In Progress" in result

    def test_format_issue_no_ansi_codes(self, formatter, sample_issue):
        """AI formatter should not include ANSI color codes."""
        result = formatter.format(sample_issue)
        assert "\033[" not in result  # No ANSI escape sequences


class TestJiraIssueMarkdownFormatter:
    """Tests for Markdown issue formatting."""

    @pytest.fixture
    def formatter(self):
        return JiraIssueMarkdownFormatter()

    def test_format_issue_markdown_header(self, formatter, sample_issue):
        """Should produce Markdown header with key and summary."""
        result = formatter.format(sample_issue)
        assert "## TEST-123" in result
        assert "Sample test issue summary" in result

    def test_format_issue_markdown_table(self, formatter, sample_issue):
        """Should include Markdown table for fields."""
        result = formatter.format(sample_issue)
        assert "| Field | Value |" in result
        assert "|-------|-------|" in result

    def test_format_issue_includes_description_section(self, formatter, sample_issue):
        """Should include description as Markdown section."""
        result = formatter.format(sample_issue)
        assert "### Description" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Search Results Formatter Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestJiraSearchHumanFormatter:
    """Tests for human-readable search results."""

    @pytest.fixture
    def formatter(self):
        return JiraSearchHumanFormatter()

    def test_format_search_results(self, formatter, sample_search_results):
        """Should format search results as list."""
        result = formatter.format(sample_search_results)

        assert "TEST-1" in result
        assert "TEST-2" in result
        assert "First test issue" in result

    def test_format_empty_results(self, formatter):
        """Should handle empty results."""
        result = formatter.format([])
        # Falls back to parent formatter which returns yellow("No results")
        assert "No" in result  # "No issues found" or "No results"

    def test_format_non_search_data(self, formatter):
        """Should fall back for non-search data."""
        result = formatter.format([{"key": "TEST-1"}])
        assert "TEST-1" in result


class TestJiraSearchAIFormatter:
    """Tests for AI-optimized search results."""

    @pytest.fixture
    def formatter(self):
        return JiraSearchAIFormatter()

    def test_format_search_results_count(self, formatter, sample_search_results):
        """Should include result count for AI."""
        result = formatter.format(sample_search_results)
        assert "FOUND: 2 issues" in result

    def test_format_empty_results(self, formatter):
        """Should return specific marker for empty results."""
        result = formatter.format([])
        # Falls back to parent AIFormatter which returns "EMPTY_RESULT: No items found"
        assert "EMPTY_RESULT" in result or "No" in result

    def test_format_truncates_large_results(self, formatter):
        """Should truncate results beyond 30 items."""
        many_issues = [
            {"key": f"TEST-{i}", "fields": {"summary": f"Issue {i}", "status": {"name": "Open"}}}
            for i in range(50)
        ]
        result = formatter.format(many_issues)
        assert "... and 20 more" in result


class TestJiraSearchMarkdownFormatter:
    """Tests for Markdown search results."""

    @pytest.fixture
    def formatter(self):
        return JiraSearchMarkdownFormatter()

    def test_format_search_results_table(self, formatter, sample_search_results):
        """Should format as Markdown table."""
        result = formatter.format(sample_search_results)

        assert "| Key | Status | Priority | Summary |" in result
        assert "| TEST-1 |" in result

    def test_format_empty_results(self, formatter):
        """Should handle empty results with Markdown."""
        result = formatter.format([])
        # Falls back to parent MarkdownFormatter which returns "*No results*"
        assert "*No" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Transitions Formatter Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestJiraTransitionsHumanFormatter:
    """Tests for human-readable transitions."""

    @pytest.fixture
    def formatter(self):
        return JiraTransitionsHumanFormatter()

    def test_format_transitions_list(self, formatter, sample_transitions):
        """Should format transitions as list."""
        result = formatter.format(sample_transitions)

        assert "Start Progress" in result
        assert "In Progress" in result
        assert "Resolve" in result

    def test_format_empty_transitions(self, formatter):
        """Should handle empty transitions."""
        result = formatter.format([])
        # Empty list without "to" field falls back to parent which returns "No results"
        assert "No" in result


class TestJiraTransitionsAIFormatter:
    """Tests for AI-optimized transitions."""

    @pytest.fixture
    def formatter(self):
        return JiraTransitionsAIFormatter()

    def test_format_transitions_ai(self, formatter, sample_transitions):
        """Should format for AI with IDs."""
        result = formatter.format(sample_transitions)

        assert "AVAILABLE_TRANSITIONS:" in result
        assert "(id:11)" in result or "id:" in result

    def test_format_empty_transitions(self, formatter):
        """Should return marker for no transitions."""
        result = formatter.format([])
        # Empty list without "to" field falls back to parent which returns "EMPTY_RESULT"
        assert "EMPTY_RESULT" in result or "No" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Comments Formatter Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestJiraCommentsHumanFormatter:
    """Tests for human-readable comments."""

    @pytest.fixture
    def formatter(self):
        return JiraCommentsHumanFormatter()

    def test_format_comments_list(self, formatter, sample_comments):
        """Should format comments with author and body."""
        result = formatter.format(sample_comments)

        assert "Alice" in result
        assert "test comment" in result
        assert "Bob" in result

    def test_format_empty_comments(self, formatter):
        """Should handle empty comments."""
        result = formatter.format([])
        # Empty list without "author" field falls back to parent which returns "No results"
        assert "No" in result

    def test_format_long_comments(self, formatter):
        """Should handle long comment bodies."""
        comments = [{
            "author": {"displayName": "User"},
            "body": "X" * 200,
            "created": "2024-01-01T00:00:00.000+0000",
        }]
        result = formatter.format(comments)
        # Should include comment content and author
        assert "User" in result
        assert "X" in result


class TestJiraCommentsAIFormatter:
    """Tests for AI-optimized comments."""

    @pytest.fixture
    def formatter(self):
        return JiraCommentsAIFormatter()

    def test_format_comments_ai(self, formatter, sample_comments):
        """Should format for AI with count."""
        result = formatter.format(sample_comments)

        assert "COMMENTS: 2" in result
        assert "Alice:" in result

    def test_format_empty_comments(self, formatter):
        """Should return marker for no comments."""
        result = formatter.format([])
        # Empty list without "author" field falls back to parent which returns "EMPTY_RESULT"
        assert "EMPTY_RESULT" in result or "No" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Formatter Registry Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFormatterRegistry:
    """Tests for Jira formatter registration."""

    def test_jira_formatters_registered(self):
        """All Jira formatters should be registered."""
        # Force re-registration
        register_jira_formatters()

        # Check issue formatters (new API: get(format_name, plugin=..., data_type=...))
        assert formatter_registry.get("human", plugin="jira", data_type="issue") is not None
        assert formatter_registry.get("ai", plugin="jira", data_type="issue") is not None
        assert formatter_registry.get("markdown", plugin="jira", data_type="issue") is not None

        # Check search formatters
        assert formatter_registry.get("human", plugin="jira", data_type="search") is not None
        assert formatter_registry.get("ai", plugin="jira", data_type="search") is not None

        # Check transitions formatters
        assert formatter_registry.get("human", plugin="jira", data_type="transitions") is not None
        assert formatter_registry.get("ai", plugin="jira", data_type="transitions") is not None

        # Check comments formatters
        assert formatter_registry.get("human", plugin="jira", data_type="comments") is not None
        assert formatter_registry.get("ai", plugin="jira", data_type="comments") is not None

    def test_registered_formatters_are_correct_type(self):
        """Registered formatters should be correct types."""
        issue_formatter = formatter_registry.get("human", plugin="jira", data_type="issue")
        assert isinstance(issue_formatter, JiraIssueHumanFormatter)

        ai_formatter = formatter_registry.get("ai", plugin="jira", data_type="issue")
        assert isinstance(ai_formatter, JiraIssueAIFormatter)

    def test_fallback_to_base_formatter(self):
        """Should fall back to global formatter for unknown types."""
        from ai_tool_bridge.builtins.formatters import HumanFormatter
        # Register global formatter for fallback
        formatter_registry.register_global("human", HumanFormatter())

        formatter = formatter_registry.get("human", plugin="jira", data_type="unknown_type")
        # Should get global HumanFormatter, not None
        assert formatter is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Cases and Error Handling
# ═══════════════════════════════════════════════════════════════════════════════

class TestFormatterEdgeCases:
    """Tests for edge cases in formatters."""

    def test_issue_with_missing_fields(self):
        """Should handle issues with missing fields gracefully."""
        formatter = JiraIssueHumanFormatter()
        issue = {"key": "TEST-1", "fields": {}}
        result = formatter.format(issue)
        assert "TEST-1" in result

    def test_issue_with_empty_nested_dicts(self):
        """Should handle empty nested dicts in fields."""
        formatter = JiraIssueAIFormatter()
        issue = {
            "key": "TEST-1",
            "fields": {
                "summary": "",
                "status": {},
                "issuetype": {},
                "priority": {},
            }
        }
        result = formatter.format(issue)
        assert "TEST-1" in result

    def test_search_with_partial_fields(self):
        """Should handle search results with partial fields."""
        formatter = JiraSearchAIFormatter()
        issues = [
            {"key": "TEST-1", "fields": {"summary": "Has summary"}},
            {"key": "TEST-2", "fields": {}},
        ]
        result = formatter.format(issues)
        assert "TEST-1" in result
        assert "TEST-2" in result

    def test_transition_with_data(self):
        """Should format transitions with all fields."""
        formatter = JiraTransitionsHumanFormatter()
        transitions = [{"id": "1", "name": "Test Transition", "to": "Done"}]
        result = formatter.format(transitions)
        assert "Test Transition" in result
        assert "Done" in result

    def test_comment_with_newlines(self):
        """Should handle comments with newlines."""
        formatter = JiraCommentsHumanFormatter()
        comments = [{
            "author": {"displayName": "User"},
            "body": "Line 1\nLine 2\nLine 3",
            "created": "2024-01-01T00:00:00.000+0000",
        }]
        result = formatter.format(comments)
        # Newlines should be replaced with spaces
        assert "Line 1" in result
        assert "User" in result
