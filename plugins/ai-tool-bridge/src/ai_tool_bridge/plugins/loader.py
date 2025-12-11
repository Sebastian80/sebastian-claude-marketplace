"""
Plugin Loader - Load and instantiate plugins.

Handles:
- Importing plugin modules
- Instantiating plugin classes
- Dependency injection of bridge services
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import structlog

from ..contracts import PluginProtocol
from .discovery import PluginManifest

logger = structlog.get_logger(__name__)


class PluginLoadError(Exception):
    """Raised when plugin loading fails."""

    pass


def load_plugin(
    manifest: PluginManifest,
    bridge_context: dict[str, Any] | None = None,
) -> PluginProtocol:
    """Load a plugin from its manifest.

    Args:
        manifest: Plugin manifest with entry point info
        bridge_context: Optional context to inject into plugin

    Returns:
        Instantiated plugin

    Raises:
        PluginLoadError: If loading fails
    """
    try:
        # Parse entry point: "module.path:ClassName"
        if ":" not in manifest.entry_point:
            raise PluginLoadError(
                f"Invalid entry_point format: {manifest.entry_point}. "
                "Expected 'module.path:ClassName'"
            )

        module_path, class_name = manifest.entry_point.split(":", 1)

        # Add plugin paths to sys.path for import resolution
        # The entry_point module name tells us what to look for
        base_module = module_path.split(".")[0]  # e.g., "skills_plugin"

        # Check if manifest.path IS the module (package directory)
        if manifest.path.name == base_module and (manifest.path / "__init__.py").exists():
            # Add parent directory so 'import skills_plugin' works
            parent_str = str(manifest.path.parent)
            if parent_str not in sys.path:
                sys.path.insert(0, parent_str)
                logger.debug("added_to_path", path=parent_str, reason="parent of package")

        # Also add src/ if it exists (standard layout)
        plugin_src = manifest.path / "src"
        if plugin_src.exists():
            src_str = str(plugin_src)
            if src_str not in sys.path:
                sys.path.insert(0, src_str)
                logger.debug("added_to_path", path=src_str, reason="src directory")

        # Also add the plugin root as fallback
        plugin_root = str(manifest.path)
        if plugin_root not in sys.path:
            sys.path.insert(0, plugin_root)
            logger.debug("added_to_path", path=plugin_root, reason="plugin root")

        # Import the module
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise PluginLoadError(f"Failed to import {module_path}: {e}") from e

        # Get the class
        if not hasattr(module, class_name):
            raise PluginLoadError(
                f"Module {module_path} has no class {class_name}"
            )

        plugin_class = getattr(module, class_name)

        # Instantiate - try with context first, then without
        try:
            if bridge_context:
                plugin = plugin_class(bridge_context)
            else:
                plugin = plugin_class()
        except TypeError:
            # Plugin doesn't accept context argument
            plugin = plugin_class()

        # Verify it implements the protocol
        _verify_protocol(plugin, manifest.name)

        logger.info(
            "plugin_loaded",
            name=manifest.name,
            version=manifest.version,
            class_name=class_name,
        )

        return plugin

    except PluginLoadError:
        raise
    except Exception as e:
        raise PluginLoadError(f"Failed to load plugin {manifest.name}: {e}") from e


def load_plugin_from_path(
    path: Path,
    bridge_context: dict[str, Any] | None = None,
) -> PluginProtocol:
    """Load a plugin from a directory path.

    Convenience function that discovers manifest and loads plugin.

    Args:
        path: Plugin directory containing manifest.json
        bridge_context: Optional context to inject

    Returns:
        Instantiated plugin

    Raises:
        PluginLoadError: If loading fails
    """
    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        raise PluginLoadError(f"No manifest.json found in {path}")

    manifest = PluginManifest.from_file(manifest_path)
    return load_plugin(manifest, bridge_context)


def _verify_protocol(plugin: Any, name: str) -> None:
    """Verify plugin implements required protocol methods.

    Args:
        plugin: Plugin instance to verify
        name: Plugin name for error messages

    Raises:
        PluginLoadError: If protocol not implemented
    """
    required_attrs = ["name", "version", "description", "router"]
    required_methods = ["startup", "shutdown", "health_check"]

    missing_attrs = [attr for attr in required_attrs if not hasattr(plugin, attr)]
    missing_methods = [
        method for method in required_methods
        if not hasattr(plugin, method) or not callable(getattr(plugin, method))
    ]

    if missing_attrs or missing_methods:
        errors = []
        if missing_attrs:
            errors.append(f"missing attributes: {missing_attrs}")
        if missing_methods:
            errors.append(f"missing methods: {missing_methods}")
        raise PluginLoadError(
            f"Plugin {name} doesn't implement PluginProtocol: {'; '.join(errors)}"
        )
