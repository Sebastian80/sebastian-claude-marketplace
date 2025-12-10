"""
Skills Daemon - Central daemon for Claude Code skills.

Provides a FastAPI-based HTTP server with plugin architecture.
Plugins are auto-discovered and provide their own endpoints.
"""

__version__ = "1.0.0"

# Import config for convenient access
from .config import config, DaemonConfig

# Re-export commonly used values (use config.* for paths)
DEFAULT_HOST = config.host
DEFAULT_PORT = config.port
