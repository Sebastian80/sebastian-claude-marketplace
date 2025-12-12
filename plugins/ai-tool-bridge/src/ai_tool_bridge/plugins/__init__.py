"""
Plugins - Plugin discovery, loading, and lifecycle management.

The plugin system supports:
- Auto-discovery from standard locations (~/.claude/plugins)
- Manifest-based configuration (manifest.json)
- Lifecycle management (startup, shutdown, health)
- Route mounting for FastAPI integration

Example:
    from ai_tool_bridge.plugins import (
        discover_plugins,
        load_plugin,
        plugin_registry,
    )

    # Discover all available plugins
    manifests = discover_plugins()

    # Load and register each plugin
    for manifest in manifests:
        plugin = load_plugin(manifest)
        plugin_registry.register(plugin)

    # Start all plugins
    await plugin_registry.startup_all()
"""

from .cli import install_cli, is_cli_installed, uninstall_cli
from .discovery import (
    DEFAULT_PLUGIN_PATHS,
    PluginManifest,
    discover_plugins,
    find_plugin,
)
from .loader import PluginLoadError, load_plugin, load_plugin_from_path
from .registry import PluginRegistry, plugin_registry

__all__ = [
    # CLI
    "install_cli",
    "uninstall_cli",
    "is_cli_installed",
    # Discovery
    "DEFAULT_PLUGIN_PATHS",
    "PluginManifest",
    "discover_plugins",
    "find_plugin",
    # Loader
    "PluginLoadError",
    "load_plugin",
    "load_plugin_from_path",
    # Registry
    "PluginRegistry",
    "plugin_registry",
]
