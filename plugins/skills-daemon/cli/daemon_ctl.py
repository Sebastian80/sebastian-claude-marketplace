#!/usr/bin/env python3
"""
Skills daemon control CLI.

Usage:
    skills-daemon start|stop|status|restart|reload|logs
"""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from skills_daemon.colors import get_color_tuple

DAEMON_URL = "http://127.0.0.1:9100"
PID_FILE = "/tmp/skills-daemon.pid"
LOG_FILE = "/tmp/skills-daemon.log"

RED, GREEN, YELLOW, _, DIM, BOLD, RESET = get_color_tuple()


def read_pid() -> int | None:
    try:
        return int(Path(PID_FILE).read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def is_running() -> bool:
    pid = read_pid()
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_health() -> dict | None:
    try:
        with urllib.request.urlopen(f"{DAEMON_URL}/health", timeout=2) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def cmd_start():
    if is_running():
        print(f"{GREEN}Daemon already running{RESET}")
        return 0

    print(f"{DIM}Starting skills daemon...{RESET}")
    skills_daemon = Path(__file__).parent.parent
    venv_python = skills_daemon / ".venv" / "bin" / "python"

    if not venv_python.exists():
        print(f"{RED}Error:{RESET} Run: cd {skills_daemon} && python -m venv .venv && .venv/bin/pip install -e .")
        return 1

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
            if is_running() and get_health():
                print(f"{GREEN}Daemon started{RESET}")
                return 0
        print(f"{RED}Failed to start{RESET} - check: tail {LOG_FILE}")
        return 1
    except Exception as e:
        print(f"{RED}Error:{RESET} {e}")
        return 1


def cmd_stop():
    pid = read_pid()
    if not pid or not is_running():
        print(f"{YELLOW}Daemon not running{RESET}")
        return 0

    print(f"{DIM}Stopping daemon...{RESET}")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(30):
            time.sleep(0.1)
            if not is_running():
                print(f"{GREEN}Daemon stopped{RESET}")
                return 0
        os.kill(pid, signal.SIGKILL)
        print(f"{YELLOW}Daemon killed{RESET}")
        return 0
    except ProcessLookupError:
        print(f"{GREEN}Daemon stopped{RESET}")
        return 0


def cmd_status():
    if not is_running():
        print(f"{RED}Daemon not running{RESET}")
        return 1

    health = get_health()
    if not health:
        print(f"{YELLOW}Daemon running but not responding{RESET}")
        return 1

    print(f"{GREEN}Daemon running{RESET}")
    print(f"  Version: {health.get('version', '?')}")
    print(f"  Plugins: {', '.join(health.get('plugins', []))}")
    for name, status in health.get("plugin_health", {}).items():
        s = status.get("status", "?")
        c = GREEN if s in ("ok", "connected") else YELLOW
        print(f"  {name}: {c}{s}{RESET}")
    return 0


def cmd_restart():
    if is_running():
        cmd_stop()
        time.sleep(0.3)
    return cmd_start()


def cmd_logs():
    if not Path(LOG_FILE).exists():
        print(f"{YELLOW}No logs at {LOG_FILE}{RESET}")
        return 1
    print(f"{DIM}Tailing {LOG_FILE} (Ctrl+C to stop){RESET}")
    try:
        subprocess.run(["tail", "-f", LOG_FILE])
    except KeyboardInterrupt:
        pass
    return 0


def cmd_reload():
    """Hot-reload plugins without restarting daemon."""
    if not is_running():
        print(f"{RED}Daemon not running{RESET}")
        return 1

    print(f"{DIM}Reloading plugins...{RESET}")
    try:
        req = urllib.request.Request(f"{DAEMON_URL}/reload-plugins", method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read().decode())

        if result.get("success"):
            added = result.get("added", [])
            removed = result.get("removed", [])
            reloaded = result.get("reloaded", [])
            total = result.get("total", 0)

            print(f"{GREEN}Plugins reloaded{RESET} ({total} total)")
            if added:
                print(f"  {GREEN}Added:{RESET} {', '.join(added)}")
            if removed:
                print(f"  {YELLOW}Removed:{RESET} {', '.join(removed)}")
            if reloaded:
                print(f"  {DIM}Reloaded:{RESET} {', '.join(reloaded)}")
            return 0
        else:
            print(f"{RED}Reload failed:{RESET} {result.get('error', 'Unknown error')}")
            return 1
    except Exception as e:
        print(f"{RED}Error:{RESET} {e}")
        return 1


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(f"""
{BOLD}Skills Daemon Control{RESET}

{BOLD}Commands:{RESET}
    start       Start daemon
    stop        Stop daemon
    status      Show status
    restart     Restart daemon
    reload      Hot-reload plugins (no restart)
    logs        Tail logs
""")
        return 0

    cmds = {"start": cmd_start, "stop": cmd_stop, "status": cmd_status, "restart": cmd_restart, "reload": cmd_reload, "logs": cmd_logs}
    if args[0] not in cmds:
        print(f"{RED}Unknown command:{RESET} {args[0]}")
        return 1
    return cmds[args[0]]()


if __name__ == "__main__":
    sys.exit(main())
