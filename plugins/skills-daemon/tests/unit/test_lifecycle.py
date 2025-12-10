"""Unit tests for lifecycle management.

Tests cover:
- LifecycleManager class
- Standalone functions (read_pid, is_daemon_running, stop_daemon, cleanup_stale_pid)
- Edge cases and error handling
"""

import asyncio
import os
import signal
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from skills_daemon.lifecycle import (
    LifecycleManager,
    read_pid,
    is_daemon_running,
    stop_daemon,
    cleanup_stale_pid,
)


class TestLifecycleManager:
    """Tests for LifecycleManager."""

    def test_touch_updates_last_request_time(self):
        """touch() updates last request time."""
        manager = LifecycleManager()
        initial_time = manager.last_request_time

        with patch('time.time', return_value=initial_time + 100):
            manager.touch()

        assert manager.last_request_time > initial_time

    def test_check_idle_timeout_false_when_active(self):
        """Idle timeout not reached when recently touched."""
        manager = LifecycleManager(idle_timeout=60)
        manager.touch()

        assert manager.check_idle_timeout() is False

    def test_check_idle_timeout_true_when_idle(self):
        """Idle timeout reached after idle period."""
        manager = LifecycleManager(idle_timeout=60)

        # Simulate time passing
        manager.last_request_time = manager.last_request_time - 120

        assert manager.check_idle_timeout() is True

    def test_on_shutdown_registers_callback(self):
        """Can register shutdown callbacks."""
        manager = LifecycleManager()
        callback = MagicMock()

        manager.on_shutdown(callback)

        assert callback in manager._shutdown_callbacks

    @pytest.mark.asyncio
    async def test_run_shutdown_callbacks_executes_all(self):
        """Shutdown callbacks are all executed."""
        manager = LifecycleManager()
        results = []

        def sync_callback():
            results.append("sync")

        async def async_callback():
            results.append("async")

        manager.on_shutdown(sync_callback)
        manager.on_shutdown(async_callback)

        await manager.run_shutdown_callbacks(timeout=5)

        assert "sync" in results
        assert "async" in results

    @pytest.mark.asyncio
    async def test_run_shutdown_callbacks_handles_errors(self):
        """Callback errors don't stop other callbacks."""
        manager = LifecycleManager()
        results = []

        def error_callback():
            raise RuntimeError("Test error")

        def success_callback():
            results.append("success")

        manager.on_shutdown(error_callback)
        manager.on_shutdown(success_callback)

        await manager.run_shutdown_callbacks(timeout=5)

        assert "success" in results

    @pytest.mark.asyncio
    async def test_run_shutdown_callbacks_timeout_protection(self):
        """Shutdown callbacks timeout after specified duration."""
        manager = LifecycleManager()

        async def slow_callback():
            await asyncio.sleep(10)  # Very slow

        manager.on_shutdown(slow_callback)

        # Should complete quickly due to timeout (not wait 10s)
        import time
        start = time.time()
        await manager.run_shutdown_callbacks(timeout=0.1)
        elapsed = time.time() - start

        assert elapsed < 1  # Should timeout quickly, not wait 10s

    def test_shutdown_event_initially_not_set(self):
        """Shutdown event is not set on creation."""
        manager = LifecycleManager()

        assert not manager.shutdown_event.is_set()

    def test_shutdown_event_can_be_set(self):
        """Shutdown event can be triggered."""
        manager = LifecycleManager()

        manager.shutdown_event.set()

        assert manager.shutdown_event.is_set()


# ============================================================================
# read_pid() Tests
# ============================================================================

class TestReadPid:
    """Tests for read_pid() function."""

    def test_read_valid_pid(self, temp_dir, monkeypatch):
        """Reads valid PID from file."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("12345")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = read_pid()

        assert result == 12345

    def test_read_pid_with_whitespace(self, temp_dir, monkeypatch):
        """Reads PID even with surrounding whitespace."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("  12345\n  ")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = read_pid()

        assert result == 12345

    def test_read_pid_file_not_exists(self, temp_dir):
        """Returns None when file doesn't exist."""
        pid_file = temp_dir / "nonexistent.pid"

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = read_pid()

        assert result is None

    def test_read_pid_invalid_content(self, temp_dir):
        """Returns None when file contains non-integer."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("not-a-number")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = read_pid()

        assert result is None

    def test_read_pid_empty_file(self, temp_dir):
        """Returns None when file is empty."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = read_pid()

        assert result is None


# ============================================================================
# is_daemon_running() Tests
# ============================================================================

