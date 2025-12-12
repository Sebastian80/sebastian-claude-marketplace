"""
Lifecycle - Daemon process management.

Handles:
- PID file management (prevent duplicate instances)
- Signal handling (graceful shutdown on SIGTERM/SIGINT)
- Idle monitoring (auto-shutdown after inactivity)
- Desktop notifications (plugin connect/error events)

Example:
    from ai_tool_bridge.lifecycle import (
        PIDFile,
        SignalHandler,
        IdleMonitor,
    )

    async def run_daemon():
        pid_file = PIDFile("~/.local/share/ai-tool-bridge/bridge.pid")
        signal_handler = SignalHandler()
        idle_monitor = IdleMonitor(timeout_seconds=300)

        with pid_file:
            signal_handler.setup()
            signal_handler.register_async(idle_monitor.stop)

            await idle_monitor.start()

            while not signal_handler.should_shutdown:
                await asyncio.sleep(1)

            await signal_handler.wait_for_shutdown()
"""

from .idle import IdleMonitor
from .notifications import Notifier, NotifyLevel, get_notifier, init_notifier
from .pid import PIDFile, send_signal
from .signals import SignalHandler, signal_handler

__all__ = [
    "IdleMonitor",
    "Notifier",
    "NotifyLevel",
    "get_notifier",
    "init_notifier",
    "PIDFile",
    "send_signal",
    "SignalHandler",
    "signal_handler",
]
