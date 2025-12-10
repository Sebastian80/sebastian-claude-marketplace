"""
Skills Daemon - Central daemon for Claude Code skills.

Provides a FastAPI-based HTTP server with plugin architecture.
Plugins are auto-discovered and provide their own endpoints.
"""

__version__ = "1.0.0"

# Configuration
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9100
IDLE_TIMEOUT = 1800  # 30 minutes
PID_FILE = "/tmp/skills-daemon.pid"
LOG_FILE = "/tmp/skills-daemon.log"
