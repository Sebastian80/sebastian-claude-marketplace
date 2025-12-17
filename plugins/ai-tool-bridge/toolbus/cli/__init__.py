"""
CLI - Command-line interface for the AI Tool Bridge.

The `bridge` command provides unified access to daemon management
and runtime operations.

Commands:
    bridge start [-f]    Start daemon (use -f for foreground)
    bridge stop          Stop daemon gracefully
    bridge restart       Restart daemon
    bridge status        Show status of daemon and components
    bridge health        Quick health check
    bridge plugins       List loaded plugins
    bridge connectors    List connectors and their circuit state
    bridge reconnect X   Force reconnect a connector

Example:
    # Start in background
    $ bridge start
    Bridge started (PID 12345)

    # Check status
    $ bridge status
    Bridge is running (PID 12345)
    AI Tool Bridge v1.0.0

    Plugins:
      * jira v1.0.0
      * confluence v1.0.0

    Connectors:
      * jira [closed]
      * confluence [closed]

    # Stop
    $ bridge stop
    Stopping bridge (PID 12345)...
    Bridge stopped
"""

from .main import main

__all__ = ["main"]
