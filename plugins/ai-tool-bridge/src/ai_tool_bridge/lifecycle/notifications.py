"""
Desktop Notifications - System notifications for daemon events.

Uses notify-send on Linux for desktop notifications.
Notifications are configurable via BRIDGE_NOTIFICATIONS env var.

Events:
- Plugin connect success/failure
- Connector connect success/failure
- Daemon startup/shutdown
"""

import shutil
import subprocess
from enum import Enum
from typing import Callable

import structlog

logger = structlog.get_logger(__name__)


class NotifyLevel(Enum):
    """Notification urgency level."""

    INFO = "low"
    SUCCESS = "normal"
    WARNING = "normal"
    ERROR = "critical"


class Notifier:
    """Desktop notification sender.

    Sends notifications via notify-send on Linux.
    Gracefully degrades if notify-send is not available.

    Example:
        notifier = Notifier(enabled=True)
        notifier.success("Jira", "Connected successfully")
        notifier.error("Jira", "Connection failed: timeout")
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._notify_send = shutil.which("notify-send")
        self._callbacks: list[Callable[[str, str, NotifyLevel], None]] = []

        if enabled and not self._notify_send:
            logger.warning("notify_send_not_found", message="Desktop notifications disabled")

    @property
    def available(self) -> bool:
        """Check if notifications are available."""
        return self._enabled and self._notify_send is not None

    def add_callback(self, callback: Callable[[str, str, NotifyLevel], None]) -> None:
        """Add a callback for notifications (useful for testing)."""
        self._callbacks.append(callback)

    def _send(self, title: str, message: str, level: NotifyLevel, icon: str | None = None) -> bool:
        """Send a desktop notification.

        Args:
            title: Notification title
            message: Notification body
            level: Urgency level
            icon: Optional icon name

        Returns:
            True if notification was sent
        """
        # Call callbacks first (for testing/logging)
        for callback in self._callbacks:
            try:
                callback(title, message, level)
            except Exception:
                pass

        if not self.available:
            return False

        try:
            cmd = [
                self._notify_send,
                f"--urgency={level.value}",
                "--app-name=AI Tool Bridge",
            ]

            if icon:
                cmd.append(f"--icon={icon}")

            cmd.extend([title, message])

            subprocess.run(cmd, check=True, capture_output=True, timeout=5)
            logger.debug("notification_sent", title=title, level=level.name)
            return True

        except subprocess.TimeoutExpired:
            logger.warning("notification_timeout", title=title)
            return False
        except subprocess.CalledProcessError as e:
            logger.warning("notification_failed", title=title, error=str(e))
            return False
        except Exception as e:
            logger.warning("notification_error", title=title, error=str(e))
            return False

    def info(self, title: str, message: str) -> bool:
        """Send an info notification."""
        return self._send(title, message, NotifyLevel.INFO, icon="dialog-information")

    def success(self, title: str, message: str) -> bool:
        """Send a success notification."""
        return self._send(title, message, NotifyLevel.SUCCESS, icon="emblem-ok-symbolic")

    def warning(self, title: str, message: str) -> bool:
        """Send a warning notification."""
        return self._send(title, message, NotifyLevel.WARNING, icon="dialog-warning")

    def error(self, title: str, message: str) -> bool:
        """Send an error notification."""
        return self._send(title, message, NotifyLevel.ERROR, icon="dialog-error")

    # Convenience methods for common events

    def plugin_connected(self, plugin_name: str) -> bool:
        """Notify that a plugin connected successfully."""
        return self.success(
            f"AI Bridge: {plugin_name.title()}",
            "Connected successfully",
        )

    def plugin_connection_failed(self, plugin_name: str, error: str) -> bool:
        """Notify that a plugin connection failed."""
        # Truncate error if too long
        if len(error) > 100:
            error = error[:97] + "..."
        return self.error(
            f"AI Bridge: {plugin_name.title()}",
            f"Connection failed: {error}",
        )

    def plugin_started(self, plugin_name: str) -> bool:
        """Notify that a plugin started successfully."""
        return self.success(
            f"AI Bridge: {plugin_name.title()}",
            "Plugin started",
        )

    def plugin_start_failed(self, plugin_name: str, error: str) -> bool:
        """Notify that a plugin failed to start."""
        if len(error) > 100:
            error = error[:97] + "..."
        return self.error(
            f"AI Bridge: {plugin_name.title()}",
            f"Failed to start: {error}",
        )

    def connector_connected(self, connector_name: str) -> bool:
        """Notify that a connector connected successfully."""
        return self.success(
            f"AI Bridge: {connector_name.title()}",
            "Service connected",
        )

    def connector_connection_failed(self, connector_name: str, error: str) -> bool:
        """Notify that a connector connection failed."""
        if len(error) > 100:
            error = error[:97] + "..."
        return self.error(
            f"AI Bridge: {connector_name.title()}",
            f"Connection failed: {error}",
        )

    def daemon_started(self, plugins: list[str]) -> bool:
        """Notify that the daemon started."""
        if not plugins:
            message = "Started (no plugins)"
        else:
            plugin_list = ", ".join(p.title() for p in plugins)
            message = f"Ready ({plugin_list})"
        return self.info("AI Tool Bridge", message)

    def daemon_stopped(self) -> bool:
        """Notify that the daemon stopped."""
        return self.info(
            "AI Tool Bridge",
            "Daemon stopped",
        )


# Global notifier instance (configured during app startup)
notifier: Notifier | None = None


def init_notifier(enabled: bool = True) -> Notifier:
    """Initialize the global notifier.

    Args:
        enabled: Whether notifications are enabled

    Returns:
        The notifier instance
    """
    global notifier
    notifier = Notifier(enabled=enabled)
    return notifier


def get_notifier() -> Notifier | None:
    """Get the global notifier instance."""
    return notifier
