"""
CLI Main - Entry point for the `bridge` command.

Usage:
    bridge start [--foreground]   Start the daemon
    bridge stop                   Stop the daemon
    bridge restart                Restart the daemon
    bridge status                 Show daemon and component status
    bridge health                 Quick health check
    bridge plugins                List loaded plugins
    bridge connectors             List connectors and their state
    bridge <plugin> <path...>     Route to plugin endpoint
"""

import argparse
import json
import sys

import httpx

from ..config import BridgeConfig
from .client import BridgeClient, print_error, print_status
from .daemon import daemon_status, restart_daemon, start_daemon, stop_daemon

# Built-in commands (not plugin names)
BUILTIN_COMMANDS = {"start", "stop", "restart", "status", "health", "plugins", "connectors", "reconnect", "notify"}


def main(args: list[str] | None = None) -> int:
    """Main entry point for the bridge CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code
    """
    if args is None:
        args = sys.argv[1:]

    # Check if first arg is a plugin name (not a built-in command)
    if args and args[0] not in BUILTIN_COMMANDS and not args[0].startswith("-"):
        return run_plugin_command(args)

    parser = create_parser()
    parsed = parser.parse_args(args)

    config = BridgeConfig()

    if not hasattr(parsed, "command") or parsed.command is None:
        parser.print_help()
        return 0

    try:
        return run_command(parsed.command, parsed, config)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print_error(str(e))
        return 1


def run_plugin_command(args: list[str]) -> int:
    """Route command to a plugin via HTTP.

    Converts CLI args to HTTP request:
        bridge jira issue KEY --format human
        -> GET /jira/issue/KEY?format=human

    Args:
        args: Command line arguments starting with plugin name

    Returns:
        Exit code
    """
    config = BridgeConfig()

    # Parse plugin name and path segments
    plugin = args[0]
    remaining = args[1:]

    # Separate path segments from options
    path_parts = []
    query_params = {}

    i = 0
    while i < len(remaining):
        arg = remaining[i]
        if arg.startswith("--"):
            # Option: --key value or --flag
            key = arg[2:]
            if i + 1 < len(remaining) and not remaining[i + 1].startswith("-"):
                query_params[key] = remaining[i + 1]
                i += 2
            else:
                query_params[key] = "true"
                i += 1
        elif arg.startswith("-") and len(arg) == 2:
            # Short option: -k value
            key = arg[1:]
            if i + 1 < len(remaining) and not remaining[i + 1].startswith("-"):
                query_params[key] = remaining[i + 1]
                i += 2
            else:
                query_params[key] = "true"
                i += 1
        else:
            # Path segment
            path_parts.append(arg)
            i += 1

    # Build URL
    path = "/" + plugin + ("/" + "/".join(path_parts) if path_parts else "")
    url = f"{config.bridge_url}{path}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=query_params)

            # Handle response
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and "data" in data:
                            # Unwrap success response
                            print(json.dumps(data["data"], indent=2))
                        else:
                            print(json.dumps(data, indent=2))
                    except json.JSONDecodeError:
                        print(response.text)
                else:
                    # Plain text response (human/ai/markdown format)
                    print(response.text)
                return 0
            else:
                try:
                    error = response.json()
                    if "detail" in error:
                        print_error(error["detail"])
                    elif "error" in error:
                        print_error(error["error"])
                    else:
                        print_error(response.text)
                except json.JSONDecodeError:
                    print_error(f"HTTP {response.status_code}: {response.text}")
                return 1

    except httpx.ConnectError:
        print_error("Bridge is not running. Start it with: bridge start")
        return 1
    except Exception as e:
        print_error(str(e))
        return 1


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

    # connectors
    subparsers.add_parser("connectors", help="List connectors")

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

    return parser


def run_command(command: str, args: argparse.Namespace, config: BridgeConfig) -> int:
    """Run the specified command.

    Args:
        command: Command name
        args: Parsed arguments
        config: Bridge configuration

    Returns:
        Exit code
    """
    # Daemon management commands (don't need running daemon)
    if command == "start":
        return start_daemon(config, foreground=args.foreground)
    elif command == "stop":
        return stop_daemon(config)
    elif command == "restart":
        return restart_daemon(config)

    # Status check (works regardless of daemon state)
    if command == "status":
        # First check if daemon is running
        exit_code = daemon_status(config)
        if exit_code != 0:
            return exit_code

        # Then get detailed status from API
        with BridgeClient(config) as client:
            if client.is_running():
                status = client.status()
                print()
                print_status(status)
        return 0

    # Commands that require running daemon
    with BridgeClient(config) as client:
        if not client.is_running():
            print_error("Bridge is not running. Start it with: bridge start")
            return 1

        if command == "health":
            health = client.health()
            print(f"Status: {health.get('status', 'unknown')}")
            return 0 if health.get("status") == "ok" else 1

        elif command == "plugins":
            plugins = client.plugins()
            if not plugins:
                print("No plugins loaded")
            else:
                for p in plugins:
                    state = "[*]" if p.get("started") else "[ ]"
                    print(f"{state} {p['name']} v{p['version']}")
                    if p.get("description"):
                        print(f"    {p['description']}")
            return 0

        elif command == "connectors":
            result = client.connectors()
            connectors = result.get("connectors", {})
            if not connectors:
                print("No connectors registered")
            else:
                print(f"Status: {result.get('status', 'unknown')}")
                print(f"Total: {result.get('total', 0)}, Healthy: {result.get('healthy_count', 0)}")
                print()
                for name, c in connectors.items():
                    state = "[*]" if c.get("healthy") else "[ ]"
                    circuit = c.get("circuit_state", "unknown")
                    print(f"{state} {name}")
                    print(f"    Circuit: {circuit}")
                    if c.get("base_url"):
                        print(f"    URL: {c['base_url']}")
                    if c.get("last_error"):
                        print(f"    Last error: {c['last_error']}")
            return 0

        elif command == "reconnect":
            result = client.reconnect(args.name)
            print(f"Reconnected: {result.get('connector')}")
            return 0

        elif command == "notify":
            if args.action == "status":
                result = client.notifications_status()
                enabled = result.get("enabled", False)
                available = result.get("available", False)
                print(f"Notifications: {'enabled' if enabled else 'disabled'}")
                print(f"System support: {'available' if available else 'not available'}")
                return 0
            else:
                result = client.notifications_action(args.action)
                print(f"Notifications: {result.get('status', 'unknown')}")
                return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
