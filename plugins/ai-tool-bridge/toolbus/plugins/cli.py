"""
CLI Management - Install/uninstall plugin CLI wrappers.

Plugins can declare CLI commands in their manifest:
    "cli": {
        "command": "jira",
        "script": "../cli/jira"
    }

The script is symlinked to ~/.local/bin/<command> during plugin load.
Symlinks are preferred over copies so changes are reflected immediately.
"""

import os
from pathlib import Path

import structlog

from .discovery import PluginManifest

__all__ = ["install_cli", "is_cli_installed", "uninstall_cli"]

logger = structlog.get_logger(__name__)

# User binary directory (no sudo needed)
USER_BIN_DIR = Path.home() / ".local" / "bin"


def install_cli(manifest: PluginManifest) -> bool:
    """Install CLI wrapper for a plugin.

    Args:
        manifest: Plugin manifest with cli configuration

    Returns:
        True if installed, False if no CLI or failed
    """
    if not manifest.cli:
        return False

    command = manifest.cli.get("command")
    script = manifest.cli.get("script")

    if not command or not script:
        logger.warning(
            "invalid_cli_config",
            plugin=manifest.name,
            cli=manifest.cli,
        )
        return False

    # Resolve script path relative to manifest directory
    source = (manifest.path / script).resolve()

    if not source.exists():
        logger.warning(
            "cli_script_not_found",
            plugin=manifest.name,
            script=str(source),
        )
        return False

    # Ensure ~/.local/bin exists
    USER_BIN_DIR.mkdir(parents=True, exist_ok=True)

    target = USER_BIN_DIR / command

    try:
        # Remove existing (symlink or file) if present
        if target.exists() or target.is_symlink():
            target.unlink()

        # Create symlink to source script
        os.symlink(source, target)

        logger.info(
            "cli_installed",
            plugin=manifest.name,
            command=command,
            target=str(target),
            source=str(source),
        )
        return True

    except Exception as e:
        logger.error(
            "cli_install_failed",
            plugin=manifest.name,
            command=command,
            error=str(e),
        )
        return False


def uninstall_cli(manifest: PluginManifest) -> bool:
    """Uninstall CLI wrapper for a plugin.

    Args:
        manifest: Plugin manifest with cli configuration

    Returns:
        True if uninstalled, False if no CLI or failed
    """
    if not manifest.cli:
        return False

    command = manifest.cli.get("command")
    if not command:
        return False

    target = USER_BIN_DIR / command

    if not target.exists() and not target.is_symlink():
        logger.debug(
            "cli_not_installed",
            plugin=manifest.name,
            command=command,
        )
        return False

    try:
        target.unlink(missing_ok=True)
        logger.info(
            "cli_uninstalled",
            plugin=manifest.name,
            command=command,
        )
        return True

    except Exception as e:
        logger.error(
            "cli_uninstall_failed",
            plugin=manifest.name,
            command=command,
            error=str(e),
        )
        return False


def is_cli_installed(manifest: PluginManifest) -> bool:
    """Check if CLI wrapper is installed for a plugin.

    Args:
        manifest: Plugin manifest with cli configuration

    Returns:
        True if CLI is installed
    """
    if not manifest.cli:
        return False

    command = manifest.cli.get("command")
    if not command:
        return False

    return (USER_BIN_DIR / command).exists()