class TestIsDaemonRunning:
    """Tests for is_daemon_running() function."""

    def test_running_with_current_process(self, temp_dir):
        """Returns True for running process (use current PID)."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text(str(os.getpid()))

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = is_daemon_running()

        assert result is True

    def test_not_running_no_pid_file(self, temp_dir):
        """Returns False when no PID file."""
        pid_file = temp_dir / "nonexistent.pid"

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = is_daemon_running()

        assert result is False

    def test_not_running_stale_pid(self, temp_dir):
        """Returns False for stale PID (process doesn't exist)."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        # Use a very high PID unlikely to exist
        pid_file.write_text("999999999")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = is_daemon_running()

        assert result is False

    def test_not_running_invalid_pid(self, temp_dir):
        """Returns False for invalid PID in file."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("garbage")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = is_daemon_running()

        assert result is False


# ============================================================================
# stop_daemon() Tests
# ============================================================================

class TestStopDaemon:
    """Tests for stop_daemon() function."""

    def test_stop_no_pid_file(self, temp_dir):
        """Returns False when no PID file exists."""
        pid_file = temp_dir / "nonexistent.pid"

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = stop_daemon()

        assert result is False

    def test_stop_stale_pid(self, temp_dir):
        """Returns False when process doesn't exist."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("999999999")  # Non-existent PID

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            result = stop_daemon()

        assert result is False

    def test_stop_sends_sigterm(self, temp_dir):
        """Sends SIGTERM to process."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("12345")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            with patch("os.kill") as mock_kill:
                # Simulate process terminating after SIGTERM
                mock_kill.side_effect = [None, ProcessLookupError]

                result = stop_daemon()

        assert result is True
        mock_kill.assert_any_call(12345, signal.SIGTERM)

    def test_stop_sends_sigkill_after_timeout(self, temp_dir):
        """Sends SIGKILL if process doesn't terminate."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("12345")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            with patch("os.kill") as mock_kill:
                # Process keeps running (os.kill(pid, 0) succeeds)
                mock_kill.return_value = None
                with patch("time.sleep"):  # Speed up test
                    result = stop_daemon()

        assert result is True
        # Should have called SIGKILL after SIGTERM
        calls = [call[0] for call in mock_kill.call_args_list]
        assert (12345, signal.SIGTERM) in calls
        assert (12345, signal.SIGKILL) in calls


# ============================================================================
# cleanup_stale_pid() Tests
# ============================================================================

class TestCleanupStalePid:
    """Tests for cleanup_stale_pid() function."""

    def test_cleanup_removes_stale_file(self, temp_dir):
        """Removes PID file when process doesn't exist."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("999999999")  # Non-existent PID

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            cleanup_stale_pid()

        assert not pid_file.exists()

    def test_cleanup_keeps_active_pid(self, temp_dir):
        """Keeps PID file when process is running."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text(str(os.getpid()))  # Current process

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            cleanup_stale_pid()

        assert pid_file.exists()

    def test_cleanup_no_file_noop(self, temp_dir):
        """Does nothing when no PID file exists."""
        pid_file = temp_dir / "nonexistent.pid"

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            # Should not raise
            cleanup_stale_pid()

    def test_cleanup_handles_permission_error(self, temp_dir):
        """Handles permission errors gracefully."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("999999999")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            with patch.object(Path, "unlink", side_effect=PermissionError):
                # Should not raise
                cleanup_stale_pid()


# ============================================================================
# LifecycleManager PID File Tests
# ============================================================================

class TestLifecycleManagerPidFile:
    """Tests for LifecycleManager PID file operations."""

    def test_write_pid_file(self, temp_dir):
        """write_pid_file creates file with current PID."""
        pid_file = temp_dir / "state" / "daemon.pid"

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            manager = LifecycleManager()
            manager.write_pid_file()

        assert pid_file.exists()
        assert int(pid_file.read_text()) == os.getpid()

    def test_write_pid_file_creates_directory(self, temp_dir):
        """write_pid_file creates parent directories."""
        pid_file = temp_dir / "deep" / "nested" / "daemon.pid"

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            manager = LifecycleManager()
            manager.write_pid_file()

        assert pid_file.parent.exists()
        assert pid_file.exists()

    def test_remove_pid_file(self, temp_dir):
        """remove_pid_file deletes the file."""
        pid_file = temp_dir / "state" / "daemon.pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("12345")

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            manager = LifecycleManager()
            manager.remove_pid_file()

        assert not pid_file.exists()

    def test_remove_pid_file_missing_ok(self, temp_dir):
        """remove_pid_file doesn't error on missing file."""
        pid_file = temp_dir / "nonexistent.pid"

        with patch("skills_daemon.lifecycle.config") as mock_config:
            mock_config.pid_file = pid_file
            manager = LifecycleManager()
            # Should not raise
            manager.remove_pid_file()


# ============================================================================
# Idle Timeout Checker Tests
# ============================================================================

class TestIdleTimeoutChecker:
    """Tests for idle_timeout_checker background task."""

    @pytest.mark.asyncio
    async def test_checker_stops_on_shutdown_event(self):
        """Checker exits when shutdown event is set."""
        manager = LifecycleManager(idle_timeout=3600)

        # Set shutdown event immediately
        manager.shutdown_event.set()

        # Should return quickly
        task = asyncio.create_task(manager.idle_timeout_checker())
        await asyncio.wait_for(task, timeout=1.0)

    @pytest.mark.asyncio
    async def test_checker_sets_shutdown_on_timeout(self):
        """Checker sets shutdown event when idle timeout reached."""
        manager = LifecycleManager(idle_timeout=0)  # Immediate timeout

        # Simulate already idle
        manager.last_request_time = 0

        # Run checker with mocked sleep
        with patch("asyncio.sleep", new_callable=lambda: AsyncMock()):
            task = asyncio.create_task(manager.idle_timeout_checker())

            # Wait for shutdown event
            try:
                await asyncio.wait_for(manager.shutdown_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()
                pytest.fail("Shutdown event not set")

            task.cancel()

        assert manager.shutdown_event.is_set()


# Helper for async mock
class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)
