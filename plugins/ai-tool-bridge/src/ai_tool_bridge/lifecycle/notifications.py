"""
Desktop Notifications - Event-driven system notifications.

Subscribes to EventBus and shows desktop notifications via notify-send.
Decoupled from emitters - just reacts to events.

Events handled:
- intent="notify" - Generic notifications from plugins
- topic="plugin.*" from source="bridge" - Plugin lifecycle
- topic="error" - Errors from any source
"""

import shutil
import subprocess
from enum import Enum
from typing import TYPE_CHECKING, Callable

import structlog

if TYPE_CHECKING:
    from ..events import Event

logger = structlog.get_logger(__name__)


class NotifyLevel(Enum):
    """Notification urgency level."""

    INFO = "low"
    SUCCESS = "normal"
    WARNING = "normal"
    ERROR = "critical"


# Level mapping from string to enum
LEVEL_MAP = {
    "info": NotifyLevel.INFO,
    "success": NotifyLevel.SUCCESS,
    "warning": NotifyLevel.WARNING,
    "error": NotifyLevel.ERROR,
}


class Notifier:
    """Desktop notification sender with event bus integration.

    Core responsibility: Send notifications to desktop.
    Subscribes to events and formats them as notifications.
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

    # ─────────────────────────────────────────────────────────────────
    # Core send method
    # ─────────────────────────────────────────────────────────────────

    def send(
        self,
        title: str,
        message: str,
        level: NotifyLevel = NotifyLevel.INFO,
        icon: str | None = None,
    ) -> bool:
        """Send a desktop notification.

        Args:
            title: Notification title
            message: Notification body
            level: Urgency level
            icon: Optional icon name (default: dialog-information)

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

        icon = icon or "dialog-information"

        try:
            cmd = [
                self._notify_send,
                f"--urgency={level.value}",
                "--app-name=AI Tool Bridge",
                f"--icon={icon}",
                title,
                message,
            ]

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

    # ─────────────────────────────────────────────────────────────────
    # Convenience methods (for direct use)
    # ─────────────────────────────────────────────────────────────────

    def info(self, title: str, message: str) -> bool:
        return self.send(title, message, NotifyLevel.INFO)

    def success(self, title: str, message: str) -> bool:
        return self.send(title, message, NotifyLevel.SUCCESS)

    def warning(self, title: str, message: str) -> bool:
        return self.send(title, message, NotifyLevel.WARNING)

    def error(self, title: str, message: str) -> bool:
        return self.send(title, message, NotifyLevel.ERROR)

    # ─────────────────────────────────────────────────────────────────
    # Event handlers (subscribed via EventBus)
    # ─────────────────────────────────────────────────────────────────

    def handle_notify_intent(self, event: "Event") -> None:
        """Handle events with intent='notify'.

        Expected data:
            title: Notification title (optional, defaults to source)
            message: Notification body
            level: "info", "success", "warning", "error"
        """
        data = event.data
        title = data.get("title", f"⚡ {event.source.title()}")
        message = data.get("message", event.topic)
        level = LEVEL_MAP.get(data.get("level", "info"), NotifyLevel.INFO)

        self.send(title, message, level)

    def handle_plugin_lifecycle(self, event: "Event") -> None:
        """Handle plugin lifecycle events from bridge.

        Topics: plugin.loaded, plugin.unloaded, plugin.reloaded
        """
        data = event.data
        plugin_name = data.get("name", "Unknown")
        title = f"⚡ {plugin_name.title()}"

        if event.topic == "plugin.loaded":
            lines = ["✅ Plugin loaded"]
            deps = data.get("deps_installed", [])
            if deps:
                lines.append("")
                lines.append("📦 Installed:")
                for dep in deps[:5]:
                    lines.append(f"   ➕ {dep}")
                if len(deps) > 5:
                    lines.append(f"   ... +{len(deps) - 5} more")
            self.send(title, "\n".join(lines), NotifyLevel.SUCCESS)

        elif event.topic == "plugin.unloaded":
            lines = ["🔌 Plugin unloaded"]
            deps = data.get("deps_removed", [])
            if deps:
                lines.append("")
                lines.append("🧹 Cleaned:")
                for dep in deps[:5]:
                    lines.append(f"   ➖ {dep}")
                if len(deps) > 5:
                    lines.append(f"   ... +{len(deps) - 5} more")
            self.send(title, "\n".join(lines), NotifyLevel.INFO)

        elif event.topic == "plugin.reloaded":
            lines = ["🔄 Plugin reloaded"]
            installed = data.get("deps_installed", [])
            removed = data.get("deps_removed", [])
            if installed or removed:
                lines.append("")
                lines.append("📦 Dependencies:")
                for dep in installed[:3]:
                    lines.append(f"   ➕ {dep}")
                for dep in removed[:3]:
                    lines.append(f"   ➖ {dep}")
            self.send(title, "\n".join(lines), NotifyLevel.INFO)

    def handle_error(self, event: "Event") -> None:
        """Handle error events from any source."""
        title = f"⚠️ {event.source.title()}"
        message = event.data.get("message", event.topic)
        self.send(title, message, NotifyLevel.ERROR)

    def handle_daemon_lifecycle(self, event: "Event") -> None:
        """Handle daemon start/stop events."""
        if event.topic == "daemon.started":
            plugins = event.data.get("plugins", [])
            if plugins:
                msg = f"Ready ({', '.join(p.title() for p in plugins)})"
            else:
                msg = "Started (no plugins)"
            self.send("AI Tool Bridge", msg, NotifyLevel.INFO)

        elif event.topic == "daemon.stopped":
            self.send("AI Tool Bridge", "Daemon stopped", NotifyLevel.INFO)

    # ─────────────────────────────────────────────────────────────────
    # Event bus registration
    # ─────────────────────────────────────────────────────────────────

    def subscribe(self, bus: "EventBus") -> None:
        """Subscribe to relevant events on the bus."""
        from ..events import EventBus

        # Generic notifications from plugins
        bus.on(self.handle_notify_intent, intent="notify")

        # Plugin lifecycle from bridge
        bus.on(self.handle_plugin_lifecycle, source="bridge", topic="plugin.*")

        # Errors from anywhere
        bus.on(self.handle_error, topic="error")

        # Daemon lifecycle
        bus.on(self.handle_daemon_lifecycle, source="bridge", topic="daemon.*")

        logger.debug("notifier_subscribed")


# ─────────────────────────────────────────────────────────────────────────────
# Global instance
# ─────────────────────────────────────────────────────────────────────────────

_notifier: Notifier | None = None


def init_notifier(enabled: bool = True) -> Notifier:
    """Initialize the global notifier."""
    global _notifier
    _notifier = Notifier(enabled=enabled)
    return _notifier


def get_notifier() -> Notifier | None:
    """Get the global notifier instance."""
    return _notifier
