#!/usr/bin/env python3
"""
Unified thin client for skills daemon.
Uses only stdlib for fast startup (~10ms).

Usage:
    skills-client <plugin> <command> [--param value]
    skills-client --json <plugin> <command>
    skills-client health
    skills-client plugins
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

# Configuration
DAEMON_URL = "http://127.0.0.1:9100"
DAEMON_PORT = 9100
PID_FILE = "/tmp/skills-daemon.pid"
LOCK_FILE = "/tmp/skills-daemon.lock"
TIMEOUT = 30

# ANSI colors
RED, GREEN, YELLOW, CYAN, DIM, BOLD, RESET = (
    ("\033[31m", "\033[32m", "\033[33m", "\033[36m", "\033[2m", "\033[1m", "\033[0m")
    if sys.stdout.isatty() else ("", "", "", "", "", "", "")
)


def is_port_in_use(port: int = DAEMON_PORT) -> bool:
    """Check if daemon port is in use by attempting to bind (most reliable)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False  # Bind succeeded = port is free
        except OSError:
            return True  # Bind failed = port is in use


def is_daemon_healthy() -> bool:
    """Check if daemon is responding to health checks."""
    try:
        urllib.request.urlopen(f"{DAEMON_URL}/health", timeout=1)
        return True
    except Exception:
        return False


def is_daemon_running() -> bool:
    """Check if daemon is running via port + health check or PID file."""
    # Primary: port in use AND responding to health
    if is_port_in_use():
        if is_daemon_healthy():
            return True
        # Port in use but not healthy - might be starting up or zombie
        # Fall through to PID check
    # Fallback: check PID file
    try:
        pid = int(Path(PID_FILE).read_text().strip())
        os.kill(pid, 0)
        return True
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        return False


def cleanup_stale_daemon() -> None:
    """Kill any daemon process that's not responding on the expected port."""
    try:
        pid = int(Path(PID_FILE).read_text().strip())
        # Check if process exists but port is not responding
        try:
            os.kill(pid, 0)  # Process exists
            if not is_port_in_use():
                # Process exists but not listening - kill it
                print(f"{YELLOW}Cleaning up stale daemon (PID {pid})...{RESET}", file=sys.stderr)
                os.kill(pid, 9)  # SIGKILL
                time.sleep(0.2)
        except ProcessLookupError:
            pass  # Process doesn't exist
        # Clean up PID file
        Path(PID_FILE).unlink(missing_ok=True)
    except (FileNotFoundError, ValueError):
        pass


def start_daemon() -> bool:
    """Start the daemon in background with lock protection."""
    # Quick check - if port is already in use, daemon is running
    if is_port_in_use():
        return True

    # Use lockfile to prevent race condition
    lock_path = Path(LOCK_FILE)
    try:
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        try:
            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Another process is starting the daemon, wait for it
            print(f"{DIM}Waiting for daemon startup...{RESET}", file=sys.stderr)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)  # Blocking wait
            os.close(lock_fd)
            # After lock acquired, daemon should be running
            for _ in range(30):
                if is_port_in_use():
                    return True
                time.sleep(0.1)
            return False

        # We have the lock - check again if daemon started while waiting
        if is_port_in_use():
            os.close(lock_fd)
            return True

        # Clean up any stale state
        cleanup_stale_daemon()

        print(f"{DIM}Starting skills daemon...{RESET}", file=sys.stderr)

        skills_daemon = Path(__file__).parent.parent
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
            # Wait for daemon to start (check port, not PID file)
            for _ in range(50):  # 5 seconds max
                time.sleep(0.1)
                if is_port_in_use():
                    try:
                        urllib.request.urlopen(f"{DAEMON_URL}/health", timeout=1)
                        return True
                    except Exception:
                        pass
            return False
        except Exception as e:
            print(f"{RED}Error:{RESET} {e}", file=sys.stderr)
            return False
        finally:
            os.close(lock_fd)
    except Exception as e:
        print(f"{RED}Lock error:{RESET} {e}", file=sys.stderr)
        return False


