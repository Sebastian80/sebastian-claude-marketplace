"""
Daemon lifecycle management: PID file, signals, idle timeout.
"""

import asyncio
import os
import signal
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from . import PID_FILE, IDLE_TIMEOUT
from .logging import logger


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
            Path(PID_FILE).write_text(str(os.getpid()))
            logger.info("PID file written", pid=os.getpid(), path=PID_FILE)
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not write PID file: {e}")

    def remove_pid_file(self) -> None:
        """Remove PID file."""
        try:
            Path(PID_FILE).unlink(missing_ok=True)
        except (OSError, PermissionError):
            pass

    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        def handle_signal(signum: int) -> None:
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))

    def touch(self) -> None:
        """Update last request time (call on each request)."""
        self.last_request_time = time.time()

    def check_idle_timeout(self) -> bool:
        """Check if idle timeout has been reached."""
        return (time.time() - self.last_request_time) > self.idle_timeout

    def on_shutdown(self, callback: Callable) -> None:
        """Register a shutdown callback."""
        self._shutdown_callbacks.append(callback)

    async def run_shutdown_callbacks(self) -> None:
        """Run all registered shutdown callbacks."""
        for callback in self._shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Shutdown callback failed: {e}")

    async def idle_timeout_checker(self) -> None:
        """Background task to check for idle timeout."""
        while not self.shutdown_event.is_set():
            await asyncio.sleep(60)  # Check every minute
            if self.check_idle_timeout():
                logger.info("Idle timeout reached, shutting down...")
                self.shutdown_event.set()
                break


def read_pid() -> Optional[int]:
    """Read PID from file."""
    try:
        return int(Path(PID_FILE).read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def is_daemon_running() -> bool:
    """Check if daemon is running."""
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def stop_daemon() -> bool:
    """Stop the running daemon."""
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
