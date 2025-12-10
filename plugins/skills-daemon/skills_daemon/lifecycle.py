"""
Daemon lifecycle management: PID file, signals, idle timeout.

This module is the SINGLE SOURCE OF TRUTH for daemon state functions.
CLI scripts should import from here instead of redefining.
"""

import asyncio
import os
import signal
import sys
import time
from pathlib import Path
from typing import Callable

from .config import config
from .logging import logger

# Use config directly - no re-exports needed
IDLE_TIMEOUT = config.idle_timeout


class LifecycleManager:
    """Manages daemon lifecycle: startup, shutdown, idle timeout."""

    def __init__(self, idle_timeout: int = IDLE_TIMEOUT):
        self.idle_timeout = idle_timeout
        self.last_request_time = time.time()
        self.shutdown_event = asyncio.Event()
        self._shutdown_callbacks: list[Callable] = []

    def write_pid_file(self) -> None:
        """Write PID to file."""
        try:
            config.pid_file.parent.mkdir(parents=True, exist_ok=True)
            config.pid_file.write_text(str(os.getpid()))
            logger.info("PID file written", pid=os.getpid(), path=str(config.pid_file))
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not write PID file: {e}")

    def remove_pid_file(self) -> None:
        """Remove PID file."""
        try:
            config.pid_file.unlink(missing_ok=True)
        except (OSError, PermissionError):
            pass

    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        def handle_signal(signum: int) -> None:
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))
            except (RuntimeError, NotImplementedError):
                # Signal handlers only work in main thread
                # Skip setup in tests or non-main threads
                logger.debug(f"Skipping signal handler setup (not in main thread)")

    def touch(self) -> None:
        """Update last request time (call on each request)."""
        self.last_request_time = time.time()

    def check_idle_timeout(self) -> bool:
        """Check if idle timeout has been reached."""
        return (time.time() - self.last_request_time) > self.idle_timeout

    def on_shutdown(self, callback: Callable) -> None:
        """Register a shutdown callback."""
        self._shutdown_callbacks.append(callback)

    async def run_shutdown_callbacks(self, timeout: float | None = None) -> None:
        """Run all registered shutdown callbacks with timeout protection.

        Args:
            timeout: Maximum time to wait for all callbacks (default: config.shutdown_timeout)
        """
        if timeout is None:
            timeout = config.shutdown_timeout

        async def _run_callbacks():
            for callback in self._shutdown_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Shutdown callback failed: {e}")

        try:
            await asyncio.wait_for(_run_callbacks(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(
                f"Shutdown callbacks timed out after {timeout}s, forcing shutdown"
            )

    async def idle_timeout_checker(self) -> None:
        """Background task to check for idle timeout."""
        while not self.shutdown_event.is_set():
            await asyncio.sleep(60)  # Check every minute
            if self.check_idle_timeout():
                logger.info("Idle timeout reached, shutting down...")
                self.shutdown_event.set()
                break


# ═══════════════════════════════════════════════════════════════════════════════
# Standalone daemon state functions (SINGLE SOURCE OF TRUTH)
# Import these in CLI scripts instead of redefining
# ═══════════════════════════════════════════════════════════════════════════════

def read_pid() -> int | None:
    """Read PID from file.

    Returns:
        PID if file exists and is valid, None otherwise.
    """
    try:
        return int(config.pid_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def is_daemon_running() -> bool:
    """Check if daemon process is running (via PID file).

    Returns:
        True if process exists, False otherwise.
    """
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def stop_daemon() -> bool:
    """Stop the running daemon gracefully.

    Sends SIGTERM, waits up to 1s, then SIGKILL if still running.

    Returns:
        True if daemon was stopped, False if not running.
    """
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for process to terminate
        for _ in range(10):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except (OSError, ProcessLookupError):
                return True
        # Force kill if still running
        os.kill(pid, signal.SIGKILL)
        return True
    except (OSError, ProcessLookupError):
        return False


def cleanup_stale_pid() -> None:
    """Remove PID file if process doesn't exist.

    Call this before starting daemon to clean up stale state.
    """
    pid = read_pid()
    if pid is not None:
        try:
            os.kill(pid, 0)
            # Process exists - don't clean up
        except (OSError, ProcessLookupError):
            # Process doesn't exist - clean up stale PID file
            try:
                config.pid_file.unlink(missing_ok=True)
            except (OSError, PermissionError):
                pass
