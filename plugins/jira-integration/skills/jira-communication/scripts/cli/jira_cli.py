#!/usr/bin/env python3
"""
Jira CLI - Thin client using skills-daemon.

Response modes:
  --human     Formatted for terminal (default)
  --json      Raw JSON for programmatic use
  --ai        Optimized for LLM consumption
  --markdown  Markdown tables for docs

Formatting is done server-side by the daemon - this CLI is intentionally thin.
Uses only stdlib for fast startup (~15ms).
"""

import fcntl
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

DAEMON_URL = "http://127.0.0.1:9100"
DAEMON_PORT = 9100
PID_FILE = "/tmp/skills-daemon.pid"
LOCK_FILE = "/tmp/skills-daemon.lock"
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 0.5

# ANSI colors (for local error messages only)
if sys.stdout.isatty():
    RED, GREEN, DIM, RESET = "\033[31m", "\033[32m", "\033[2m", "\033[0m"
else:
    RED = GREEN = DIM = RESET = ""


# ═══════════════════════════════════════════════════════════════════════════════
# Daemon Management
# ═══════════════════════════════════════════════════════════════════════════════

def is_port_in_use(port: int = DAEMON_PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def is_daemon_healthy() -> bool:
    try:
        urllib.request.urlopen(f"{DAEMON_URL}/health", timeout=2)
        return True
    except Exception:
        return False


def cleanup_stale_daemon() -> None:
    try:
        pid = int(Path(PID_FILE).read_text().strip())
        try:
            os.kill(pid, 0)
            if not is_port_in_use():
                os.kill(pid, 9)
                time.sleep(0.2)
        except ProcessLookupError:
            pass
        Path(PID_FILE).unlink(missing_ok=True)
    except (FileNotFoundError, ValueError):
        pass


def start_daemon() -> bool:
    if is_port_in_use():
        return True

    lock_path = Path(LOCK_FILE)
    try:
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"{DIM}Waiting for daemon...{RESET}", file=sys.stderr)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            os.close(lock_fd)
            for _ in range(30):
                if is_port_in_use():
                    return True
                time.sleep(0.1)
            return False

        if is_port_in_use():
            os.close(lock_fd)
            return True

        cleanup_stale_daemon()
        print(f"{DIM}Starting daemon...{RESET}", file=sys.stderr)

        skills_daemon = Path(__file__).parent.parent.parent.parent.parent.parent / "skills-daemon"
        venv_python = skills_daemon / ".venv" / "bin" / "python"
        if not venv_python.exists():
            venv_python = Path(sys.executable)

        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(skills_daemon)
            subprocess.Popen(
                [str(venv_python), "-m", "skills_daemon.main"],
                cwd=str(skills_daemon),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )
            for _ in range(50):
                time.sleep(0.1)
                if is_port_in_use() and is_daemon_healthy():
                    return True
            return False
        finally:
            os.close(lock_fd)
    except Exception as e:
        print(f"{RED}Daemon error:{RESET} {e}", file=sys.stderr)
        return False


def ensure_daemon() -> bool:
    if is_port_in_use() and is_daemon_healthy():
        return True
    return start_daemon()


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP Client
# ═══════════════════════════════════════════════════════════════════════════════

def request(method: str, path: str, params: Optional[dict] = None) -> tuple[bool, str]:
    """Make HTTP request to daemon. Returns (success, response_text)."""
    url = f"{DAEMON_URL}/jira/{path}"
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, method=method)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode()
                # Check content type - if text/plain, return directly
                content_type = resp.headers.get("content-type", "")
                if "text/plain" in content_type:
                    return True, body
                # JSON response - check for success
                try:
                    data = json.loads(body)
                    if data.get("success") is False:
                        return False, data.get("error", "Unknown error")
                    return True, body
                except json.JSONDecodeError:
                    return True, body
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode()
                # Check if plain text error
                if "text/plain" in e.headers.get("content-type", ""):
                    return False, body
                data = json.loads(body)
                return False, data.get("detail", data.get("error", f"HTTP {e.code}"))
            except Exception:
                return False, f"HTTP {e.code}"
        except urllib.error.URLError as e:
            last_error = f"Connection failed: {e.reason}"
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                if not is_daemon_healthy():
                    start_daemon()
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    return False, last_error or "Request failed"


