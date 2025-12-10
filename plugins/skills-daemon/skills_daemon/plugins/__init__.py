"""
Plugin interface for skills daemon.
"""

from abc import ABC, abstractmethod
from typing import Any

from fastapi import APIRouter


class SkillPlugin(ABC):
    """Base class for skill plugins.

    Each plugin provides:
    - A name (used in URL prefix: /<plugin>/)
    - A FastAPI router with endpoints
    - Optional startup/shutdown hooks
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name (used in URL prefix)."""
        pass

    @property
    @abstractmethod
    def router(self) -> APIRouter:
        """FastAPI router with all endpoints."""
        pass

    @property
    def description(self) -> str:
        """Plugin description for /plugins endpoint."""
        return ""

    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"

    async def startup(self) -> None:
        """Called on daemon startup. Override to initialize resources."""
        pass

    async def connect(self) -> None:
        """Called after startup() to establish backend connection.

        Override to:
        - Connect to external APIs (Jira, Confluence, etc.)
        - Initialize database connections
        - Start background workers

        Exceptions are logged but don't prevent daemon from running.
        """
        pass

    async def reconnect(self) -> None:
        """Re-establish connection after failure.

        Default implementation calls connect().
        Override for custom reconnection logic (e.g., with backoff).
        """
        await self.connect()

    async def shutdown(self) -> None:
        """Called on daemon shutdown. Override to cleanup resources."""
        pass

    def health_check(self) -> dict[str, Any]:
        """Return plugin health status. Override for custom checks."""
        return {"status": "ok"}


class PluginRegistry:
    """Registry for loaded plugins."""

    def __init__(self):
        self._plugins: dict[str, SkillPlugin] = {}

    def register(self, plugin: SkillPlugin) -> None:
        """Register a plugin."""
        self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> SkillPlugin | None:
        """Unregister a plugin by name."""
        return self._plugins.pop(name, None)

    def clear(self) -> list[str]:
        """Clear all plugins. Returns list of removed plugin names."""
        names = list(self._plugins.keys())
        self._plugins.clear()
        return names

    def get(self, name: str) -> SkillPlugin | None:
        """Get plugin by name."""
        return self._plugins.get(name)

    def all(self) -> list[SkillPlugin]:
        """Get all registered plugins."""
        return list(self._plugins.values())

    def names(self) -> list[str]:
        """Get all plugin names."""
        return list(self._plugins.keys())


# Global registry
registry = PluginRegistry()
