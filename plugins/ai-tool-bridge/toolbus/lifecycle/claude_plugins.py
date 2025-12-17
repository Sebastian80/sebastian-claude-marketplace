"""
Claude Code Plugin Monitor - Watch for plugin installs/enables/disables.

Monitors Claude Code's plugin system and emits events when:
- Plugins are enabled/disabled (settings.json changes)
- New plugins are installed (cache directory changes)

Also manages dependencies:
- Installs plugin deps to bridge venv on enable
- Tracks deps per plugin for cleanup on disable
"""

import asyncio
import hashlib
import json
from pathlib import Path

import structlog

from ..config import BridgeConfig
from ..deps import normalize_dep_name, run_uv_install, run_uv_uninstall
from ..events import get_event_bus

__all__ = ["ClaudePluginMonitor", "find_plugin_deps", "get_latest_plugin_version"]

logger = structlog.get_logger(__name__)

# Claude Code paths
CLAUDE_DIR = Path.home() / ".claude"
SETTINGS_PATH = CLAUDE_DIR / "settings.json"
CACHE_DIR = CLAUDE_DIR / "plugins" / "cache"


def find_plugin_deps(plugin_path: Path) -> list[str]:
    """Find dependencies declared in manifest.json files.

    Args:
        plugin_path: Path to plugin version directory

    Returns:
        List of dependency specs
    """
    deps: list[str] = []

    if not plugin_path.exists():
        return deps

    # Search for manifest.json with dependencies
    for manifest_file in plugin_path.rglob("manifest.json"):
        try:
            content = json.loads(manifest_file.read_text())
            if "dependencies" in content and isinstance(content["dependencies"], list):
                manifest_deps = content["dependencies"]
                deps.extend(manifest_deps)
                logger.debug(
                    "deps_from_manifest", path=str(manifest_file), count=len(manifest_deps)
                )
        except Exception as e:
            logger.warning("manifest_parse_failed", path=str(manifest_file), error=str(e))

    # Deduplicate
    return list(set(deps))


def get_latest_plugin_version(marketplace: str, plugin: str) -> Path | None:
    """Get path to latest version of a plugin."""
    plugin_dir = CACHE_DIR / marketplace / plugin
    if not plugin_dir.exists():
        return None

    versions = [d for d in plugin_dir.iterdir() if d.is_dir()]
    if not versions:
        return None

    # Sort by version (simple string sort works for semver)
    versions.sort(key=lambda p: p.name, reverse=True)
    return versions[0]


