"""
Serena Daemon - HTTP server for fast CLI responses.

Keeps Python and httpx connections warm, reducing CLI latency
from ~200ms to ~50ms (client) + ~10ms (daemon overhead).

Architecture:
    serena (thin client) → HTTP → serena-daemon → Serena MCP server
"""

__version__ = "1.0.0"

DEFAULT_PORT = 9122
DEFAULT_HOST = "127.0.0.1"
PID_FILE = "/tmp/serena-daemon.pid"
IDLE_TIMEOUT = 1800  # 30 minutes