def ensure_daemon() -> bool:
    """Ensure daemon is running and healthy."""
    if is_port_in_use() and is_daemon_healthy():
        return True
    return start_daemon()


def request(path: str, params: dict, method: str = "GET") -> dict:
    """Make HTTP request to daemon."""
    try:
        url = f"{DAEMON_URL}/{path}"
        # Always use query params (FastAPI endpoints expect Query params)
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)
        data = None  # Body not needed - using query params

        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"success": False, "error": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_args(args: list[str]) -> tuple[dict, str]:
    """Parse CLI args to params dict and HTTP method."""
    params = {}
    method = "GET"
    i = 0
    positionals = []

    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg[2:].replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                val = args[i + 1]
                # Try integer first (fixes --depth 1 being parsed as True)
                try:
                    params[key] = int(val)
                except ValueError:
                    # Then try explicit boolean strings (not "1"/"0" - those are ints)
                    if val.lower() in ("true", "yes"):
                        params[key] = True
                    elif val.lower() in ("false", "no"):
                        params[key] = False
                    else:
                        params[key] = val
                i += 2
            else:
                params[key] = True
                i += 1
        elif arg.startswith("-") and len(arg) == 2:
            key = arg[1]
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                params[key] = args[i + 1]
                i += 2
            else:
                params[key] = True
                i += 1
        else:
            positionals.append(arg)
            i += 1

    # Positional args not supported in generic client
    # Use named args: --pattern X, --file Y, etc.
    # Plugin-specific CLIs can add smarter positional handling
    if positionals:
        print(f"{YELLOW}Warning:{RESET} Positional args ignored. Use --param value", file=sys.stderr)
        print(f"  Got: {positionals}", file=sys.stderr)

    # POST for write operations (body=True for include_body is NOT a write op)
    if any(k in params for k in ("content", "code", "new_name")):
        method = "POST"
    # body param with string value (actual code body) triggers POST
    if "body" in params and isinstance(params["body"], str):
        method = "POST"

    return params, method


# Commands that require POST method (checked against last path segment for nested commands)
POST_COMMANDS = {
    "activate", "write", "replace", "after", "before", "rename", "delete", "move", "archive",
    "init_memories",  # Creates memory folder structure
}


