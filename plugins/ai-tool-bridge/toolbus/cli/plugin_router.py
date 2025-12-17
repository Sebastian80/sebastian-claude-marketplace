"""
Plugin Router - Routes CLI commands to plugins via HTTP.

Converts CLI arguments to HTTP requests and executes them.
Auto-starts daemon if not running.
"""

import json
import sys
import time
from typing import TYPE_CHECKING

import httpx

from .client import print_error
from .daemon import start_daemon

if TYPE_CHECKING:
    from ..config import BridgeConfig

__all__ = ["run_plugin_command"]

# Auto-start configuration
AUTO_START_TIMEOUT = 5.0  # max seconds to wait for daemon
AUTO_START_POLL_INTERVAL = 0.1  # seconds between health polls

# Connection errors that indicate daemon not running (DRY: used in multiple places)
CONNECTION_ERRORS = (
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.ReadError,
    ConnectionRefusedError,
    OSError,
)

# Params that indicate read-only operations (always query params)
_QUERY_ONLY_PARAMS = {
    "format", "expand", "fields", "maxResults", "startAt",
    "limit", "includeArchived", "jql", "query",
}


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
    from ..config import BridgeConfig

    config = BridgeConfig()

    # Parse plugin name and path segments
    plugin = args[0]
    remaining = args[1:]

    # Handle --help / -h flag anywhere: convert to /plugin/help/{command} request
    if not remaining or remaining == ["--help"] or remaining == ["-h"]:
        remaining = ["help"]
    elif "--help" in remaining or "-h" in remaining:
        # Extract command before --help and redirect to help endpoint
        # e.g., "jira issue --help" -> "/jira/help/issue"
        command_parts = []
        for arg in remaining:
            if arg in ("--help", "-h"):
                break
            if not arg.startswith("-"):
                command_parts.append(arg)
        if command_parts:
            remaining = ["help", command_parts[0]]
        else:
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
            # Option: --key=value, --key value, or --flag
            arg_content = arg[2:]
            if "=" in arg_content:
                # Handle --key=value format
                key, value = arg_content.split("=", 1)
                params[key] = value
                i += 1
            else:
                # Handle --key value or --flag format
                key = arg_content
                if i + 1 < len(remaining) and not remaining[i + 1].startswith("-"):
                    params[key] = remaining[i + 1]
                    i += 2
                else:
                    params[key] = "true"
                    i += 1
        elif arg.startswith("-") and not arg.startswith("--"):
            # Short option: -k=value, -k value, or -k (flag)
            arg_content = arg[1:]
            if "=" in arg_content:
                # Handle -k=value format
                key, value = arg_content.split("=", 1)
                params[key] = value
                i += 1
            elif len(arg_content) == 1:
                # Handle -k value or -k (flag) format
                key = arg_content
                if i + 1 < len(remaining) and not remaining[i + 1].startswith("-"):
                    params[key] = remaining[i + 1]
                    i += 2
                else:
                    params[key] = "true"
                    i += 1
            else:
                # Path segment that starts with - but isn't an option
                path_parts.append(arg)
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


def _detect_http_method(config: "BridgeConfig", path: str, params: dict) -> str:
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


def _get_method_from_openapi(
    config: "BridgeConfig", path: str, params: dict
) -> str | None:
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
                    valid = ("get", "post", "put", "patch", "delete")
                    available_methods = [m.upper() for m in methods if m in valid]

                    if len(available_methods) == 1:
                        return available_methods[0]

                    # Multiple methods available - use params to determine
                    if "GET" in available_methods and not (
                        set(params.keys()) - _QUERY_ONLY_PARAMS
                    ):
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


def _execute_plugin_request(
    url: str, method: str, params: dict, config: "BridgeConfig"
) -> int:
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
    except CONNECTION_ERRORS:
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


def _auto_start_daemon(config: "BridgeConfig") -> bool:
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
        except CONNECTION_ERRORS:
            pass
        time.sleep(AUTO_START_POLL_INTERVAL)

    print_error(f"Daemon did not become ready within {AUTO_START_TIMEOUT}s")
    return False
