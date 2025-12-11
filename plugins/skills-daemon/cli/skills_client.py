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

sys.path.insert(0, str(Path(__file__).parent.parent))
from skills_daemon.colors import get_color_tuple
from skills_daemon.config import config
from skills_daemon.lifecycle import read_pid, cleanup_stale_pid

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.5  # seconds (0.5, 1.0, 2.0)
TIMEOUT = 30

# ANSI colors
RED, GREEN, YELLOW, CYAN, DIM, BOLD, RESET = get_color_tuple()


def is_port_in_use(port: int = None) -> bool:
    """Check if daemon port is in use by attempting IPv6 connect (bypasses ESET)."""
    if port is None:
        port = config.port
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect(("::1", port))
            return True  # Connection succeeded = something is listening
        except (OSError, socket.timeout):
            return False  # Connection failed = port is free


def is_daemon_healthy() -> bool:
    """Check if daemon is responding to health checks."""
    try:
        urllib.request.urlopen(f"{config.daemon_url}/health", timeout=1)
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
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def cleanup_stale_daemon() -> None:
    """Kill any daemon process that's not responding on the expected port."""
    pid = read_pid()
    if pid is None:
        return
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
    cleanup_stale_pid()


def start_daemon() -> bool:
    """Start the daemon in background with lock protection."""
    # Quick check - if port is already in use, daemon is running
    if is_port_in_use():
        return True

    # Use lockfile to prevent race condition
    lock_path = config.state_dir / "daemon.lock"
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
        # Use centralized runtime venv (matches daemon_ctl.py)
        venv_python = config.venv_dir / "bin" / "python"
        if not venv_python.exists():
            # Fallback: try local .venv (development mode)
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
                        urllib.request.urlopen(f"{config.daemon_url}/health", timeout=1)
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


def request(path: str, params: dict, method: str = "GET") -> dict | str:
    """Make HTTP request to daemon with retry and exponential backoff.

    Retries on transient errors (connection refused, timeout).
    Does NOT retry on HTTP errors (4xx, 5xx) - those are legitimate responses.

    Returns:
        dict for JSON responses, str for plain text responses (format=human/ai/markdown)
    """
    # URL-encode path segments to handle spaces and special characters
    encoded_path = "/".join(urllib.parse.quote(seg, safe="") for seg in path.split("/"))
    url = f"{config.daemon_url}/{encoded_path}"
    # Always use query params (FastAPI endpoints expect Query params)
    clean = {k: v for k, v in params.items() if v is not None}
    if clean:
        url += "?" + urllib.parse.urlencode(clean)
    data = None  # Body not needed - using query params

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode()
                content_type = resp.headers.get("Content-Type", "")

                # Handle plain text responses (format=human, ai, markdown)
                if "text/plain" in content_type:
                    return body  # Return raw text directly

                # JSON response
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    # Fallback: treat as plain text if JSON parsing fails
                    return body

        except urllib.error.HTTPError as e:
            # HTTP errors are not transient - don't retry
            try:
                return json.loads(e.read().decode())
            except Exception:
                return {"success": False, "error": f"HTTP {e.code}"}

        except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
            # Transient errors - retry with backoff
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BACKOFF_BASE * (2 ** attempt)
                print(f"{DIM}Retry {attempt + 1}/{MAX_RETRIES} in {delay:.1f}s...{RESET}", file=sys.stderr)
                time.sleep(delay)
            continue

        except Exception as e:
            # Unknown errors - don't retry
            return {"success": False, "error": str(e)}

    # All retries exhausted
    reason = str(last_error.reason) if hasattr(last_error, 'reason') else str(last_error)
    return {"success": False, "error": f"Connection failed after {MAX_RETRIES} retries: {reason}"}


def parse_args(args: list[str]) -> tuple[dict, str, list[str]]:
    """Parse CLI args to params dict, HTTP method, and positional path segments.

    Positional args become path segments: "user me" → "/user/me"
    Named args become query params: "--jql 'foo'" → "?jql=foo"
    """
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

    # POST for write operations (body=True for include_body is NOT a write op)
    if any(k in params for k in ("content", "code", "new_name")):
        method = "POST"
    # body param with string value (actual code body) triggers POST
    if "body" in params and isinstance(params["body"], str):
        method = "POST"

    return params, method, positionals


# Commands that require POST method (checked against last path segment for nested commands)
POST_COMMANDS = {
    "activate", "write", "replace", "after", "before", "rename", "delete", "move", "archive",
    "init_memories",  # Creates memory folder structure
    "create", "link", "comment", "transition", "discover",  # Jira write operations
}