# ═══════════════════════════════════════════════════════════════════════════════
# Command Handlers
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_issue_get(args: list, fmt: str) -> int:
    if not args:
        print(f"{RED}Error:{RESET} Missing issue key", file=sys.stderr)
        return 1

    key = args[0]
    params = {"format": fmt}
    if "--full" in args or "-f" in args:
        params["expand"] = "renderedFields,changelog"

    success, response = request("GET", f"issue/{key}", params)
    print(response)
    return 0 if success else 1


def cmd_search(args: list, fmt: str) -> int:
    if not args:
        print(f"{RED}Error:{RESET} Missing JQL query", file=sys.stderr)
        return 1

    jql = args[0]
    params = {"jql": jql, "format": fmt}

    i = 1
    while i < len(args):
        if args[i] in ("-n", "--limit") and i + 1 < len(args):
            params["maxResults"] = int(args[i + 1])
            i += 2
        else:
            i += 1

    success, response = request("GET", "search", params)
    print(response)
    return 0 if success else 1


def cmd_transition_list(args: list, fmt: str) -> int:
    if not args:
        print(f"{RED}Error:{RESET} Missing issue key", file=sys.stderr)
        return 1

    success, response = request("GET", f"transitions/{args[0]}", {"format": fmt})
    print(response)
    return 0 if success else 1


def cmd_transition_do(args: list, fmt: str) -> int:
    if len(args) < 2:
        print(f"{RED}Error:{RESET} Missing arguments (KEY and STATE)", file=sys.stderr)
        return 1

    key, target = args[0], args[1]
    params = {"target": target, "format": fmt}
    if "--dry-run" in args:
        params["dryRun"] = "true"

    success, response = request("POST", f"transition/{key}", params)
    print(response)
    return 0 if success else 1


def cmd_comment_list(args: list, fmt: str) -> int:
    if not args:
        print(f"{RED}Error:{RESET} Missing issue key", file=sys.stderr)
        return 1

    success, response = request("GET", f"comments/{args[0]}", {"format": fmt})
    print(response)
    return 0 if success else 1


def cmd_comment_add(args: list, fmt: str) -> int:
    if len(args) < 2:
        print(f"{RED}Error:{RESET} Missing arguments (KEY and TEXT)", file=sys.stderr)
        return 1

    key, text = args[0], args[1]
    success, response = request("POST", f"comment/{key}", {"text": text, "format": fmt})
    print(response)
    return 0 if success else 1


def cmd_create(args: list, fmt: str) -> int:
    params = {"format": fmt}
    i = 0
    while i < len(args):
        if args[i] in ("--project", "-p") and i + 1 < len(args):
            params["project"] = args[i + 1]
            i += 2
        elif args[i] in ("--type", "-t") and i + 1 < len(args):
            params["type"] = args[i + 1]
            i += 2
        elif args[i] in ("--summary", "-s") and i + 1 < len(args):
            params["summary"] = args[i + 1]
            i += 2
        elif args[i] in ("--description", "-d") and i + 1 < len(args):
            params["description"] = args[i + 1]
            i += 2
        elif args[i] == "--priority" and i + 1 < len(args):
            params["priority"] = args[i + 1]
            i += 2
        elif args[i] == "--assignee" and i + 1 < len(args):
            params["assignee"] = args[i + 1]
            i += 2
        else:
            i += 1

    required = ["project", "type", "summary"]
    missing = [r for r in required if r not in params]
    if missing:
        print(f"{RED}Error:{RESET} Missing required: {', '.join(missing)}", file=sys.stderr)
        return 1

    success, response = request("POST", "create", params)
    print(response)
    return 0 if success else 1


def cmd_link(args: list, fmt: str) -> int:
    if len(args) < 3:
        print(f"{RED}Error:{RESET} Missing arguments (FROM TO --type TYPE)", file=sys.stderr)
        return 1

    from_key, to_key = args[0], args[1]
    link_type = None
    for i, arg in enumerate(args):
        if arg in ("--type", "-t") and i + 1 < len(args):
            link_type = args[i + 1]

    if not link_type:
        print(f"{RED}Error:{RESET} Missing --type", file=sys.stderr)
        return 1

    success, response = request("POST", "link", {"from": from_key, "to": to_key, "type": link_type, "format": fmt})
    print(response)
    return 0 if success else 1


def cmd_link_types(args: list, fmt: str) -> int:
    success, response = request("GET", "link/types", {"format": fmt})
    print(response)
    return 0 if success else 1


def cmd_user_me(args: list, fmt: str) -> int:
    success, response = request("GET", "user/me", {"format": fmt})
    print(response)
    return 0 if success else 1


