"""
Idle Shutdown - Auto-shutdown after inactivity.

Tracks request activity and shuts down the daemon
when idle for too long. Saves resources when not in use.
"""

import asyncio
import time
from collections.abc import Callable

import structlog

__all__ = ["IdleMonitor"]

logger = structlog.get_logger(__name__)


class IdleMonitor:
    """Monitors activity and triggers shutdown after idle timeout.

    Tracks the last activity timestamp. A background task checks
    periodically if the idle timeout has been exceeded.

    Example:
        monitor = IdleMonitor(
            timeout_seconds=300,  # 5 minutes
            on_idle=shutdown_callback,
        )

        # Start monitoring
        await monitor.start()

        # Call on each request
        monitor.touch()

        # Stop when shutting down
        await monitor.stop()
    """

    def __init__(
        self,
        timeout_seconds: float = 300.0,
        check_interval: float = 30.0,
        on_idle: Callable[[], None] | None = None,
    ) -> None:
        """Initialize idle monitor.

        Args:
            timeout_seconds: Seconds of inactivity before idle
            check_interval: How often to check for idle (seconds)
            on_idle: Callback when idle timeout reached
        """
        self.timeout_seconds = timeout_seconds
        self.check_interval = check_interval
        self.on_idle = on_idle

        self._last_activity: float = time.monotonic()
        self._task: asyncio.Task | None = None
        self._running = False

    @property
    def idle_seconds(self) -> float:
        """Seconds since last activity."""
        return time.monotonic() - self._last_activity

    @property
    def is_idle(self) -> bool:
        """Check if currently idle (past timeout)."""
        return self.idle_seconds >= self.timeout_seconds

    def touch(self) -> None:
        """Record activity (call on each request)."""
        self._last_activity = time.monotonic()

    async def start(self) -> None:
        """Start the idle monitoring background task."""
        if self._running:
            return

        self._running = True
        self._last_activity = time.monotonic()
        self._task = asyncio.create_task(self._monitor_loop())

        logger.info(
            "idle_monitor_started",
            timeout=self.timeout_seconds,
            check_interval=self.check_interval,
        )

    async def stop(self) -> None:
        """Stop the idle monitoring task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("idle_monitor_stopped")

    async def _monitor_loop(self) -> None:
        """Background loop that checks for idle state."""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)

                if not self._running:
                    break

                if self.is_idle:
                    logger.info(
                        "idle_timeout_reached",
                        idle_seconds=self.idle_seconds,
                        timeout=self.timeout_seconds,
                    )
                    if self.on_idle:
                        self.on_idle()
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("idle_monitor_error", error=str(e))

    def status(self) -> dict:
        """Get current idle status."""
        return {
            "running": self._running,
            "idle_seconds": round(self.idle_seconds, 1),
            "timeout_seconds": self.timeout_seconds,
            "is_idle": self.is_idle,
            "time_until_idle": max(0, round(self.timeout_seconds - self.idle_seconds, 1)),
        }