def validate_params(plugin: str, command: str, params: dict) -> None:
    """Validate params against known command parameters.

    Warns about unknown parameters to catch typos. Does not block execution.
    """
    try:
        help_result = request(f"{plugin}/help", {"command": command})
        if not isinstance(help_result, dict) or "parameters" not in help_result:
            return  # Can't validate without help info

        # Get known param names (both actual name and alias)
        known_params = set()
        for param in help_result.get("parameters", []):
            name = param.get("name", "")
            if name:
                # Add both underscore and hyphen versions
                known_params.add(name)
                known_params.add(name.replace("-", "_"))
                known_params.add(name.replace("_", "-"))

        # Check for unknown params
        unknown = []
        for param_name in params:
            normalized = param_name.replace("-", "_")
            if normalized not in known_params and param_name not in known_params:
                unknown.append(param_name)

        if unknown:
            # Suggest similar params
            for unk in unknown:
                similar = find_similar_param(unk, known_params)
                if similar:
                    print(f"{YELLOW}Warning:{RESET} Unknown parameter '--{unk}'. Did you mean '--{similar}'?", file=sys.stderr)
                else:
                    print(f"{YELLOW}Warning:{RESET} Unknown parameter '--{unk}'", file=sys.stderr)

    except Exception:
        pass  # Validation failure shouldn't break command execution


def find_similar_param(param: str, known: set) -> str | None:
    """Find similar parameter name for typo suggestions."""
    param_lower = param.lower().replace("_", "").replace("-", "")

    for known_param in known:
        known_lower = known_param.lower().replace("_", "").replace("-", "")
        # Check prefix match (e.g., "proj" matches "project")
        if known_lower.startswith(param_lower) or param_lower.startswith(known_lower):
            return known_param
        # Check if most chars match (simple similarity)
        common = sum(1 for c in param_lower if c in known_lower)
        if common >= len(param_lower) * 0.7:
            return known_param

    return None


def format_validation_error(details: list) -> str:
    """Format FastAPI validation errors into friendly messages."""
    lines = [f"{RED}Error:{RESET} Invalid parameters"]

    for error in details:
        error_type = error.get("type", "unknown")
        loc = error.get("loc", [])
        msg = error.get("msg", "")

        # Extract parameter name from location (e.g., ['query', 'project'] -> 'project')
        param_name = loc[-1] if loc else "unknown"
        param_source = loc[0] if len(loc) > 1 else ""

        if error_type == "missing":
            lines.append(f"  {YELLOW}Missing required parameter:{RESET} --{param_name}")
        elif error_type == "string_type":
            lines.append(f"  {YELLOW}Invalid value for --{param_name}:{RESET} expected string")
        elif error_type == "int_parsing":
            lines.append(f"  {YELLOW}Invalid value for --{param_name}:{RESET} expected integer")
        elif error_type == "bool_parsing":
            lines.append(f"  {YELLOW}Invalid value for --{param_name}:{RESET} expected true/false")
        else:
            # Generic error
            lines.append(f"  {YELLOW}--{param_name}:{RESET} {msg}")

    lines.append("")
    lines.append(f"{DIM}Hint: Use --help to see required parameters{RESET}")

    return "\n".join(lines)


def format_result(result: dict | str, fmt: str) -> str:
    """Format result for display."""
    # Handle plain text responses (already formatted by daemon)
    if isinstance(result, str):
        return result

    # Handle FastAPI validation errors (422 responses)
    if "detail" in result and isinstance(result["detail"], list):
        return format_validation_error(result["detail"])

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
                # Jira issue output: {key, fields: {summary, status, ...}}
                elif "key" in item and "fields" in item:
                    key = item.get("key", "?")
                    fields = item.get("fields", {})
                    summary = fields.get("summary", "")[:50]
                    status = fields.get("status", {}).get("name", "?")
                    lines.append(f"{CYAN}{key:15}{RESET} {status:15} {summary}")
                # Symbol output: {name_path, kind, relative_path, ...}
                elif "name_path" in item or "kind" in item:
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
                # Unknown dict - show as compact JSON
                else:
                    lines.append(json.dumps(item, ensure_ascii=False, default=str))
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


