"""
Background Health Monitor - Continuously monitors connector health.

Features:
- Periodic health checks for all connectors
- Auto-reconnection after failures
- Circuit breaker reset on recovery
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Background health monitor for connectors.

    Runs a continuous loop that:
    1. Checks health of each connector
    2. Updates healthy status
    3. Attempts reconnection after multiple failures
    4. Resets circuit breaker on recovery

    Example:
        monitor = HealthMonitor(connector_registry, interval=10.0)
        task = asyncio.create_task(monitor.run())

        # Later, on shutdown:
        await monitor.stop()
    """

    def __init__(
        self,
        registry: "ConnectorRegistry",
        interval: float = 10.0,
        reconnect_after_failures: int = 3,
    ):
        self.registry = registry
        self.interval = interval
        self.reconnect_after_failures = reconnect_after_failures
        self._failure_counts: dict[str, int] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    async def run(self) -> None:
        """Run the health monitoring loop."""
        self._running = True
        logger.info("Health monitor started (interval=%.1fs)", self.interval)

        while self._running:
            try:
                await asyncio.sleep(self.interval)
                await self._check_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

        logger.info("Health monitor stopped")

    async def stop(self) -> None:
        """Stop the health monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def start(self) -> asyncio.Task:
        """Start health monitor as background task."""
        self._task = asyncio.create_task(self.run())
        return self._task

    async def _check_all(self) -> None:
        """Check health of all connectors."""
        for connector in self.registry.all():
            await self._check_one(connector)

    async def _check_one(self, connector) -> None:
        """Check health of a single connector."""
        name = connector.name
        was_healthy = connector.healthy

        try:
            is_healthy = await connector.check_health()
        except Exception:
            is_healthy = False

        # Update connector health status
        connector._healthy = is_healthy

        if is_healthy:
            # Reset failure count on success
            self._failure_counts[name] = 0

            if not was_healthy:
                logger.info(f"Connector recovered: {name}")
                # Reset circuit breaker
                if hasattr(connector, "_circuit"):
                    connector._circuit.reset()
        else:
            # Increment failure count
            self._failure_counts[name] = self._failure_counts.get(name, 0) + 1

            if was_healthy:
                logger.warning(f"Connector unhealthy: {name}")

            # Attempt reconnection after multiple failures
            if self._failure_counts[name] >= self.reconnect_after_failures:
                logger.info(f"Attempting reconnection: {name}")
                try:
                    await connector.connect()
                    self._failure_counts[name] = 0
                except Exception as e:
                    logger.warning(f"Reconnection failed for {name}: {e}")
