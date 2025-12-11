"""
Signal Handling - Graceful shutdown support.

Handles SIGTERM, SIGINT for clean daemon shutdown.
Integrates with asyncio event loop.
"""

import asyncio
import signal
from typing import Callable

import structlog

logger = structlog.get_logger(__name__)


class SignalHandler:
    """Handles OS signals for graceful shutdown.

    Captures SIGTERM and SIGINT, sets a shutdown event,
    and calls registered callbacks.

    Example:
        handler = SignalHandler()
        handler.register(cleanup_function)

        async def main():
            handler.setup()
            while not handler.shutdown_event.is_set():
                await do_work()
                await asyncio.sleep(1)
            await handler.wait_for_shutdown()
    """

    def __init__(self) -> None:
        self._callbacks: list[Callable[[], None]] = []
        self._async_callbacks: list[Callable[[], asyncio.Future]] = []
        self._shutdown_event: asyncio.Event | None = None
        self._signals_received: list[signal.Signals] = []

    @property
    def shutdown_event(self) -> asyncio.Event:
        """Event that's set when shutdown signal is received."""
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
        return self._shutdown_event

    @property
    def should_shutdown(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_event is not None and self._shutdown_event.is_set()

    def setup(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Register signal handlers with the event loop.

        Args:
            loop: Event loop to use (defaults to running loop)
        """
        if loop is None:
            loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_signal, sig)

        logger.info("signal_handlers_registered", signals=["SIGTERM", "SIGINT"])

    def register(self, callback: Callable[[], None]) -> None:
        """Register a synchronous callback for shutdown.

        Args:
            callback: Function to call on shutdown
        """
        self._callbacks.append(callback)

    def register_async(self, callback: Callable[[], asyncio.Future]) -> None:
        """Register an async callback for shutdown.

        Args:
            callback: Async function to call on shutdown
        """
        self._async_callbacks.append(callback)

    def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle received signal."""
        self._signals_received.append(sig)
        logger.info("signal_received", signal=sig.name, count=len(self._signals_received))

        if len(self._signals_received) == 1:
            # First signal - initiate graceful shutdown
            self.shutdown_event.set()
            self._run_sync_callbacks()
        elif len(self._signals_received) >= 2:
            # Second signal - force exit
            logger.warning("forced_shutdown", signal=sig.name)
            raise SystemExit(128 + sig.value)

    def _run_sync_callbacks(self) -> None:
        """Run all synchronous callbacks."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                logger.error("callback_error", error=str(e))

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal and run async callbacks."""
        await self.shutdown_event.wait()

        # Run async callbacks
        for callback in self._async_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error("async_callback_error", error=str(e))

        logger.info("shutdown_complete")

    def trigger_shutdown(self) -> None:
        """Programmatically trigger shutdown (e.g., for idle timeout)."""
        logger.info("programmatic_shutdown")
        self.shutdown_event.set()
        self._run_sync_callbacks()


# Global handler instance
signal_handler = SignalHandler()
