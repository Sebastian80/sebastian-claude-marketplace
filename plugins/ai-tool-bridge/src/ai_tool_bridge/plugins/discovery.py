"""
Plugin Discovery - Find plugins in standard locations.

Scans plugin directories for valid plugin packages.
A valid plugin has a manifest.json with required fields.

Integrates with Claude Code's installed_plugins.json to respect
enabled/disabled state from /plugin command.
"""

import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Standard plugin locations
DEFAULT_PLUGIN_PATHS = [
    Path.home() / ".claude" / "plugins" / "marketplaces",
    Path.home() / ".claude" / "plugins" / "local",
]

# Claude Code's plugin registry files
INSTALLED_PLUGINS_PATH = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


def get_installed_plugins() -> set[str]:
    """Read Claude Code's plugin state and return enabled plugin identifiers.

    Uses settings.json -> enabledPlugins as the authoritative source.
    A plugin is only considered enabled if:
    - It exists in enabledPlugins AND its value is True, OR
    - It exists in installed_plugins.json AND is not explicitly disabled in enabledPlugins

    Returns:
        Set of enabled plugin identifiers in format "name@marketplace"
    """
    installed = set()
    enabled_state = {}  # plugin_id -> True/False

    # Get list of installed plugins
    if INSTALLED_PLUGINS_PATH.exists():
        try:
            with open(INSTALLED_PLUGINS_PATH) as f:
                data = json.load(f)
            installed.update(data.get("plugins", {}).keys())
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("installed_plugins_parse_error", error=str(e))

    # Get enabled state from settings.json (authoritative for enable/disable)
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH) as f:
                data = json.load(f)
            enabled_state = data.get("enabledPlugins", {})
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("settings_parse_error", error=str(e))

    # Build final set: plugin is enabled if:
    # - Explicitly enabled in settings.json (enabledPlugins[id] = true)
    # - OR installed but not mentioned in enabledPlugins (default to enabled)
    # A plugin is disabled if enabledPlugins[id] = false
    result = set()

    # Add plugins explicitly enabled in settings
    for plugin_id, is_enabled in enabled_state.items():
        if is_enabled:
            result.add(plugin_id)

    # Add installed plugins not explicitly disabled
    for plugin_id in installed:
        if plugin_id not in enabled_state:
            # Not mentioned in enabledPlugins, default to enabled
            result.add(plugin_id)
        # If it's in enabled_state, we already handled it above

    logger.debug("installed_plugins_loaded", count=len(result), plugins=list(result))
    return result


def extract_marketplace_from_path(manifest_path: Path) -> str | None:
    """Extract marketplace name from manifest path.

    Example:
        Path: ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jira/skills/jira/manifest.json
        Returns: "sebastian-marketplace"

        Path: ~/.claude/plugins/local/my-plugin/manifest.json
        Returns: "local"
    """
    parts = manifest_path.parts

    # Look for "marketplaces" in path
    if "marketplaces" in parts:
        idx = parts.index("marketplaces")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    # Local plugins
    if "local" in parts:
        return "local"

    return None


def is_plugin_enabled(plugin_name: str, manifest_path: Path, installed_plugins: set[str]) -> bool:
    """Check if a plugin is enabled in Claude Code.

    Args:
        plugin_name: Name from manifest
        manifest_path: Path to manifest.json
        installed_plugins: Set of enabled plugin identifiers

    Returns:
        True if plugin is enabled or if we can't determine (fail-open)
    """
    # If no installed_plugins.json, fail-open (allow all)
    if not installed_plugins:
        return True

    marketplace = extract_marketplace_from_path(manifest_path)
    if not marketplace:
        # Can't determine marketplace, fail-open
        return True

    # Build the identifier Claude Code uses
    plugin_id = f"{plugin_name}@{marketplace}"

    # Direct match
    if plugin_id in installed_plugins:
        return True

    # Check if it's a skill within an installed plugin
    # Path pattern: .../marketplaces/MARKETPLACE/plugins/PARENT/skills/SKILL/manifest.json
    # We need to find the parent plugin name which comes after "plugins" but before "skills"
    path_str = str(manifest_path)
    if "/skills/" in path_str:
        # Extract parent plugin from path
        # Example: .../plugins/jira/skills/jira/manifest.json -> parent is "jira"
        # Example: .../plugins/serena-integration/skills/serena/manifest.json -> parent is "serena-integration"
        parts = path_str.split("/")
        try:
            skills_idx = parts.index("skills")
            # The parent plugin is the directory before "skills"
            # But we need to find the right "plugins" - the one in the marketplace structure
            # Look backwards from skills_idx to find "plugins"
            for i in range(skills_idx - 1, -1, -1):
                if parts[i] == "plugins" and i + 1 < skills_idx:
                    parent_plugin = parts[i + 1]
                    parent_id = f"{parent_plugin}@{marketplace}"
                    if parent_id in installed_plugins:
                        logger.debug(
                            "plugin_enabled_via_parent",
                            name=plugin_name,
                            parent=parent_plugin,
                        )
                        return True
                    break
        except (ValueError, IndexError):
            pass

    return False


