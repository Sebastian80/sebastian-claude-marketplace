"""
CLI Parser - Argument parser for the bridge command.

Defines all subcommands and their arguments.
"""

import argparse

__all__ = ["create_parser"]


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="bridge",
        description="AI Tool Bridge - Unified interface for AI tool integrations",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # start
    start_parser = subparsers.add_parser("start", help="Start the daemon")
    start_parser.add_argument(
        "-f", "--foreground",
        action="store_true",
        help="Run in foreground (don't daemonize)",
    )

    # stop
    subparsers.add_parser("stop", help="Stop the daemon")

    # restart
    subparsers.add_parser("restart", help="Restart the daemon")

    # status
    subparsers.add_parser("status", help="Show daemon and component status")

    # health
    subparsers.add_parser("health", help="Quick health check")

    # plugins
    subparsers.add_parser("plugins", help="List loaded plugins")

    # reconnect
    reconnect_parser = subparsers.add_parser("reconnect", help="Reconnect a connector")
    reconnect_parser.add_argument("name", help="Connector name")

    # notify
    notify_parser = subparsers.add_parser("notify", help="Manage notifications")
    notify_parser.add_argument(
        "action",
        choices=["status", "enable", "disable", "test"],
        help="Notification action",
    )

    # deps
    deps_parser = subparsers.add_parser("deps", help="Manage plugin dependencies")
    deps_parser.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=["status", "sync", "force"],
        help="Action: status (show deps), sync (install if changed), force (reinstall all)",
    )

    # reload
    reload_parser = subparsers.add_parser("reload", help="Hot-reload plugins")
    reload_parser.add_argument(
        "plugin",
        nargs="?",
        default=None,
        help="Plugin name to reload (all plugins if not specified)",
    )

    return parser
