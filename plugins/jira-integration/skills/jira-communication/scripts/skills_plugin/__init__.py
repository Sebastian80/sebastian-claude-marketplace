"""
Jira plugin for skills daemon.

Provides Jira issue tracking and workflow automation via persistent connection.

Features:
- Issue CRUD (get, create, update)
- JQL search with multiple output formats
- Smart workflow transitions (multi-step)
- Comments and issue links
- Web links (remote links)
- Persistent connection with auto-reconnect
- Health monitoring and self-healing

Usage:
    from skills_plugin import JiraPlugin
    plugin = JiraPlugin()
"""

import sys
from pathlib import Path

# Add skills-daemon to path for SkillPlugin base class
SKILLS_DAEMON = Path(__file__).parent.parent.parent.parent.parent.parent / "skills-daemon"
if str(SKILLS_DAEMON) not in sys.path:
    sys.path.insert(0, str(SKILLS_DAEMON))

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
