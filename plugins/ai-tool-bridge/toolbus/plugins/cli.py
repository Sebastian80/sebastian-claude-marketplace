"""
CLI Management - Install/uninstall plugin CLI wrappers.

Plugins can declare CLI commands in their manifest:
    "cli": {
        "command": "jira",
        "script": "../cli/jira"
    }

The script is installed to ~/.local/bin/<command> during plugin load.
"""

import shutil
import stat
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
        # Copy script to target
        shutil.copy2(source, target)

        # Make executable (rwxr-xr-x)
        target.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        logger.info(
            "cli_installed",
            plugin=manifest.name,
            command=command,
            target=str(target),
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

    if not target.exists():
        logger.debug(
            "cli_not_installed",
            plugin=manifest.name,
            command=command,
        )
        return False

    try:
        target.unlink()
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