class PluginManifest:
    """Parsed plugin manifest.

    Required fields:
        name: Plugin identifier
        version: Semantic version string
        entry_point: Python module path to plugin class

    Optional fields:
        description: Human-readable description
        dependencies: List of pip package requirements
        bridge_api: Minimum bridge API version required
        cli: CLI wrapper configuration {"command": str, "script": str}
    """

    def __init__(self, data: dict[str, Any], manifest_path: Path) -> None:
        self.path = manifest_path.parent
        self.name = data["name"]
        self.version = data["version"]
        self.entry_point = data["entry_point"]
        self.description = data.get("description", "")
        self.dependencies = data.get("dependencies", [])
        self.bridge_api = data.get("bridge_api", "1.0.0")
        self.cli = data.get("cli")  # {"command": "jira", "script": "../cli/jira"}

    @classmethod
    def from_file(cls, manifest_path: Path) -> "PluginManifest":
        """Load manifest from file.

        Raises:
            FileNotFoundError: If manifest doesn't exist
            json.JSONDecodeError: If manifest is invalid JSON
            KeyError: If required fields are missing
        """
        with open(manifest_path) as f:
            data = json.load(f)

        # Validate required fields
        required = ["name", "version", "entry_point"]
        missing = [f for f in required if f not in data]
        if missing:
            raise KeyError(f"Missing required fields: {missing}")

        return cls(data, manifest_path)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "version": self.version,
            "entry_point": self.entry_point,
            "description": self.description,
            "dependencies": self.dependencies,
            "bridge_api": self.bridge_api,
            "path": str(self.path),
        }
        if self.cli:
            result["cli"] = self.cli
        return result


def discover_plugins(
    paths: list[Path] | None = None,
    recursive: bool = True,
    respect_claude_state: bool = True,
) -> list[PluginManifest]:
    """Discover all plugins in given paths.

    Args:
        paths: Directories to scan (defaults to DEFAULT_PLUGIN_PATHS)
        recursive: Whether to scan subdirectories
        respect_claude_state: If True, filter by Claude Code's installed_plugins.json

    Returns:
        List of discovered plugin manifests
    """
    if paths is None:
        paths = DEFAULT_PLUGIN_PATHS

    # Load Claude Code's installed plugins if we're respecting state
    installed_plugins = get_installed_plugins() if respect_claude_state else set()

    manifests = []
    skipped = []

    for base_path in paths:
        if not base_path.exists():
            logger.debug("plugin_path_not_found", path=str(base_path))
            continue

        # Find all manifest.json files
        pattern = "**/manifest.json" if recursive else "*/manifest.json"
        for manifest_path in base_path.glob(pattern):
            try:
                manifest = PluginManifest.from_file(manifest_path)

                # Check if plugin is enabled in Claude Code
                if respect_claude_state and installed_plugins:
                    if not is_plugin_enabled(manifest.name, manifest_path, installed_plugins):
                        skipped.append(manifest.name)
                        logger.debug(
                            "plugin_disabled_in_claude",
                            name=manifest.name,
                            path=str(manifest.path),
                        )
                        continue

                manifests.append(manifest)
                logger.debug(
                    "plugin_discovered",
                    name=manifest.name,
                    version=manifest.version,
                    path=str(manifest.path),
                )
            except json.JSONDecodeError as e:
                logger.warning(
                    "invalid_manifest_json",
                    path=str(manifest_path),
                    error=str(e),
                )
            except KeyError as e:
                logger.warning(
                    "incomplete_manifest",
                    path=str(manifest_path),
                    error=str(e),
                )
            except Exception as e:
                logger.warning(
                    "manifest_load_error",
                    path=str(manifest_path),
                    error=str(e),
                )

    if skipped:
        logger.info("plugins_skipped_disabled", count=len(skipped), plugins=skipped)

    logger.info("plugin_discovery_complete", count=len(manifests))
    return manifests


def find_plugin(name: str, paths: list[Path] | None = None) -> PluginManifest | None:
    """Find a specific plugin by name.

    Args:
        name: Plugin name to find
        paths: Directories to search

    Returns:
        Plugin manifest or None if not found
    """
    for manifest in discover_plugins(paths):
        if manifest.name == name:
            return manifest
    return None
