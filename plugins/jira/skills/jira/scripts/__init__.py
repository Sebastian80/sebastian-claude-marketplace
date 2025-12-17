"""Jira bridge plugin - issue tracking and workflow automation."""

# Register Jira formatters on import
from .formatters import register_jira_formatters
register_jira_formatters()

from .plugin import JiraPlugin

__all__ = ["JiraPlugin"]