class ClaudePluginMonitor:
    """Monitors Claude Code plugin system for changes.

    Watches:
    - ~/.claude/settings.json for enabledPlugins changes
    - ~/.claude/plugins/cache/ for new plugin installs

    Emits events:
    - claude.plugin.enabled: {name, marketplace, deps_installed}
    - claude.plugin.disabled: {name, marketplace, deps_removed}
    - claude.plugin.installed: {name, marketplace, version}
    """

    __slots__ = (
        "_check_interval",
        "_running",
        "_task",
        "_settings_hash",
        "_enabled_plugins",
        "_cached_plugins",
        "_config",
        "_logger",
    )

    def __init__(self, check_interval: float = 2.0, config: BridgeConfig | None = None) -> None:
        self._check_interval = check_interval
        self._running = False
        self._task: asyncio.Task | None = None
        self._settings_hash: str = ""
        self._enabled_plugins: dict[str, bool] = {}
        self._cached_plugins: set[str] = set()
        self._config = config or BridgeConfig()
        self._logger = logger.bind(component="claude_plugin_monitor")

    def _get_plugin_deps_file(self, plugin_key: str) -> Path:
        """Get path to store deps for a plugin."""
        safe_key = plugin_key.replace("@", "_at_").replace("/", "_")
        return self._config.state_dir / "claude_plugin_deps" / f"{safe_key}.deps"

    def _load_plugin_deps(self, plugin_key: str) -> set[str]:
        """Load stored deps for a plugin."""
        deps_file = self._get_plugin_deps_file(plugin_key)
        if deps_file.exists():
            return set(d for d in deps_file.read_text().strip().split("\n") if d)
        return set()

    def _save_plugin_deps(self, plugin_key: str, deps: list[str]) -> None:
        """Save deps for a plugin."""
        deps_file = self._get_plugin_deps_file(plugin_key)
        deps_file.parent.mkdir(parents=True, exist_ok=True)
        deps_file.write_text("\n".join(sorted(deps)))

    def _remove_plugin_deps_file(self, plugin_key: str) -> None:
        """Remove deps file for a plugin."""
        deps_file = self._get_plugin_deps_file(plugin_key)
        if deps_file.exists():
            deps_file.unlink()

    def _get_all_tracked_deps(self) -> set[str]:
        """Get all deps tracked across all plugins."""
        all_deps: set[str] = set()
        deps_dir = self._config.state_dir / "claude_plugin_deps"
        if deps_dir.exists():
            for deps_file in deps_dir.glob("*.deps"):
                try:
                    deps = deps_file.read_text().strip().split("\n")
                    all_deps.update(d for d in deps if d)
                except Exception:
                    pass
        return all_deps

    async def _install_plugin_deps(self, plugin: str, marketplace: str) -> list[str]:
        """Install dependencies for a Claude Code plugin."""
        plugin_key = f"{plugin}@{marketplace}"

        plugin_path = get_latest_plugin_version(marketplace, plugin)
        if not plugin_path:
            return []

        deps = find_plugin_deps(plugin_path)
        if not deps:
            return []

        self._logger.info("installing_claude_plugin_deps", plugin=plugin_key, deps=deps)

        if run_uv_install(self._config, deps):
            self._save_plugin_deps(plugin_key, deps)
            return deps

        return []

    async def _uninstall_plugin_deps(self, plugin: str, marketplace: str) -> list[str]:
        """Uninstall dependencies for a disabled plugin (if not shared)."""
        plugin_key = f"{plugin}@{marketplace}"

        plugin_deps = self._load_plugin_deps(plugin_key)
        if not plugin_deps:
            return []

        # Remove deps file first
        self._remove_plugin_deps_file(plugin_key)

        # Get deps still needed by other plugins
        still_needed = self._get_all_tracked_deps()

        # Find deps to remove (not needed by others)
        to_remove = [normalize_dep_name(d) for d in plugin_deps if d not in still_needed]

        if not to_remove:
            return []

        self._logger.info("uninstalling_claude_plugin_deps", plugin=plugin_key, deps=to_remove)

        if run_uv_uninstall(self._config, to_remove):
            return to_remove

        return []

    async def start(self) -> None:
        """Start monitoring."""
        if self._running:
            return

        self._running = True
        (self._config.state_dir / "claude_plugin_deps").mkdir(parents=True, exist_ok=True)
        self._load_initial_state()
        self._task = asyncio.create_task(self._monitor_loop())

        self._logger.info(
            "claude_plugin_monitor_started",
            check_interval=self._check_interval,
            plugins_tracked=len(self._enabled_plugins),
        )

    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._logger.info("claude_plugin_monitor_stopped")

    def _load_initial_state(self) -> None:
        """Load initial state from settings and cache."""
        if SETTINGS_PATH.exists():
            try:
                content = SETTINGS_PATH.read_text()
                self._settings_hash = self._hash(content)
                settings = json.loads(content)
                self._enabled_plugins = settings.get("enabledPlugins", {})
            except Exception as e:
                self._logger.warning("settings_load_failed", error=str(e))

        self._cached_plugins = self._scan_cache()

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _scan_cache(self) -> set[str]:
        """Scan cache directory for installed plugins."""
        plugins: set[str] = set()

        if not CACHE_DIR.exists():
            return plugins

        for marketplace_dir in CACHE_DIR.iterdir():
            if not marketplace_dir.is_dir():
                continue
            marketplace = marketplace_dir.name

            # Skip temp dirs and hidden dirs
            if marketplace.startswith("temp_") or marketplace.startswith("."):
                continue

            for plugin_dir in marketplace_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue
                plugin = plugin_dir.name

                # Skip hidden dirs
                if plugin.startswith("."):
                    continue

                for version_dir in plugin_dir.iterdir():
                    if not version_dir.is_dir():
                        continue
                    version = version_dir.name

                    # Skip hidden dirs
                    if version.startswith("."):
                        continue

                    plugins.add(f"{marketplace}/{plugin}/{version}")

        return plugins

    def _parse_plugin_key(self, key: str) -> tuple[str, str]:
        """Parse 'plugin@marketplace' into (plugin, marketplace)."""
        if "@" in key:
            parts = key.split("@", 1)
            return parts[0], parts[1]
        return key, "unknown"

    async def _check_settings(self) -> None:
        """Check settings.json for enabledPlugins changes."""
        if not SETTINGS_PATH.exists():
            return

        try:
            content = SETTINGS_PATH.read_text()
            new_hash = self._hash(content)

            if new_hash == self._settings_hash:
                return

            self._settings_hash = new_hash
            settings = json.loads(content)
            new_enabled = settings.get("enabledPlugins", {})

            bus = get_event_bus()
            all_keys = set(self._enabled_plugins.keys()) | set(new_enabled.keys())

            for key in all_keys:
                old_val = self._enabled_plugins.get(key, False)
                new_val = new_enabled.get(key, False)

                if old_val != new_val:
                    plugin, marketplace = self._parse_plugin_key(key)

                    if new_val:
                        installed_deps = await self._install_plugin_deps(plugin, marketplace)
                        self._logger.info(
                            "claude_plugin_enabled",
                            plugin=plugin,
                            marketplace=marketplace,
                            deps_installed=len(installed_deps),
                        )
                        await bus.emit(
                            "claude",
                            "plugin.enabled",
                            {
                                "name": plugin,
                                "marketplace": marketplace,
                                "deps_installed": installed_deps,
                            },
                        )
                    else:
                        removed_deps = await self._uninstall_plugin_deps(plugin, marketplace)
                        self._logger.info(
                            "claude_plugin_disabled",
                            plugin=plugin,
                            marketplace=marketplace,
                            deps_removed=len(removed_deps),
                        )
                        await bus.emit(
                            "claude",
                            "plugin.disabled",
                            {
                                "name": plugin,
                                "marketplace": marketplace,
                                "deps_removed": removed_deps,
                            },
                        )

            self._enabled_plugins = new_enabled

        except Exception as e:
            self._logger.warning("settings_check_failed", error=str(e))

    async def _check_cache(self) -> None:
        """Check cache directory for plugin installs/uninstalls."""
        new_cached = self._scan_cache()
        bus = get_event_bus()

        # New installs
        new_installs = new_cached - self._cached_plugins
        for path in new_installs:
            parts = path.split("/")
            if len(parts) == 3:
                marketplace, plugin, version = parts
                self._logger.info(
                    "claude_plugin_installed",
                    plugin=plugin,
                    marketplace=marketplace,
                    version=version,
                )
                await bus.emit(
                    "claude",
                    "plugin.installed",
                    {"name": plugin, "marketplace": marketplace, "version": version},
                )

        # Uninstalls (removed from cache)
        removed = self._cached_plugins - new_cached
        for path in removed:
            parts = path.split("/")
            if len(parts) == 3:
                marketplace, plugin, version = parts
                self._logger.info(
                    "claude_plugin_uninstalled",
                    plugin=plugin,
                    marketplace=marketplace,
                    version=version,
                )
                await bus.emit(
                    "claude",
                    "plugin.uninstalled",
                    {"name": plugin, "marketplace": marketplace, "version": version},
                )

        self._cached_plugins = new_cached

    async def _monitor_loop(self) -> None:
        """Background loop checking for changes."""
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                if not self._running:
                    break
                await self._check_settings()
                await self._check_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error("monitor_error", error=str(e))

    def status(self) -> dict:
        """Get monitor status."""
        return {
            "running": self._running,
            "plugins_tracked": len(self._enabled_plugins),
            "cached_versions": len(self._cached_plugins),
            "check_interval": self._check_interval,
        }
