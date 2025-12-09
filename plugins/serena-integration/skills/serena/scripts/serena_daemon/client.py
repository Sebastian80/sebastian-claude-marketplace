"""
Thin stdlib-only client for Serena daemon.

Uses only Python stdlib to minimize import time (~10ms vs ~150ms with httpx/typer).
This is the key to fast CLI responses.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from serena_daemon import DEFAULT_HOST, DEFAULT_PORT, PID_FILE

# Colors (ANSI escape codes)
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
RESET = "\033[0m"


def is_daemon_running() -> bool:
    """Check if daemon is running by making HTTP health request.

    Using HTTP instead of socket check because ESET/security software
    can interfere with raw socket connections on loopback.
    """
    try:
        url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/health"
        request = Request(url, method="GET")
        with urlopen(request, timeout=0.5) as response:
            data = json.loads(response.read().decode())
            return data.get("success", False)
    except Exception:
        return False


def start_daemon() -> bool:
    """Start the daemon in background."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(os.path.dirname(script_dir), ".venv", "bin", "python")

    if not os.path.exists(venv_python):
        print(f"{RED}Error: venv not found at {venv_python}{RESET}", file=sys.stderr)
        return False

    # Start daemon in background
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(script_dir)

    subprocess.Popen(
        [venv_python, "-m", "serena_daemon.server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )

    # Wait for daemon to start (max 3 seconds)
    for _ in range(30):
        time.sleep(0.1)
        if is_daemon_running():
            return True

    return False


def ensure_daemon() -> bool:
    """Ensure daemon is running, start if needed."""
    if is_daemon_running():
        return True

    print(f"{DIM}Starting Serena daemon...{RESET}", file=sys.stderr)
    return start_daemon()


def daemon_request(
    endpoint: str,
    params: Optional[dict] = None,
    method: str = "GET",
    timeout: float = 30.0,
) -> dict:
    """Make request to daemon."""
    url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/{endpoint}"

    data = None
    if params:
        if method == "GET":
            url = f"{url}?{urlencode(params)}"
        else:
            data = json.dumps(params).encode()

    request = Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")

    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"success": False, "error": f"HTTP {e.code}: {body}"}
    except URLError as e:
        return {"success": False, "error": f"Connection error: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_symbol(symbol: dict, show_body: bool = False) -> str:
    """Format a symbol for display."""
    kind = symbol.get("kind", "unknown")
    name = symbol.get("name", "?")
    file = symbol.get("file", "")
    line = symbol.get("line", 0)

    # Color by kind
    kind_colors = {
        "class": CYAN,
        "interface": BLUE,
        "method": GREEN,
        "function": GREEN,
        "property": YELLOW,
        "constant": YELLOW,
    }
    color = kind_colors.get(kind, "")

    # Shorten file path
    if "/src/" in file:
        file = file.split("/src/")[-1]
    elif "/vendor/" in file:
        file = "vendor/" + file.split("/vendor/")[-1]

    output = f"{color}{BOLD}{name}{RESET} {DIM}({kind}){RESET}"
    output += f"\n  {DIM}{file}:{line}{RESET}"

    if show_body and "body" in symbol:
        body = symbol["body"]
        # First line only for compact display
        first_line = body.split("\n")[0][:100]
        output += f"\n  {DIM}{first_line}{RESET}"

    return output


def format_reference(ref: dict) -> str:
    """Format a reference for display."""
    file = ref.get("file", "")
    line = ref.get("line", 0)
    preview = ref.get("preview", "").strip()

    # Shorten path
    if "/src/" in file:
        file = file.split("/src/")[-1]
    elif "/vendor/" in file:
        file = "vendor/" + file.split("/vendor/")[-1]

    return f"  {DIM}{file}:{line}{RESET}\n    {preview}"


def format_result(endpoint: str, data: Any, args: dict) -> str:
    """Format result based on endpoint type."""
    if args.get("json"):
        return json.dumps(data, indent=2)

    if endpoint == "find":
        if not data:
            return f"{YELLOW}No symbols found{RESET}"

        output = []
        for symbol in data:
            output.append(format_symbol(symbol, show_body=args.get("body", False)))
        return "\n".join(output)

    elif endpoint == "refs":
        if not data:
            return f"{YELLOW}No references found{RESET}"

        output = [f"{BOLD}Found {len(data)} reference(s):{RESET}"]
        for ref in data:
            output.append(format_reference(ref))
        return "\n".join(output)

    elif endpoint == "overview":
        if not data:
            return f"{YELLOW}No symbols in file{RESET}"

        output = []
        for symbol in data:
            indent = "  " * symbol.get("depth", 0)
            kind = symbol.get("kind", "")
            name = symbol.get("name", "")
            line = symbol.get("line", 0)
            output.append(f"{indent}{CYAN}{name}{RESET} {DIM}({kind} L{line}){RESET}")
        return "\n".join(output)

    elif endpoint == "search":
        if not data:
            return f"{YELLOW}No matches found{RESET}"

        output = []
        for match in data:
            file = match.get("file", "")
            line = match.get("line", 0)
            text = match.get("text", "").strip()
            output.append(f"{DIM}{file}:{line}{RESET}\n  {text}")
        return "\n".join(output)

    elif endpoint == "status":
        project = data.get("active_project", "none")
        output = [f"{BOLD}Serena Status{RESET}"]
        output.append(f"  Active project: {GREEN}{project}{RESET}")
        if "projects" in data:
            output.append(f"  Available: {', '.join(data['projects'])}")
        return "\n".join(output)

    # Default: JSON
    return json.dumps(data, indent=2)


def print_error(message: str, hint: Optional[str] = None) -> None:
    """Print error message."""
    print(f"{RED}Error: {message}{RESET}", file=sys.stderr)
    if hint:
        print(f"{DIM}Hint: {hint}{RESET}", file=sys.stderr)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="serena",
        description="Serena CLI - Semantic code navigation",
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--no-daemon", action="store_true", help="Don't auto-start daemon")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # find
    find_p = subparsers.add_parser("find", help="Find symbols")
    find_p.add_argument("pattern", help="Symbol pattern to find")
    find_p.add_argument("--kind", "-k", help="Filter by kind (class, method, etc)")
    find_p.add_argument("--path", "-p", help="Filter by path pattern")
    find_p.add_argument("--body", "-b", action="store_true", help="Include body")
    find_p.add_argument("--depth", "-d", type=int, default=0, help="Nesting depth")
    find_p.add_argument("--exact", "-e", action="store_true", help="Exact match")

    # refs
    refs_p = subparsers.add_parser("refs", help="Find references")
    refs_p.add_argument("symbol", help="Symbol name")
    refs_p.add_argument("file", help="File containing symbol")
    refs_p.add_argument("--all", "-a", action="store_true", help="Include all refs")

    # overview
    overview_p = subparsers.add_parser("overview", help="File overview")
    overview_p.add_argument("file", help="File path")

    # search
    search_p = subparsers.add_parser("search", help="Code search")
    search_p.add_argument("pattern", help="Search pattern")
    search_p.add_argument("--glob", "-g", help="File glob pattern")
    search_p.add_argument("--path", "-p", help="Path filter")

    # status
    subparsers.add_parser("status", help="Show status")

    # activate
    activate_p = subparsers.add_parser("activate", help="Activate project")
    activate_p.add_argument("project", nargs="?", help="Project name")

    # memory
    memory_p = subparsers.add_parser("memory", help="Memory operations")
    memory_sub = memory_p.add_subparsers(dest="action")

    mem_list = memory_sub.add_parser("list", help="List memories")
    mem_list.add_argument("--folder", "-f", help="Folder filter")

    mem_read = memory_sub.add_parser("read", help="Read memory")
    mem_read.add_argument("name", help="Memory name")

    mem_write = memory_sub.add_parser("write", help="Write memory")
    mem_write.add_argument("name", help="Memory name")
    mem_write.add_argument("content", help="Content to write")

    mem_delete = memory_sub.add_parser("delete", help="Delete memory")
    mem_delete.add_argument("name", help="Memory name")

    mem_tree = memory_sub.add_parser("tree", help="Memory tree")
    mem_tree.add_argument("--folder", "-f", help="Folder filter")

    mem_search = memory_sub.add_parser("search", help="Search memories")
    mem_search.add_argument("pattern", help="Search pattern")
    mem_search.add_argument("--folder", "-f", help="Folder filter")

    # daemon
    daemon_p = subparsers.add_parser("daemon", help="Daemon control")
    daemon_sub = daemon_p.add_subparsers(dest="action")
    daemon_sub.add_parser("start", help="Start daemon")
    daemon_sub.add_parser("stop", help="Stop daemon")
    daemon_sub.add_parser("status", help="Daemon status")
    daemon_sub.add_parser("restart", help="Restart daemon")

    args = parser.parse_args()

    # Handle daemon commands directly
    if args.command == "daemon":
        if args.action == "start":
            if is_daemon_running():
                print(f"{GREEN}Daemon already running{RESET}")
            elif start_daemon():
                print(f"{GREEN}Daemon started{RESET}")
            else:
                print(f"{RED}Failed to start daemon{RESET}", file=sys.stderr)
                sys.exit(1)
            return

        elif args.action == "stop":
            if not is_daemon_running():
                print(f"{YELLOW}Daemon not running{RESET}")
            else:
                result = daemon_request("shutdown")
                if result.get("success"):
                    print(f"{GREEN}Daemon stopping...{RESET}")
                else:
                    print(f"{RED}Failed to stop daemon{RESET}", file=sys.stderr)
                    sys.exit(1)
            return

        elif args.action == "status":
            if is_daemon_running():
                result = daemon_request("health")
                if result.get("success"):
                    data = result.get("data", {})
                    print(f"{GREEN}Daemon running{RESET}")
                    print(f"  Version: {data.get('version', '?')}")
                    print(f"  Status: {data.get('status', '?')}")
                else:
                    print(f"{YELLOW}Daemon responding but unhealthy{RESET}")
            else:
                print(f"{RED}Daemon not running{RESET}")
                sys.exit(1)
            return

        elif args.action == "restart":
            if is_daemon_running():
                daemon_request("shutdown")
                time.sleep(0.5)
            if start_daemon():
                print(f"{GREEN}Daemon restarted{RESET}")
            else:
                print(f"{RED}Failed to restart daemon{RESET}", file=sys.stderr)
                sys.exit(1)
            return

        else:
            parser.print_help()
            return

    if not args.command:
        parser.print_help()
        return

    # Ensure daemon is running
    if not args.no_daemon and not ensure_daemon():
        print_error("Could not start daemon")
        sys.exit(1)

    # Build request
    endpoint = args.command
    params = {}

    if args.command == "find":
        params = {
            "pattern": args.pattern,
            "kind": args.kind,
            "path": args.path,
            "body": str(args.body).lower(),
            "depth": args.depth,
            "exact": str(args.exact).lower(),
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None and v != "false" and v != 0}

    elif args.command == "refs":
        params = {
            "symbol": args.symbol,
            "file": args.file,
            "all": str(getattr(args, "all", False)).lower(),
        }

    elif args.command == "overview":
        params = {"file": args.file}

    elif args.command == "search":
        params = {
            "pattern": args.pattern,
            "glob": args.glob,
            "path": args.path,
        }
        params = {k: v for k, v in params.items() if v is not None}

    elif args.command == "activate":
        params = {"project": args.project} if args.project else {}

    elif args.command == "memory":
        if not args.action:
            memory_p.print_help()
            return

        endpoint = f"memory/{args.action}"

        if args.action == "list":
            params = {"folder": args.folder} if args.folder else {}
        elif args.action == "read":
            params = {"name": args.name}
        elif args.action == "write":
            params = {"name": args.name, "content": args.content}
        elif args.action == "delete":
            params = {"name": args.name}
        elif args.action == "tree":
            params = {"folder": args.folder} if args.folder else {}
        elif args.action == "search":
            params = {"pattern": args.pattern}
            if args.folder:
                params["folder"] = args.folder

    # Make request
    method = "POST" if args.command in ("memory",) and args.action in ("write",) else "GET"
    result = daemon_request(endpoint, params, method)

    if not result.get("success"):
        print_error(result.get("error", "Unknown error"), result.get("hint"))
        sys.exit(1)

    # Format and print result
    output = format_result(
        args.command,
        result.get("data"),
        {"json": args.json, "body": getattr(args, "body", False)},
    )
    print(output)


if __name__ == "__main__":
    main()