def format_help(result: dict, fmt: str = "compact") -> str:
    """Format /help endpoint response for display."""
    if fmt == "json":
        return json.dumps(result, indent=2, ensure_ascii=False)

    if "error" in result:
        out = f"{RED}Error:{RESET} {result['error']}"
        if available := result.get("available"):
            out += f"\n{DIM}Available: {', '.join(available)}{RESET}"
        return out

    lines = []

    # Plugin-level help
    if "commands" in result:
        name = result.get("plugin", "?")
        desc = result.get("description", "")
        version = result.get("version", "")

        lines.append(f"{BOLD}{name}{RESET} - {desc}")
        if version:
            lines.append(f"{DIM}Version: {version}{RESET}")
        lines.append("")
        lines.append(f"{BOLD}Commands:{RESET}")

        # Group by unique command name
        seen = {}
        for cmd in result.get("commands", []):
            cmd_name = cmd.get("name", "?")
            if cmd_name not in seen:
                seen[cmd_name] = cmd
            else:
                # Merge methods
                seen[cmd_name]["methods"] = list(set(seen[cmd_name].get("methods", []) + cmd.get("methods", [])))

        for cmd_name, cmd in seen.items():
            summary = cmd.get("summary", "")
            methods = ", ".join(cmd.get("methods", []))
            lines.append(f"  {CYAN}{cmd_name:20}{RESET} {DIM}[{methods}]{RESET} {summary}")

        if hint := result.get("hint"):
            lines.append("")
            lines.append(f"{DIM}{hint}{RESET}")

    # Command-level help
    elif "parameters" in result:
        name = result.get("command", "?")
        plugin = result.get("plugin", "?")
        summary = result.get("summary", "")
        desc = result.get("description", "")
        path = result.get("path", "")
        methods = ", ".join(result.get("methods", []))
        usage = result.get("usage", "")
        examples = result.get("examples", [])

        lines.append(f"{BOLD}{plugin} {name}{RESET} - {summary}")
        if desc:
            lines.append(f"{desc}")
        lines.append("")

        # Show usage hint
        if usage:
            lines.append(f"{BOLD}Usage:{RESET} {usage}")
            lines.append("")

        lines.append(f"{DIM}Path: {path}  Methods: {methods}{RESET}")

        params = result.get("parameters", [])
        if params:
            lines.append("")
            lines.append(f"{BOLD}Parameters:{RESET}")
            for param in params:
                pname = param.get("name", "?")
                req = f"{RED}required{RESET}" if param.get("required") else f"{DIM}optional{RESET}"
                pin = param.get("in", "query")
                pdesc = param.get("description", "")
                default = param.get("default")

                line = f"  --{pname:20} [{req}]"
                if pdesc:
                    line += f" {pdesc}"
                if default is not None:
                    line += f" {DIM}(default: {default}){RESET}"
                lines.append(line)

        # Show examples if available
        if examples:
            lines.append("")
            lines.append(f"{BOLD}Examples:{RESET}")
            for ex in examples:
                lines.append(f"  {CYAN}{ex}{RESET}")

    return "\n".join(lines)


def main():
    args = sys.argv[1:]

    # Global flags
    fmt = "compact"
    if "--json" in args or "-j" in args:
        fmt = "json"
        args = [a for a in args if a not in ("--json", "-j")]

    # Check if --help is present (but NOT as the only arg - that's client help)
    has_help = "--help" in args or "-h" in args

    if has_help or not args:
        # Remove help flags for processing
        args = [a for a in args if a not in ("--help", "-h")]

        if not args:
            # No plugin specified - show client help
            print(f"""
{BOLD}Skills Client{RESET} - Unified CLI for skills daemon

{BOLD}Usage:{RESET}
    skills-client <plugin> <command> [args...]
    skills-client <plugin> --help              # Plugin help (from daemon)
    skills-client <plugin> <command> --help    # Command help (from daemon)
    skills-client health
    skills-client plugins

{BOLD}Options:{RESET}
    --json      Output raw JSON
    --help      Show this help

{BOLD}Examples:{RESET}
    skills-client health                       # Daemon health
    skills-client plugins                      # List available plugins
    skills-client jira --help                  # Jira plugin help
    skills-client jira search --help           # Jira search command help
    skills-client --json jira search --jql ... # JSON output
""")
            return

        # Plugin specified with --help - fetch help from daemon
        if not ensure_daemon():
            print(f"{RED}Error:{RESET} Could not start daemon", file=sys.stderr)
            sys.exit(1)

        plugin = args[0]
        command = args[1] if len(args) > 1 else None

        if command:
            result = request(f"{plugin}/help", {"command": command})
        else:
            result = request(f"{plugin}/help", {})

        print(format_help(result, fmt))
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

    params, method, positionals = parse_args(rest)
    # Build path: command + positional args joined with /
    # "jira issue HMKG-123" → plugin=jira, command=issue, positionals=[HMKG-123] → /jira/issue/HMKG-123
    # "jira user me" → plugin=jira, command=user, positionals=[me] → /jira/user/me
    path_parts = [command] + positionals if positionals else [command]
    full_path = "/".join(path_parts)

    # Validate parameters against known params (warn about typos/unknown params)
    if params:
        validate_params(plugin, full_path, params)

    # Force POST for certain commands
    # Check both: command itself AND last segment (for nested commands like memory/delete)
    # But exclude read-only nested routes (like link/types)
    path_segments = full_path.split("/")
    cmd_first = path_segments[0]  # e.g., "transition" from "transition/OROSPD-589"
    cmd_last = path_segments[-1]  # e.g., "delete" from "memory/delete"

    # Commands where the base name is POST but nested paths might be GET
    READ_ONLY_NESTED = {"types", "workflows"}  # link/types, workflow/xxx

    # Use POST if:
    # 1. First segment is POST command AND last segment isn't a read-only action
    # 2. OR last segment is a POST command (for memory/delete, workflow/discover)
    if cmd_first in POST_COMMANDS and cmd_last not in READ_ONLY_NESTED:
        method = "POST"
    elif cmd_last in POST_COMMANDS:
        method = "POST"
    result = request(f"{plugin}/{full_path}", params, method)
    print(format_result(result, fmt))

    # Check for explicit failure (only for dict responses)
    if isinstance(result, dict) and result.get("success") is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
