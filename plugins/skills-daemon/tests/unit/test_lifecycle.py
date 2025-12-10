"""Unit tests for lifecycle management."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from skills_daemon.lifecycle import LifecycleManager


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
