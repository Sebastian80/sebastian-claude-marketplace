"""
Jira plugin for AI Tool Bridge.

Provides Jira issue tracking and workflow automation via JiraConnector.
"""

import sys
from pathlib import Path

# Add lib/ to path for shared Jira utilities
LIB_PATH = Path(__file__).parent.parent
if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))

# Register Jira formatters on import
from skills_plugin.formatters import register_jira_formatters
register_jira_formatters()

# Export plugin class
from skills_plugin.plugin import JiraPlugin

__all__ = ["JiraPlugin"]
