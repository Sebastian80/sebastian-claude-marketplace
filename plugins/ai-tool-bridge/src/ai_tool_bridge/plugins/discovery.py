"""
Plugin Discovery - Find plugins in standard locations.

Scans plugin directories for valid plugin packages.
A valid plugin has a manifest.json with required fields.
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
) -> list[PluginManifest]:
    """Discover all plugins in given paths.

    Args:
        paths: Directories to scan (defaults to DEFAULT_PLUGIN_PATHS)
        recursive: Whether to scan subdirectories

    Returns:
        List of discovered plugin manifests
    """
    if paths is None:
        paths = DEFAULT_PLUGIN_PATHS

    manifests = []

    for base_path in paths:
        if not base_path.exists():
            logger.debug("plugin_path_not_found", path=str(base_path))
            continue

        # Find all manifest.json files
        pattern = "**/manifest.json" if recursive else "*/manifest.json"
        for manifest_path in base_path.glob(pattern):
            try:
                manifest = PluginManifest.from_file(manifest_path)
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