def format_result(result: dict, fmt: str) -> str:
    """Format result for display."""
    # Handle explicit error responses
    if result.get("success") is False:
        out = f"{RED}Error:{RESET} {result.get('error', 'Unknown')}"
        if hint := result.get("hint"):
            out += f"\n{DIM}Hint: {hint}{RESET}"
        return out

    # Handle wrapped responses {"success": true, "data": ...}
    if "data" in result:
        data = result.get("data")
    else:
        # Direct response (health, plugins endpoints)
        data = result
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    if data is None:
        return f"{GREEN}OK{RESET}"
    if isinstance(data, str):
        return f"{GREEN}{data}{RESET}"
    if isinstance(data, list):
        if not data:
            return f"{YELLOW}No results{RESET}"
        lines = []
        for item in data:
            if isinstance(item, dict):
                # Memory search results: {memory, match_count, snippets}
                if "memory" in item and "snippets" in item:
                    mem = item.get("memory", "?")
                    count = item.get("match_count", 0)
                    snippets = item.get("snippets", [])
                    lines.append(f"{CYAN}{mem}{RESET} {DIM}({count} matches){RESET}")
                    for snippet in snippets[:3]:  # Show up to 3 snippets
                        lines.append(f"  {DIM}{snippet}{RESET}")
                # Tools output: {name, description}
                elif "description" in item and "kind" not in item:
                    name = item.get("name", "?")
                    desc = item.get("description", "")
                    # Truncate long descriptions
                    if len(desc) > 60:
                        desc = desc[:57] + "..."
                    lines.append(f"{CYAN}{name:30}{RESET} {DIM}{desc}{RESET}")
                # Symbol output: {name_path, kind, relative_path, ...}
                else:
                    name = item.get("name_path") or item.get("name", "?")
                    kind = item.get("kind", "")
                    kind_map = {
                        1: "File", 2: "Module", 3: "Namespace", 4: "Package",
                        5: "Class", 6: "Method", 7: "Property", 8: "Field",
                        9: "Constructor", 10: "Enum", 11: "Interface", 12: "Function",
                        13: "Variable", 14: "Constant", 22: "Struct", 23: "Event",
                    }
                    if isinstance(kind, int):
                        kind = kind_map.get(kind, str(kind))
                    file = item.get("relative_path") or item.get("file", "")
                    loc = item.get("body_location", {})
                    line = loc.get("start_line", 0) if loc else 0
                    lines.append(f"{CYAN}{name}{RESET} {DIM}({kind}) {file}:{line}{RESET}")
                    # Display children if present (from --depth 1)
                    children = item.get("children", [])
                    for child in children:
                        child_name = child.get("name_path") or child.get("name", "?")
                        child_kind = child.get("kind", "")
                        if isinstance(child_kind, int):
                            child_kind = kind_map.get(child_kind, str(child_kind))
                        child_loc = child.get("body_location") or child.get("location", {})
                        child_line = child_loc.get("start_line") or child_loc.get("line", 0)
                        lines.append(f"  {DIM}├─{RESET} {child_name} {DIM}({child_kind}) :{child_line}{RESET}")
            else:
                lines.append(str(item))
        return "\n".join(lines)
    if isinstance(data, dict):
        if "active_project" in data:
            return f"Project: {GREEN}{data['active_project']}{RESET}"
        if "recipes" in data:
            return f"{BOLD}Recipes:{RESET} {', '.join(data['recipes'])}"
        return "\n".join(f"{BOLD}{k}:{RESET} {v}" for k, v in data.items())
    return str(data)


def main():
    args = sys.argv[1:]

    # Global flags
    fmt = "compact"
    if "--json" in args or "-j" in args:
        fmt = "json"
        args = [a for a in args if a not in ("--json", "-j")]

    if "--help" in args or "-h" in args or not args:
        print(f"""
{BOLD}Skills Client{RESET} - Unified CLI for skills daemon

{BOLD}Usage:{RESET}
    skills-client <plugin> <command> [args...]
    skills-client health
    skills-client plugins

{BOLD}Options:{RESET}
    --json      Output raw JSON
    --help      Show this help

{BOLD}Examples:{RESET}
    skills-client health                       # Daemon health
    skills-client plugins                      # List available plugins
    skills-client <plugin> <command> --param   # Call plugin endpoint
    skills-client --json <plugin> <command>    # JSON output
""")
        return

    plugin = args[0]
    command = args[1] if len(args) > 1 else ""
    rest = args[2:]

    # Special top-level commands
    if plugin in ("health", "plugins"):
        if not ensure_daemon():
            print(f"{RED}Error:{RESET} Could not start daemon", file=sys.stderr)
            sys.exit(1)
        print(format_result(request(plugin, {}), fmt))
        return

    if not command:
        print(f"{RED}Error:{RESET} No command for '{plugin}'", file=sys.stderr)
        sys.exit(1)

    if not ensure_daemon():
        print(f"{RED}Error:{RESET} Could not start daemon", file=sys.stderr)
        sys.exit(1)

    params, method = parse_args(rest)
    # Force POST for certain commands (check last segment for nested commands like memory/delete)
    cmd_action = command.split("/")[-1] if "/" in command else command
    if cmd_action in POST_COMMANDS:
        method = "POST"
    result = request(f"{plugin}/{command}", params, method)
    print(format_result(result, fmt))

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
