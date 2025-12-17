"""
Hot Reload - Automatic plugin reload on manifest changes.

Monitors plugin manifests for changes and hot-reloads affected plugins
without requiring a full daemon restart.

Features:
- Periodic manifest hash checking (configurable interval)
- Hot-reload individual plugins (unmount routes, reimport, remount)
- Sync deps when dependencies change
- Graceful handling of new/removed plugins
- Watches Claude Code's installed_plugins.json for enable/disable changes
"""

import asyncio
import hashlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from .deps import sync_dependencies
from .events import get_event_bus
from .plugins.discovery import (
    INSTALLED_PLUGINS_PATH,
    SETTINGS_PATH,
    PluginManifest,
    discover_plugins,
)
from .plugins.loader import load_plugin
from .plugins.registry import plugin_registry

if TYPE_CHECKING:
    from fastapi import APIRouter, FastAPI

    from .config import BridgeConfig

__all__ = ["HotReloader", "ManifestTracker", "get_hot_reloader", "init_hot_reloader"]

logger = structlog.get_logger(__name__)


class ManifestTracker:
    """Tracks manifest file hashes for change detection."""

    def __init__(self) -> None:
        self._hashes: dict[str, str] = {}  # name -> hash
        self._paths: dict[str, Path] = {}  # name -> manifest path

    def compute_hash(self, manifest_path: Path) -> str:
        """Compute hash of manifest file."""
        content = manifest_path.read_text()
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def update(self, name: str, manifest_path: Path) -> bool:
        """Update hash for a manifest, return True if changed."""
        new_hash = self.compute_hash(manifest_path)
        old_hash = self._hashes.get(name)

        self._hashes[name] = new_hash
        self._paths[name] = manifest_path

        if old_hash is None:
            # New plugin
            return True
        return new_hash != old_hash

    def remove(self, name: str) -> None:
        """Remove tracking for a plugin."""
        self._hashes.pop(name, None)
        self._paths.pop(name, None)

    def get_tracked(self) -> set[str]:
        """Get set of tracked plugin names."""
        return set(self._hashes.keys())