def cmd_workflows(args: list, fmt: str) -> int:
    success, response = request("GET", "workflows", {"format": fmt})
    print(response)
    return 0 if success else 1


def cmd_workflow_discover(args: list, fmt: str) -> int:
    if not args:
        print(f"{RED}Error:{RESET} Missing issue key", file=sys.stderr)
        return 1

    success, response = request("POST", f"workflow/discover/{args[0]}", {"format": fmt})
    print(response)
    return 0 if success else 1


def print_help():
    print(f"""
Jira CLI - Fast client using skills-daemon

Usage:
    jira [OPTIONS] <command> [args...]

Options:
    --human      Terminal output with colors (default)
    --json       Raw JSON output
    --ai         Concise output for LLMs
    --markdown   Markdown tables

Commands:
    issue get <KEY> [--full]       Get issue details
    search '<JQL>' [-n LIMIT]      Search with JQL
    transition list <KEY>          List available transitions
    transition do <KEY> '<STATE>'  Execute transition
    comment list <KEY>             List comments
    comment add <KEY> '<TEXT>'     Add comment
    create -p PRJ -t TYPE -s SUM   Create issue
    link <FROM> <TO> --type TYPE   Link issues
    link types                     List link types
    user me                        Current user info
    workflows                      List cached workflows
    workflow discover <KEY>        Discover workflow

Examples:
    jira issue get HMKG-2064
    jira search 'assignee = currentUser()' -n 10
    jira --ai search 'project = OPSDHL'
    jira --json transition list HMKG-123
    jira transition do HMKG-123 'In Progress'
    jira create -p HMKG -t Task -s 'New task'
""")


def main():
    args = sys.argv[1:]

    # Parse format flag
    fmt = "human"
    clean_args = []
    for arg in args:
        if arg == "--json":
            fmt = "json"
        elif arg == "--ai":
            fmt = "ai"
        elif arg == "--markdown":
            fmt = "markdown"
        elif arg == "--human":
            fmt = "human"
        else:
            clean_args.append(arg)

    args = clean_args

    if not args or args[0] in ("help", "--help", "-h"):
        print_help()
        return 0

    # Ensure daemon is running
    if not ensure_daemon():
        print(f"{RED}Error:{RESET} Could not start daemon", file=sys.stderr)
        return 1

    cmd = args[0]
    rest = args[1:]

    # Route commands
    if cmd == "issue":
        if not rest or rest[0] == "get":
            return cmd_issue_get(rest[1:] if rest else [], fmt)
        print(f"{RED}Error:{RESET} Unknown issue command: {rest[0]}", file=sys.stderr)
        return 1

    elif cmd == "search":
        if rest and rest[0] == "query":
            return cmd_search(rest[1:], fmt)
        return cmd_search(rest, fmt)

    elif cmd == "transition":
        if not rest:
            print(f"{RED}Error:{RESET} Missing subcommand (list, do)", file=sys.stderr)
            return 1
        if rest[0] == "list":
            return cmd_transition_list(rest[1:], fmt)
        elif rest[0] == "do":
            return cmd_transition_do(rest[1:], fmt)
        print(f"{RED}Error:{RESET} Unknown transition command: {rest[0]}", file=sys.stderr)
        return 1

    elif cmd == "comment":
        if not rest:
            print(f"{RED}Error:{RESET} Missing subcommand (list, add)", file=sys.stderr)
            return 1
        if rest[0] == "list":
            return cmd_comment_list(rest[1:], fmt)
        elif rest[0] == "add":
            return cmd_comment_add(rest[1:], fmt)
        print(f"{RED}Error:{RESET} Unknown comment command: {rest[0]}", file=sys.stderr)
        return 1

    elif cmd == "create":
        return cmd_create(rest, fmt)

    elif cmd == "link":
        if rest and rest[0] == "types":
            return cmd_link_types(rest[1:], fmt)
        return cmd_link(rest, fmt)

    elif cmd == "user":
        if not rest or rest[0] == "me":
            return cmd_user_me(rest[1:] if rest else [], fmt)
        print(f"{RED}Error:{RESET} Unknown user command", file=sys.stderr)
        return 1

    elif cmd == "workflows":
        return cmd_workflows(rest, fmt)

    elif cmd == "workflow":
        if rest and rest[0] == "discover":
            return cmd_workflow_discover(rest[1:], fmt)
        print(f"{RED}Error:{RESET} Unknown workflow command", file=sys.stderr)
        return 1

    else:
        print(f"{RED}Error:{RESET} Unknown command: {cmd}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
