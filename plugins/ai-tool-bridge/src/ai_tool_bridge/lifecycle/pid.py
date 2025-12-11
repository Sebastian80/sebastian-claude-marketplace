"""
PID File Management - Track daemon process.

Handles:
- Creating/removing PID files
- Checking if daemon is already running
- Stale PID cleanup
"""

import os
import signal
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class PIDFile:
    """Manages a PID file for the daemon process.

    The PID file prevents multiple daemon instances and allows
    clients to find the running daemon.

    Example:
        pid_file = PIDFile("/run/bridge.pid")

        if pid_file.is_running():
            print(f"Already running as PID {pid_file.read()}")
        else:
            pid_file.create()
            try:
                run_daemon()
            finally:
                pid_file.remove()
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def create(self) -> None:
        """Create PID file with current process ID.

        Raises:
            RuntimeError: If PID file already exists for running process
        """
        if self.is_running():
            raise RuntimeError(
                f"Daemon already running (PID {self.read()}). "
                f"PID file: {self.path}"
            )

        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Write PID atomically
        pid = os.getpid()
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(str(pid))
        tmp_path.rename(self.path)

        logger.info("pid_file_created", path=str(self.path), pid=pid)

    def remove(self) -> bool:
        """Remove PID file.

        Returns:
            True if file was removed, False if it didn't exist
        """
        try:
            self.path.unlink()
            logger.info("pid_file_removed", path=str(self.path))
            return True
        except FileNotFoundError:
            return False

    def read(self) -> int | None:
        """Read PID from file.

        Returns:
            PID as integer, or None if file doesn't exist or is invalid
        """
        try:
            content = self.path.read_text().strip()
            return int(content)
        except (FileNotFoundError, ValueError):
            return None

    def is_running(self) -> bool:
        """Check if daemon process is still running.

        Also cleans up stale PID files from crashed processes.

        Returns:
            True if daemon is running
        """
        pid = self.read()
        if pid is None:
            return False

        # Check if process exists
        if _process_exists(pid):
            return True

        # Stale PID file - process died without cleanup
        logger.warning("stale_pid_file", path=str(self.path), pid=pid)
        self.remove()
        return False

    def __enter__(self) -> "PIDFile":
        """Context manager: create PID file on entry."""
        self.create()
        return self

    def __exit__(self, *args) -> None:
        """Context manager: remove PID file on exit."""
        self.remove()


def _process_exists(pid: int) -> bool:
    """Check if a process with given PID exists.

    Uses signal 0 which doesn't actually send a signal,
    just checks if the process exists and we have permission.
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we don't have permission
        return True


def send_signal(pid_file: PIDFile, sig: signal.Signals) -> bool:
    """Send a signal to the daemon process.

    Args:
        pid_file: PID file to read daemon PID from
        sig: Signal to send (e.g., signal.SIGTERM)

    Returns:
        True if signal was sent successfully
    """
    pid = pid_file.read()
    if pid is None:
        logger.warning("no_pid_file", path=str(pid_file.path))
        return False

    if not _process_exists(pid):
        logger.warning("process_not_running", pid=pid)
        return False

    try:
        os.kill(pid, sig)
        logger.info("signal_sent", pid=pid, signal=sig.name)
        return True
    except (ProcessLookupError, PermissionError) as e:
        logger.error("signal_failed", pid=pid, signal=sig.name, error=str(e))
        return False