class HotReloader:
    """Manages hot-reloading of plugins."""

    def __init__(
        self,
        app: "FastAPI",
        config: "BridgeConfig",
        check_interval: float = 5.0,
    ) -> None:
        self._app = app
        self._config = config
        self._check_interval = check_interval
        self._tracker = ManifestTracker()
        self._running = False
        self._task: asyncio.Task | None = None
        self._manifests: dict[str, PluginManifest] = {}  # name -> manifest
        self._claude_state_hash: str | None = None  # Track Claude Code's plugin state

    def _compute_claude_state_hash(self) -> str | None:
        """Compute combined hash of Claude Code's plugin state files.

        Tracks both installed_plugins.json and settings.json (enabledPlugins).
        """
        content_parts = []

        # Include installed_plugins.json
        if INSTALLED_PLUGINS_PATH.exists():
            try:
                content_parts.append(INSTALLED_PLUGINS_PATH.read_text())
            except Exception:
                pass

        # Include settings.json (specifically enabledPlugins section)
        if SETTINGS_PATH.exists():
            try:
                import json
                with open(SETTINGS_PATH) as f:
                    data = json.load(f)
                # Only hash the enabledPlugins part for efficiency
                enabled = data.get("enabledPlugins", {})
                content_parts.append(json.dumps(enabled, sort_keys=True))
            except Exception:
                pass

        if not content_parts:
            return None

        combined = "\n".join(content_parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    async def start(self) -> None:
        """Start the background watcher."""
        if self._running:
            return

        # Initial scan
        await self._scan_plugins()

        # Track initial state of Claude Code's plugin config
        self._claude_state_hash = self._compute_claude_state_hash()

        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("hot_reload_started", interval=self._check_interval)

    async def stop(self) -> None:
        """Stop the background watcher."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("hot_reload_stopped")

    async def _watch_loop(self) -> None:
        """Background loop that checks for changes."""
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                await self._check_for_changes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("hot_reload_error", error=str(e))

    async def _scan_plugins(self) -> None:
        """Initial scan of all plugins."""
        manifests = discover_plugins()
        for manifest in manifests:
            manifest_path = manifest.path / "manifest.json"
            if manifest_path.exists():
                self._tracker.update(manifest.name, manifest_path)
                self._manifests[manifest.name] = manifest

    async def _check_for_changes(self) -> None:
        """Check for manifest changes and reload if needed."""
        # Check if Claude Code plugin state changed (installed_plugins or settings)
        new_state_hash = self._compute_claude_state_hash()
        if new_state_hash != self._claude_state_hash:
            logger.info(
                "claude_plugin_state_changed",
                old_hash=self._claude_state_hash,
                new_hash=new_state_hash,
            )
            self._claude_state_hash = new_state_hash
            # Claude Code's state changed - this affects which plugins are enabled

        # Discover plugins (this now respects Claude Code's enabled state)
        current_manifests = {m.name: m for m in discover_plugins()}
        current_names = set(current_manifests.keys())
        tracked_names = self._tracker.get_tracked()

        # Detect new plugins (either newly added or newly enabled in Claude Code)
        new_plugins = current_names - tracked_names
        for name in new_plugins:
            manifest = current_manifests[name]
            logger.info("new_plugin_detected", name=name)
            await self._load_new_plugin(manifest)

        # Detect removed plugins (either deleted or disabled in Claude Code)
        removed_plugins = tracked_names - current_names
        for name in removed_plugins:
            logger.info("plugin_removed_detected", name=name)
            await self._unload_plugin(name)

        # Check for changes in existing plugins
        for name in current_names & tracked_names:
            manifest = current_manifests[name]
            manifest_path = manifest.path / "manifest.json"

            if self._tracker.update(name, manifest_path):
                logger.info("plugin_changed_detected", name=name)
                await self._reload_plugin(name, manifest)

    async def _load_new_plugin(self, manifest: PluginManifest) -> None:
        """Load a newly discovered plugin."""
        manifest_path = manifest.path / "manifest.json"
        self._tracker.update(manifest.name, manifest_path)
        self._manifests[manifest.name] = manifest

        # Sync deps if plugin has dependencies
        deps_result = None
        if manifest.dependencies:
            logger.info("syncing_deps_for_new_plugin", name=manifest.name)
            deps_result = sync_dependencies(self._config)

        # Load plugin
        try:
            bridge_context = self._get_bridge_context()
            plugin = load_plugin(manifest, bridge_context)

            cli_command = manifest.cli.get("command") if manifest.cli else None
            plugin_registry.register(plugin, cli_command=cli_command)

            # Mount routes
            self._mount_plugin_routes(manifest.name, plugin.router)

            # Start plugin
            await plugin_registry.startup(manifest.name)

            logger.info("new_plugin_loaded", name=manifest.name)

            # Emit event (notifier subscribes to this)
            bus = get_event_bus()
            installed = deps_result.installed if deps_result and deps_result.changed else []
            await bus.emit(
                "bridge",
                "plugin.loaded",
                {"name": manifest.name, "deps_installed": installed},
            )
        except Exception as e:
            logger.error("new_plugin_load_failed", name=manifest.name, error=str(e))

    async def _unload_plugin(self, name: str) -> None:
        """Unload a removed plugin."""
        # Shutdown plugin
        await plugin_registry.shutdown(name)

        # Unmount routes
        self._unmount_plugin_routes(name)

        # Unregister
        plugin_registry.unregister(name)

        # Clean up tracking
        self._tracker.remove(name)
        self._manifests.pop(name, None)

        # Sync deps to remove unused dependencies
        logger.info("syncing_deps_after_plugin_removal", name=name)
        result = sync_dependencies(self._config)

        logger.info("plugin_unloaded", name=name)

        # Emit event (notifier subscribes to this)
        bus = get_event_bus()
        await bus.emit(
            "bridge",
            "plugin.unloaded",
            {
                "name": name,
                "deps_removed": result.removed if result.changed else [],
            },
        )

    async def _reload_plugin(self, name: str, manifest: PluginManifest) -> None:
        """Reload a changed plugin."""
        old_manifest = self._manifests.get(name)
        deps_result = None

        # Check if deps changed
        if old_manifest and old_manifest.dependencies != manifest.dependencies:
            logger.info("deps_changed_resyncing", name=name)
            deps_result = sync_dependencies(self._config)

        # Shutdown old plugin
        await plugin_registry.shutdown(name)

        # Unmount old routes
        self._unmount_plugin_routes(name)

        # Unregister old plugin
        plugin_registry.unregister(name)

        # Clear module cache for plugin modules
        self._clear_plugin_modules(manifest)

        # Load fresh plugin
        try:
            bridge_context = self._get_bridge_context()
            plugin = load_plugin(manifest, bridge_context)

            cli_command = manifest.cli.get("command") if manifest.cli else None
            plugin_registry.register(plugin, cli_command=cli_command)

            # Mount new routes
            self._mount_plugin_routes(name, plugin.router)

            # Start new plugin
            await plugin_registry.startup(name)

            # Update manifest cache
            self._manifests[name] = manifest

            logger.info("plugin_reloaded", name=name)

            # Emit event (notifier subscribes to this)
            bus = get_event_bus()
            changed = deps_result and deps_result.changed
            await bus.emit(
                "bridge",
                "plugin.reloaded",
                {
                    "name": name,
                    "deps_installed": deps_result.installed if changed else [],
                    "deps_removed": deps_result.removed if changed else [],
                },
            )
        except Exception as e:
            logger.error("plugin_reload_failed", name=name, error=str(e))

    def _mount_plugin_routes(self, name: str, router: "APIRouter | None") -> None:
        """Mount plugin routes to the app."""
        if router is None:
            return

        prefix = f"/{name}"
        self._app.include_router(router, prefix=prefix)
        logger.debug("plugin_routes_mounted", name=name, prefix=prefix)

    def _unmount_plugin_routes(self, name: str) -> None:
        """Unmount plugin routes from the app."""
        prefix = f"/{name}"

        # Filter out routes with this prefix
        # FastAPI's routes is a property returning a list - modify in place
        routes_to_remove = [
            route for route in self._app.routes
            if hasattr(route, "path") and route.path.startswith(prefix)
        ]

        for route in routes_to_remove:
            self._app.routes.remove(route)

        if routes_to_remove:
            logger.debug("plugin_routes_unmounted", name=name, removed=len(routes_to_remove))

    def _clear_plugin_modules(self, manifest: PluginManifest) -> None:
        """Clear plugin modules from sys.modules to force reimport."""
        # Build module prefix pattern
        prefix = f"_bp_{manifest.name}"

        # Also clear the original module path
        entry_module = manifest.entry_point.split(":")[0]

        modules_to_clear = []
        for mod_name in list(sys.modules.keys()):
            is_prefixed = mod_name.startswith(prefix)
            is_entry = mod_name == entry_module or mod_name.startswith(f"{entry_module}.")
            if is_prefixed or is_entry:
                modules_to_clear.append(mod_name)

        for mod_name in modules_to_clear:
            del sys.modules[mod_name]

        if modules_to_clear:
            logger.debug(
                "cleared_modules", count=len(modules_to_clear), modules=modules_to_clear[:5]
            )

    def _get_bridge_context(self) -> dict[str, Any]:
        """Get bridge context for plugin instantiation."""
        from .connectors import connector_registry

        return {
            "config": self._config,
            "connector_registry": connector_registry,
            "event_bus": get_event_bus(),
        }

    async def reload_all(self) -> dict[str, bool]:
        """Force reload all plugins.

        Returns:
            Dict mapping plugin name to success status
        """
        results = {}
        manifests = discover_plugins()

        # Sync all deps first
        sync_dependencies(self._config, force=True)

        for manifest in manifests:
            try:
                await self._reload_plugin(manifest.name, manifest)
                results[manifest.name] = True
            except Exception as e:
                logger.error("reload_failed", name=manifest.name, error=str(e))
                results[manifest.name] = False

        return results

    async def reload_plugin(self, name: str) -> bool:
        """Force reload a specific plugin.

        Args:
            name: Plugin name to reload

        Returns:
            True if reload succeeded
        """
        manifest = self._manifests.get(name)
        if not manifest:
            # Try to discover it
            for m in discover_plugins():
                if m.name == name:
                    manifest = m
                    break

        if not manifest:
            logger.error("plugin_not_found", name=name)
            return False

        try:
            await self._reload_plugin(name, manifest)
            return True
        except Exception as e:
            logger.error("reload_failed", name=name, error=str(e))
            return False


# Global instance (set during app creation)
_hot_reloader: HotReloader | None = None


def init_hot_reloader(
    app: "FastAPI", config: "BridgeConfig", check_interval: float = 5.0
) -> HotReloader:
    """Initialize the global hot reloader."""
    global _hot_reloader
    _hot_reloader = HotReloader(app, config, check_interval)
    return _hot_reloader


def get_hot_reloader() -> HotReloader | None:
    """Get the global hot reloader instance."""
    return _hot_reloader
