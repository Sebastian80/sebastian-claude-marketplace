"""Tests for lifecycle management."""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from ai_tool_bridge.lifecycle import IdleMonitor, PIDFile, SignalHandler


class TestPIDFile:
    """Test PID file management."""

    def test_create_pid_file(self, temp_dir):
        """Creates PID file with current process ID."""
        pid_path = temp_dir / "test.pid"
        pid_file = PIDFile(pid_path)

        pid_file.create()

        assert pid_path.exists()
        assert int(pid_path.read_text()) == os.getpid()

    def test_remove_pid_file(self, temp_dir):
        """Removes PID file."""
        pid_path = temp_dir / "test.pid"
        pid_file = PIDFile(pid_path)
        pid_file.create()

        result = pid_file.remove()

        assert result is True
        assert not pid_path.exists()

    def test_remove_nonexistent(self, temp_dir):
        """Removing nonexistent file returns False."""
        pid_path = temp_dir / "nonexistent.pid"
        pid_file = PIDFile(pid_path)

        result = pid_file.remove()

        assert result is False

    def test_read_pid(self, temp_dir):
        """Reads PID from file."""
        pid_path = temp_dir / "test.pid"
        pid_path.write_text("12345")
        pid_file = PIDFile(pid_path)

        result = pid_file.read()

        assert result == 12345

    def test_read_nonexistent(self, temp_dir):
        """Reading nonexistent file returns None."""
        pid_file = PIDFile(temp_dir / "nonexistent.pid")

        result = pid_file.read()

        assert result is None

    def test_is_running_current_process(self, temp_dir):
        """Detects current process as running."""
        pid_path = temp_dir / "test.pid"
        pid_file = PIDFile(pid_path)
        pid_file.create()

        result = pid_file.is_running()

        assert result is True
        pid_file.remove()

    def test_is_running_stale_pid(self, temp_dir):
        """Detects and cleans up stale PID files."""
        pid_path = temp_dir / "test.pid"
        # Write a PID that definitely doesn't exist
        pid_path.write_text("999999999")
        pid_file = PIDFile(pid_path)

        result = pid_file.is_running()

        assert result is False
        assert not pid_path.exists()  # Cleaned up

    def test_context_manager(self, temp_dir):
        """Works as context manager."""
        pid_path = temp_dir / "test.pid"
        pid_file = PIDFile(pid_path)

        with pid_file:
            assert pid_path.exists()

        assert not pid_path.exists()

    def test_create_raises_if_running(self, temp_dir):
        """Raises if daemon already running."""
        pid_path = temp_dir / "test.pid"
        pid_file = PIDFile(pid_path)
        pid_file.create()

        with pytest.raises(RuntimeError):
            pid_file.create()

        pid_file.remove()


class TestSignalHandler:
    """Test signal handler."""

    def test_initial_state(self):
        """Starts with shutdown not requested."""
        handler = SignalHandler()

        assert handler.should_shutdown is False

    def test_trigger_shutdown(self):
        """Can trigger shutdown programmatically."""
        handler = SignalHandler()

        handler.trigger_shutdown()

        assert handler.should_shutdown is True

    def test_register_callback(self):
        """Registered callbacks are called on shutdown."""
        handler = SignalHandler()
        called = []

        handler.register(lambda: called.append("called"))
        handler.trigger_shutdown()

        assert "called" in called

    @pytest.mark.asyncio
    async def test_register_async_callback(self):
        """Async callbacks are called on shutdown."""
        handler = SignalHandler()
        called = []

        async def async_callback():
            called.append("async_called")

        handler.register_async(async_callback)
        handler.trigger_shutdown()
        await handler.wait_for_shutdown()

        assert "async_called" in called


class TestIdleMonitor:
    """Test idle shutdown monitoring."""

    def test_initial_state(self):
        """Starts not idle."""
        monitor = IdleMonitor(timeout_seconds=60)

        assert monitor.is_idle is False
        assert monitor.idle_seconds < 1

    def test_touch_resets_timer(self):
        """Touch resets the idle timer."""
        monitor = IdleMonitor(timeout_seconds=60)

        initial = monitor.idle_seconds
        monitor.touch()
        after = monitor.idle_seconds

        assert after <= initial

    def test_is_idle_after_timeout(self):
        """Reports idle after timeout."""
        monitor = IdleMonitor(timeout_seconds=0.01)

        import time
        time.sleep(0.02)

        assert monitor.is_idle is True

    @pytest.mark.asyncio
    async def test_calls_callback_on_idle(self):
        """Calls on_idle callback when timeout reached."""
        called = []
        monitor = IdleMonitor(
            timeout_seconds=0.05,
            check_interval=0.02,
            on_idle=lambda: called.append("idle"),
        )

        await monitor.start()
        await asyncio.sleep(0.15)
        await monitor.stop()

        assert "idle" in called

    @pytest.mark.asyncio
    async def test_stop_cancels_monitoring(self):
        """Stop cancels the monitoring task."""
        monitor = IdleMonitor(timeout_seconds=10)

        await monitor.start()
        assert monitor._running is True

        await monitor.stop()
        assert monitor._running is False

    def test_status(self):
        """Status returns monitoring info."""
        monitor = IdleMonitor(timeout_seconds=60)

        status = monitor.status()

        assert "running" in status
        assert "idle_seconds" in status
        assert "timeout_seconds" in status
        assert status["timeout_seconds"] == 60


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
