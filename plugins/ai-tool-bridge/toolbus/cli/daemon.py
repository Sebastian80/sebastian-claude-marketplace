"""
CLI Daemon - Start, stop, and manage the daemon process.

Handles daemonization, PID file management, and process control.
"""

import asyncio
import os
import signal
import sys
import time

import structlog
import uvicorn

from ..app import create_app
from ..config import BridgeConfig
from ..deps import sync_dependencies
from ..lifecycle import PIDFile, SignalHandler, send_signal

__all__ = ["daemon_status", "restart_daemon", "start_daemon", "stop_daemon"]

logger = structlog.get_logger(__name__)


def start_daemon(config: BridgeConfig, foreground: bool = False, skip_deps: bool = False) -> int:
    """Start the bridge daemon.

    Args:
        config: Bridge configuration
        foreground: If True, run in foreground (don't daemonize)
        skip_deps: If True, skip dependency sync (used after fork)

    Returns:
        Exit code (0 for success)
    """
    config.ensure_dirs()
    pid_file = PIDFile(config.pid_file)

    # Check if already running
    if pid_file.is_running():
        print(f"Bridge is already running (PID {pid_file.read()})")
        return 1

    # Sync dependencies before starting (only in parent process)
    if not skip_deps:
        print("Checking dependencies...", file=sys.stderr)
        if not sync_dependencies(config):
            print("Failed to sync dependencies. Check logs.", file=sys.stderr)
            return 1

    if foreground:
        return _run_foreground(config, pid_file)
    else:
        return _run_daemon(config, pid_file)


def _run_foreground(config: BridgeConfig, pid_file: PIDFile) -> int:
    """Run daemon in foreground (for development/debugging)."""
    signal_handler = SignalHandler()

    with pid_file:
        app = create_app(config, signal_handler)

        uvicorn_config = uvicorn.Config(
            app,
            host=config.host,
            port=config.port,
            log_level="info",
            access_log=False,  # We have our own logging middleware
        )
        server = uvicorn.Server(uvicorn_config)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            signal_handler.setup(loop)
            loop.run_until_complete(server.serve())
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    return 0


def _run_daemon(config: BridgeConfig, pid_file: PIDFile) -> int:
    """Run as background daemon (double-fork)."""
    # First fork
    try:
        pid = os.fork()
        if pid > 0:
            # Parent - wait briefly then check child started
            time.sleep(0.5)
            if pid_file.is_running():
                print(f"Bridge started (PID {pid_file.read()})", file=sys.stderr)
                return 0
            else:
                print("Bridge failed to start", file=sys.stderr)
                return 1
    except OSError as e:
        print(f"Fork failed: {e}", file=sys.stderr)
        return 1

    # Child - decouple from parent
    os.setsid()
    os.umask(0)

    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            os._exit(0)
    except OSError:
        os._exit(1)

    # Grandchild - actual daemon
    # Redirect standard file descriptors
    sys.stdin = open(os.devnull)

    log_file = config.log_file
    sys.stdout = open(log_file, "a")
    sys.stderr = sys.stdout

    # Run the server
    return _run_foreground(config, pid_file)


def stop_daemon(config: BridgeConfig, timeout: float = 10.0) -> int:
    """Stop the running daemon.

    Args:
        config: Bridge configuration
        timeout: Seconds to wait for graceful shutdown

    Returns:
        Exit code (0 for success)
    """
    pid_file = PIDFile(config.pid_file)

    if not pid_file.is_running():
        print("Bridge is not running")
        return 0

    pid = pid_file.read()
    print(f"Stopping bridge (PID {pid})...")

    # Send SIGTERM for graceful shutdown
    if not send_signal(pid_file, signal.SIGTERM):
        print("Failed to send shutdown signal", file=sys.stderr)
        return 1

    # Wait for process to exit
    start = time.monotonic()
    while pid_file.is_running():
        if time.monotonic() - start > timeout:
            print("Timeout waiting for shutdown, sending SIGKILL...")
            send_signal(pid_file, signal.SIGKILL)
            time.sleep(0.5)
            break
        time.sleep(0.1)

    if not pid_file.is_running():
        print("Bridge stopped")
        return 0
    else:
        print("Failed to stop bridge", file=sys.stderr)
        return 1


def daemon_status(config: BridgeConfig) -> int:
    """Check daemon status.

    Returns:
        Exit code (0 if running, 1 if not)
    """
    pid_file = PIDFile(config.pid_file)

    if pid_file.is_running():
        pid = pid_file.read()
        print(f"Bridge is running (PID {pid})")
        print(f"  Host: {config.host}:{config.port}")
        print(f"  Runtime: {config.runtime_dir}")
        return 0
    else:
        print("Bridge is not running")
        return 1


def restart_daemon(config: BridgeConfig) -> int:
    """Restart the daemon.

    Returns:
        Exit code (0 for success)
    """
    stop_daemon(config)
    time.sleep(0.5)
    return start_daemon(config, foreground=False)
