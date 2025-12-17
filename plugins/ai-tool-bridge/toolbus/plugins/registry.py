"""
Plugin Registry - Manages plugin lifecycle.

Plugins register themselves here; the bridge manages startup/shutdown.
Each plugin provides routes and may have connectors for external services.
"""

from typing import Any

import structlog

from ..contracts import PluginProtocol

__all__ = ["PluginRegistry", "plugin_registry"]

logger = structlog.get_logger(__name__)


class PluginRegistry:
    """Registry for plugins.

    Manages plugin lifecycle: registration, startup, shutdown, health.

    Example:
        registry = PluginRegistry()

        # Register plugin
        registry.register(jira_plugin)

        # Start all plugins
        await registry.startup_all()

        # Check health
        for name, status in registry.health_status().items():
            print(f"{name}: {status}")

        # Shutdown
        await registry.shutdown_all()
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginProtocol] = {}
        self._started: set[str] = set()
        self._cli_commands: dict[str, str] = {}  # plugin_name -> cli_command

    def register(self, plugin: PluginProtocol, cli_command: str | None = None) -> None:
        """Register a plugin.

        Args:
            plugin: Plugin instance implementing PluginProtocol
            cli_command: Optional CLI command name (e.g., "jira")
        """
        if plugin.name in self._plugins:
            logger.warning("plugin_already_registered", name=plugin.name)
            return

        self._plugins[plugin.name] = plugin
        if cli_command:
            self._cli_commands[plugin.name] = cli_command
        logger.info("plugin_registered", name=plugin.name, version=plugin.version)

    def unregister(self, name: str) -> PluginProtocol | None:
        """Unregister a plugin by name.

        Returns:
            The unregistered plugin, or None if not found
        """
        plugin = self._plugins.pop(name, None)
        if plugin:
            self._started.discard(name)
            logger.info("plugin_unregistered", name=name)
        return plugin

    def get(self, name: str) -> PluginProtocol | None:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins with their status."""
        result = []
        for name, plugin in self._plugins.items():
            info = {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "started": name in self._started,
            }
            if name in self._cli_commands:
                info["cli"] = self._cli_commands[name]
            result.append(info)
        return result

    async def startup(self, name: str) -> bool:
        """Start a specific plugin.

        Returns:
            True if startup succeeded
        """
        plugin = self._plugins.get(name)
        if not plugin:
            logger.warning("plugin_not_found", name=name)
            return False

        if name in self._started:
            logger.debug("plugin_already_started", name=name)
            return True

        try:
            await plugin.startup()
            self._started.add(name)
            logger.info("plugin_started", name=name)
            return True
        except Exception as e:
            logger.error("plugin_startup_failed", name=name, error=str(e))
            return False

    async def shutdown(self, name: str) -> bool:
        """Shutdown a specific plugin.

        Returns:
            True if shutdown succeeded
        """
        plugin = self._plugins.get(name)
        if not plugin:
            return False

        if name not in self._started:
            return True

        try:
            await plugin.shutdown()
            self._started.discard(name)
            logger.info("plugin_shutdown", name=name)
            return True
        except Exception as e:
            logger.error("plugin_shutdown_failed", name=name, error=str(e))
            return False

    async def startup_all(self) -> dict[str, bool]:
        """Start all registered plugins in parallel.

        Returns:
            Dict mapping plugin name to success status
        """
        import asyncio

        async def startup_one(name: str) -> tuple[str, bool]:
            return (name, await self.startup(name))

        tasks = [startup_one(n) for n in self._plugins]
        results_list = await asyncio.gather(*tasks)
        return dict(results_list)

    async def shutdown_all(self) -> dict[str, bool]:
        """Shutdown all started plugins.

        Returns:
            Dict mapping plugin name to success status
        """
        results = {}
        # Shutdown in reverse registration order
        for name in reversed(list(self._started)):
            results[name] = await self.shutdown(name)
        return results

    async def health_check(self, name: str) -> dict[str, Any]:
        """Check health of a specific plugin.

        Returns:
            Health status dict
        """
        plugin = self._plugins.get(name)
        if not plugin:
            return {"name": name, "status": "not_found"}

        if name not in self._started:
            return {"name": name, "status": "not_started"}

        try:
            return await plugin.health_check()
        except Exception as e:
            return {"name": name, "status": "error", "error": str(e)}

    async def health_status(self) -> dict[str, dict[str, Any]]:
        """Get health status of all plugins.

        Returns:
            Dict mapping plugin name to health status
        """
        return {name: await self.health_check(name) for name in self._plugins}

    def get_routers(self) -> list[tuple[str, Any]]:
        """Get all plugin routers for mounting.

        Returns:
            List of (prefix, router) tuples
        """
        routers = []
        for name, plugin in self._plugins.items():
            if plugin.router is not None:
                routers.append((f"/{name}", plugin.router))
        return routers

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        return name in self._plugins


# Global registry instance
plugin_registry = PluginRegistry()
