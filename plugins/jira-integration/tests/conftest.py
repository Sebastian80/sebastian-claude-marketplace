"""
Pytest fixtures for jira-integration tests.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

# Add paths for importing
PLUGIN_ROOT = Path(__file__).parent.parent
SKILLS_PLUGIN = PLUGIN_ROOT / "skills" / "jira-communication" / "scripts" / "skills_plugin"
AI_TOOL_BRIDGE = PLUGIN_ROOT.parent / "ai-tool-bridge" / "src"

sys.path.insert(0, str(SKILLS_PLUGIN.parent))
sys.path.insert(0, str(AI_TOOL_BRIDGE))


@pytest.fixture
def mock_jira_client():
    """Create a mock Jira client."""
    client = MagicMock()
    client.myself.return_value = {
        "displayName": "Test User",
        "emailAddress": "test@example.com",
    }
    client.issue.return_value = {
        "key": "TEST-123",
        "fields": {
            "summary": "Test issue",
            "status": {"name": "Open"},
            "issuetype": {"name": "Bug"},
            "priority": {"name": "High"},
            "assignee": {"displayName": "Test User"},
            "description": "Test description",
        },
    }
    client.jql.return_value = {
        "issues": [
            {
                "key": "TEST-1",
                "fields": {
                    "summary": "First issue",
                    "status": {"name": "Open"},
                    "priority": {"name": "High"},
                },
            },
            {
                "key": "TEST-2",
                "fields": {
                    "summary": "Second issue",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "Medium"},
                },
            },
        ]
    }
    client.get_issue_transitions.return_value = [
        {"id": "11", "name": "Start Progress", "to": "In Progress"},
        {"id": "21", "name": "Close", "to": "Done"},
    ]
    return client


@pytest.fixture
def sample_issue():
    """Sample Jira issue data."""
    return {
        "key": "TEST-123",
        "fields": {
            "summary": "Sample test issue summary",
            "status": {"name": "In Progress"},
            "issuetype": {"name": "Story"},
            "priority": {"name": "High"},
            "assignee": {"displayName": "John Doe"},
            "description": "This is a detailed description of the issue.",
        },
    }


@pytest.fixture
def sample_search_results():
    """Sample search results."""
    return [
        {
            "key": "TEST-1",
            "fields": {
                "summary": "First test issue",
                "status": {"name": "Open"},
                "priority": {"name": "High"},
            },
        },
        {
            "key": "TEST-2",
            "fields": {
                "summary": "Second test issue",
                "status": {"name": "Closed"},
                "priority": {"name": "Low"},
            },
        },
    ]


@pytest.fixture
def sample_transitions():
    """Sample transitions list."""
    return [
        {"id": "11", "name": "Start Progress", "to": "In Progress"},
        {"id": "21", "name": "Resolve", "to": "Resolved"},
        {"id": "31", "name": "Close", "to": "Done"},
    ]


@pytest.fixture
def sample_comments():
    """Sample comments list."""
    return [
        {
            "id": "1001",
            "author": {"displayName": "Alice"},
            "body": "This is a test comment from Alice.",
            "created": "2024-01-15T10:30:00.000+0000",
        },
        {
            "id": "1002",
            "author": {"displayName": "Bob"},
            "body": "Another comment from Bob.",
            "created": "2024-01-16T14:45:00.000+0000",
        },
    ]
