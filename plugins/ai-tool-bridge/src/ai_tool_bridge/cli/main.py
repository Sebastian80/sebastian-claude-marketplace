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
import time

import httpx

from ..config import BridgeConfig
from .client import BridgeClient, print_error, print_status
from .daemon import daemon_status, restart_daemon, start_daemon, stop_daemon

# Auto-start configuration
AUTO_START_TIMEOUT = 5.0  # max seconds to wait for daemon
AUTO_START_POLL_INTERVAL = 0.1  # seconds between health polls

# Built-in commands (not plugin names)
BUILTIN_COMMANDS = {"start", "stop", "restart", "status", "health", "plugins", "reconnect", "notify"}


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

        bridge jira comment KEY --text "Hello" -X POST
        -> POST /jira/comment/KEY with JSON body {"text": "Hello"}

    Args:
        args: Command line arguments starting with plugin name

    Returns:
        Exit code
    """
    config = BridgeConfig()

    # Parse plugin name and path segments
    plugin = args[0]
    remaining = args[1:]

    # Handle --help / -h flag: convert to /plugin/help request
    if not remaining or remaining == ["--help"] or remaining == ["-h"]:
        remaining = ["help"]

    # Separate path segments from options
    path_parts = []
    params = {}
    method = None  # Auto-detect if not specified

    i = 0
    while i < len(remaining):
        arg = remaining[i]
        if arg in ("-X", "--method"):
            # HTTP method flag (like curl)
            if i + 1 < len(remaining):
                method = remaining[i + 1].upper()
                i += 2
            else:
                print_error("-X/--method requires a value (GET, POST, PUT, PATCH, DELETE)")
                return 1
        elif arg.startswith("--"):
            # Option: --key value or --flag
            key = arg[2:]
            if i + 1 < len(remaining) and not remaining[i + 1].startswith("-"):
                params[key] = remaining[i + 1]
                i += 2
            else:
                params[key] = "true"
                i += 1
        elif arg.startswith("-") and len(arg) == 2:
            # Short option: -k value
            key = arg[1:]
            if i + 1 < len(remaining) and not remaining[i + 1].startswith("-"):
                params[key] = remaining[i + 1]
                i += 2
            else:
                params[key] = "true"
                i += 1
        else:
            # Path segment
            path_parts.append(arg)
            i += 1

    # Build URL
    path = "/" + plugin + ("/" + "/".join(path_parts) if path_parts else "")
    url = f"{config.bridge_url}{path}"

    # Auto-detect method if not specified
    if method is None:
        method = _detect_http_method(config, path, params)

    return _execute_plugin_request(url, method, params, config)


# Params that indicate read-only operations (always query params)
_QUERY_ONLY_PARAMS = {"format", "expand", "fields", "maxResults", "startAt", "limit", "includeArchived", "jql", "query"}


def _detect_http_method(config: BridgeConfig, path: str, params: dict) -> str:
    """Auto-detect HTTP method based on endpoint and params.

    Strategy:
    1. Try to get method from OpenAPI spec (cached)
    2. Fall back to heuristics based on params

    Args:
        config: Bridge configuration
        path: URL path
        params: Request parameters

    Returns:
        HTTP method (GET, POST, PUT, PATCH, DELETE)
    """
    # Try OpenAPI spec first
    method = _get_method_from_openapi(config, path, params)
    if method:
        return method

    # Fallback: if only query-like params, use GET
    param_keys = set(params.keys())
    if param_keys <= _QUERY_ONLY_PARAMS or not params:
        return "GET"

    # Has write-like params, default to POST
    return "POST"


def _get_method_from_openapi(config: BridgeConfig, path: str, params: dict) -> str | None:
    """Get HTTP method from OpenAPI spec.

    Args:
        config: Bridge configuration
        path: URL path
        params: Request parameters (used to match required params)

    Returns:
        HTTP method or None if not determinable
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{config.bridge_url}/openapi.json")
            if response.status_code != 200:
                return None

            spec = response.json()
            paths = spec.get("paths", {})

            # Normalize path for matching (replace actual values with param placeholders)
            # e.g., /jira/issue/PROJ-123 -> /jira/issue/{key}
            path_segments = path.strip("/").split("/")

            for spec_path, methods in paths.items():
                spec_segments = spec_path.strip("/").split("/")

                if len(spec_segments) != len(path_segments):
                    continue

                # Check if segments match (literal or placeholder)
                match = True
                for spec_seg, path_seg in zip(spec_segments, path_segments):
                    if spec_seg.startswith("{") and spec_seg.endswith("}"):
                        continue  # Placeholder matches anything
                    if spec_seg != path_seg:
                        match = False
                        break

                if match:
                    # Found matching path - determine method
                    available_methods = [m.upper() for m in methods.keys() if m in ("get", "post", "put", "patch", "delete")]

                    if len(available_methods) == 1:
                        return available_methods[0]

                    # Multiple methods available - use params to determine
                    if "GET" in available_methods and not (set(params.keys()) - _QUERY_ONLY_PARAMS):
                        return "GET"
                    if "POST" in available_methods:
                        return "POST"
                    if "PATCH" in available_methods:
                        return "PATCH"
                    if "PUT" in available_methods:
                        return "PUT"
                    if "DELETE" in available_methods:
                        return "DELETE"

                    return available_methods[0] if available_methods else None

    except Exception:
        pass

    return None


