"""
Event Bus - Decoupled async pub/sub for plugin communication.

Design principles:
- YAGNI: Only what's needed, no event sourcing/persistence
- SOLID: Single responsibility, open for extension
- DRY: Reusable patterns, no duplication
- Performance: Minimal allocations, async-native

Usage:
    # Emit events
    await bus.emit("jira", "ticket.created", {"key": "PROJ-123"})

    # Subscribe with patterns
    bus.on(handler, topic="ticket.*")           # wildcard
    bus.on(handler, source="jira")              # filter by source
    bus.on(handler, intent="notify")            # filter by intent
    bus.on(handler)                             # receive all
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from fnmatch import fnmatch
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    pass

__all__ = [
    "Event",
    "EventBus",
    "Handler",
    "Subscription",
    "emit",
    "emit_fire_and_forget",
    "get_event_bus",
    "init_event_bus",
    "notify",
    "notify_fire_and_forget",
]

logger = structlog.get_logger(__name__)

# Type alias for handlers
Handler = Callable[["Event"], Any | Coroutine[Any, Any, Any]]


@dataclass(slots=True, frozen=True)
class Event:
    """Immutable event envelope.

    Attributes:
        source: Origin identifier (plugin name, "bridge")
        topic: What happened ("ticket.created", "error", "ready")
        data: Payload (any serializable dict)
        intent: Optional routing hint ("notify", "metric", "log")
        ts: Timestamp (auto-set)
    """
    source: str
    topic: str
    data: dict = field(default_factory=dict)
    intent: str | None = None
    ts: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass(slots=True)
class Subscription:
    """Single subscription with filters."""
    handler: Handler
    source: str = "*"
    topic: str = "*"
    intent: str | None = None

    def matches(self, event: Event) -> bool:
        """Check if event matches this subscription's filters."""
        if not fnmatch(event.source, self.source):
            return False
        if not fnmatch(event.topic, self.topic):
            return False
        if self.intent is not None and event.intent != self.intent:
            return False
        return True


class EventBus:
    """Async event bus with pattern-based subscriptions.

    Thread-safe for subscription management.
    Handlers run concurrently for performance.
    """

    __slots__ = ("_subs", "_middleware", "_logger")

    def __init__(self) -> None:
        self._subs: list[Subscription] = []
        self._middleware: list[Handler] = []
        self._logger = logger.bind(component="event_bus")

    def on(
        self,
        handler: Handler,
        *,
        source: str = "*",
        topic: str = "*",
        intent: str | None = None,
    ) -> Callable[[], None]:
        """Subscribe to events matching filters.

        Args:
            handler: Async or sync callable receiving Event
            source: Glob pattern for source filter
            topic: Glob pattern for topic filter
            intent: Exact match for intent (None = any)

        Returns:
            Unsubscribe function
        """
        sub = Subscription(handler, source, topic, intent)
        self._subs.append(sub)
        return lambda: self._subs.remove(sub) if sub in self._subs else None

    def use(self, middleware: Handler) -> None:
        """Add middleware (runs before handlers).

        Middleware can modify event or return None to cancel.
        """
        self._middleware.append(middleware)

    async def emit(
        self,
        source: str,
        topic: str,
        data: dict | None = None,
        intent: str | None = None,
    ) -> None:
        """Emit an event to all matching subscribers.

        Args:
            source: Who's emitting
            topic: What happened
            data: Event payload
            intent: Routing hint
        """
        event = Event(source, topic, data or {}, intent)

        # Run middleware (sequentially - can modify/cancel)
        for mw in self._middleware:
            result = mw(event)
            if asyncio.iscoroutine(result):
                result = await result
            if result is None:
                return  # Cancelled
            if isinstance(result, Event):
                event = result

        # Find matching handlers
        handlers = [s.handler for s in self._subs if s.matches(event)]

        if not handlers:
            return

        # Run handlers concurrently
        async def run_handler(h: Handler) -> None:
            try:
                result = h(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._logger.error(
                    "handler_error",
                    source=event.source,
                    topic=event.topic,
                    error=str(e),
                )

        await asyncio.gather(*[run_handler(h) for h in handlers])

    def emit_sync(
        self,
        source: str,
        topic: str,
        data: dict | None = None,
        intent: str | None = None,
    ) -> None:
        """Fire-and-forget emit for sync contexts."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.emit(source, topic, data, intent))
        except RuntimeError:
            # No event loop - skip
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Global singleton
# ─────────────────────────────────────────────────────────────────────────────

_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def init_event_bus() -> EventBus:
    """Initialize fresh event bus (for testing)."""
    global _bus
    _bus = EventBus()
    return _bus


# ─────────────────────────────────────────────────────────────────────────────
# Functional helpers - composition over inheritance
# ─────────────────────────────────────────────────────────────────────────────

async def emit(
    source: str,
    topic: str,
    data: dict | None = None,
    intent: str | None = None,
) -> None:
    """Emit event to global bus.

    Usage in plugins:
        from toolbus.events import emit, notify

        async def create_ticket(self):
            await emit(self.name, "ticket.created", {"key": key})
    """
    bus = get_event_bus()
    await bus.emit(source, topic, data, intent)


def emit_fire_and_forget(
    source: str,
    topic: str,
    data: dict | None = None,
    intent: str | None = None,
) -> None:
    """Fire-and-forget emit for sync contexts."""
    bus = get_event_bus()
    bus.emit_sync(source, topic, data, intent)


async def notify(
    source: str,
    title: str,
    message: str,
    level: str = "info",
) -> None:
    """Send notification via event bus.

    Usage in plugins:
        from toolbus.events import notify

        await notify(self.name, "Ticket Created", f"{key}: {summary}", "success")

    Args:
        source: Plugin name (for notification grouping)
        title: Notification title
        message: Notification body
        level: "info", "success", "warning", "error"
    """
    await emit(
        source,
        "notification",
        {"title": title, "message": message, "level": level},
        intent="notify",
    )


def notify_fire_and_forget(
    source: str,
    title: str,
    message: str,
    level: str = "info",
) -> None:
    """Fire-and-forget notify for sync contexts."""
    emit_fire_and_forget(
        source,
        "notification",
        {"title": title, "message": message, "level": level},
        intent="notify",
    )
