#!/usr/bin/env python3
"""
Unified thin client for skills daemon.
Uses only stdlib for fast startup (~10ms).

Usage:
    skills-client serena find Customer --kind class
    skills-client jira issue HMKG-123
    skills-client --json serena status
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Configuration
DAEMON_URL = "http://127.0.0.1:9100"
PID_FILE = "/tmp/skills-daemon.pid"
TIMEOUT = 30

# ANSI colors
RED, GREEN, YELLOW, CYAN, DIM, BOLD, RESET = (
    ("\033[31m", "\033[32m", "\033[33m", "\033[36m", "\033[2m", "\033[1m", "\033[0m")
    if sys.stdout.isatty() else ("", "", "", "", "", "", "")
)


def is_daemon_running() -> bool:
    """Check if daemon is running."""
    try:
        pid = int(Path(PID_FILE).read_text().strip())
        os.kill(pid, 0)
        return True
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        return False


def start_daemon() -> bool:
    """Start the daemon in background."""
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
        for _ in range(30):
            time.sleep(0.1)
            if is_daemon_running():
                try:
                    urllib.request.urlopen(f"{DAEMON_URL}/health", timeout=1)
                    return True
                except Exception:
                    pass
        return False
    except Exception as e:
        print(f"{RED}Error:{RESET} {e}", file=sys.stderr)
        return False


def ensure_daemon() -> bool:
    """Ensure daemon is running."""
    return is_daemon_running() or start_daemon()


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
                if val.lower() in ("true", "yes", "1"):
                    params[key] = True
                elif val.lower() in ("false", "no", "0"):
                    params[key] = False
                else:
                    try:
                        params[key] = int(val)
                    except ValueError:
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


# Commands that require POST method
POST_COMMANDS = {
    "activate", "write", "replace", "after", "before", "rename", "delete"
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
                # Tools output: {name, description}
                if "description" in item and "kind" not in item:
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
                    if isinstance(kind, int):
                        kind = {
                            1: "file", 2: "module", 3: "namespace", 4: "package",
                            5: "class", 6: "method", 7: "property", 8: "field",
                            9: "constructor", 10: "enum", 11: "interface", 12: "function",
                            13: "variable", 14: "constant", 22: "struct", 23: "event",
                        }.get(kind, str(kind))
                    file = item.get("relative_path") or item.get("file", "")
                    loc = item.get("body_location", {})
                    line = loc.get("start_line", 0) if loc else 0
                    lines.append(f"{CYAN}{name}{RESET} {DIM}({kind}) {file}:{line}{RESET}")
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

{BOLD}Plugins:{RESET}
    serena      Semantic code navigation
    jira        Jira (coming soon)
    jetbrains   JetBrains IDE (coming soon)

{BOLD}Examples:{RESET}
    skills-client serena find Customer --kind class
    skills-client serena status
    skills-client --json serena find Controller
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
    # Force POST for certain commands
    if command in POST_COMMANDS:
        method = "POST"
    result = request(f"{plugin}/{command}", params, method)
    print(format_result(result, fmt))

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