def _execute_plugin_request(url: str, method: str, params: dict, config: BridgeConfig) -> int:
    """Execute HTTP request to plugin, with auto-start on failure.

    Args:
        url: Full URL to plugin endpoint
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        params: Request parameters
        config: Bridge configuration

    Returns:
        Exit code
    """
    try:
        return _do_request(url, method, params)
    except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError, ConnectionRefusedError, OSError):
        # Daemon not running - auto-start and retry
        if not _auto_start_daemon(config):
            return 1
        try:
            return _do_request(url, method, params)
        except Exception as e:
            print_error(f"Request failed after auto-start: {e}")
            return 1
    except Exception as e:
        print_error(str(e))
        return 1


def _do_request(url: str, method: str, params: dict) -> int:
    """Execute the actual HTTP request.

    Args:
        url: Full URL to plugin endpoint
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        params: Request parameters

    Returns:
        Exit code
    """
    with httpx.Client(timeout=30.0) as client:
        # All params go as query string (FastAPI endpoints use Query params)
        if method == "GET":
            response = client.get(url, params=params)
        elif method == "POST":
            response = client.post(url, params=params)
        elif method == "PUT":
            response = client.put(url, params=params)
        elif method == "PATCH":
            response = client.patch(url, params=params)
        elif method == "DELETE":
            response = client.delete(url, params=params)
        else:
            print_error(f"Unsupported HTTP method: {method}")
            return 1

        # Handle response
        if response.status_code in (200, 201, 204):
            if response.status_code == 204 or not response.content:
                print("OK")
                return 0

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    data = response.json()
                    if isinstance(data, dict) and "data" in data:
                        print(json.dumps(data["data"], indent=2))
                    else:
                        print(json.dumps(data, indent=2))
                except json.JSONDecodeError:
                    print(response.text)
            else:
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


def _auto_start_daemon(config: BridgeConfig) -> bool:
    """Auto-start daemon and wait for it to be ready.

    Args:
        config: Bridge configuration

    Returns:
        True if daemon started and is ready
    """
    print("Bridge not running, starting...", file=sys.stderr)

    exit_code = start_daemon(config, foreground=False)
    if exit_code != 0:
        print_error("Failed to start bridge daemon")
        return False

    # Poll health endpoint until ready
    health_url = f"{config.bridge_url}/health"
    start_time = time.monotonic()

    while time.monotonic() - start_time < AUTO_START_TIMEOUT:
        try:
            with httpx.Client(timeout=1.0) as client:
                response = client.get(health_url)
                if response.status_code == 200:
                    return True
        except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError, ConnectionRefusedError, OSError):
            pass
        time.sleep(AUTO_START_POLL_INTERVAL)

    print_error(f"Daemon did not become ready within {AUTO_START_TIMEOUT}s")
    return False


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
                    cli_info = f" (cli: {p['cli']})" if p.get("cli") else ""
                    print(f"{state} {p['name']} v{p['version']}{cli_info}")
                    if p.get("description"):
                        print(f"    {p['description']}")
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
