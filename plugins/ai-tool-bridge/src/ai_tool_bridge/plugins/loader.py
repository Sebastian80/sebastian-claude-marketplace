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


def _load_module_isolated(manifest: "PluginManifest", module_path: str) -> Any:
    """Load a module using isolated namespace to avoid sys.path collisions.

    Uses a unique module prefix per plugin while preserving relative imports.

    Args:
        manifest: Plugin manifest with path info
        module_path: Dotted module path (e.g., "scripts" or "scripts.plugin")

    Returns:
        Loaded module object

    Raises:
        PluginLoadError: If module cannot be loaded
    """
    # Create unique prefix for this plugin's modules
    prefix = f"_bp_{manifest.name}"

    # Add the plugin directory to sys.path for imports
    plugin_root = str(manifest.path)
    if plugin_root not in sys.path:
        sys.path.insert(0, plugin_root)
        logger.debug("added_to_path", path=plugin_root, reason="isolated load")

    # Also add the module's directory for sibling imports (e.g., serena_cli in scripts/)
    parts = module_path.split(".")
    module_dir = str(manifest.path / Path(*parts))
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        logger.debug("added_to_path", path=module_dir, reason="module directory")

    # Convert module path to use our unique prefix
    # e.g., "scripts" -> "_bp_serena.scripts"
    unique_module = f"{prefix}.{module_path}"

    # We need to create the parent namespace package first
    if prefix not in sys.modules:
        # Create empty namespace package for the prefix
        import types
        ns_pkg = types.ModuleType(prefix)
        ns_pkg.__path__ = [plugin_root]
        ns_pkg.__package__ = prefix
        sys.modules[prefix] = ns_pkg

    try:
        # Load the actual module using standard import
        # This handles relative imports correctly
        parts = module_path.split(".")
        rel_path = Path(*parts)

        init_path = manifest.path / rel_path / "__init__.py"
        module_file = manifest.path / f"{rel_path}.py"

        if init_path.exists():
            file_path = init_path
            is_package = True
        elif module_file.exists():
            file_path = module_file
            is_package = False
        else:
            raise PluginLoadError(
                f"Cannot find module '{module_path}' in {manifest.path}. "
                f"Tried: {init_path}, {module_file}"
            )

        # Load with spec that preserves package semantics
        spec = importlib.util.spec_from_file_location(
            unique_module,
            file_path,
            submodule_search_locations=[str(manifest.path / rel_path)] if is_package else None
        )

        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Failed to create module spec for {file_path}")

        module = importlib.util.module_from_spec(spec)

        # Critical: set __package__ for relative imports to work
        if is_package:
            module.__package__ = unique_module
            module.__path__ = [str(manifest.path / rel_path)]
        else:
            module.__package__ = f"{prefix}.{'.'.join(parts[:-1])}" if len(parts) > 1 else prefix

        # Register module before exec so submodule imports can find it
        sys.modules[unique_module] = module

        # Also register under original name for relative imports within the package
        sys.modules[module_path] = module

        spec.loader.exec_module(module)

        logger.debug(
            "module_loaded_isolated",
            name=unique_module,
            path=str(file_path),
        )

        return module

    except PluginLoadError:
        raise
    except Exception as e:
        raise PluginLoadError(f"Failed to load module {module_path}: {e}") from e


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

        # Use isolated spec-based loading to avoid sys.path collisions
        # This creates a unique module namespace per plugin
        module = _load_module_isolated(manifest, module_path)

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
