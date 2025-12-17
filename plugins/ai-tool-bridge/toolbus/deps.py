"""
Dependency Management - UV-based automatic dependency sync.

Uses UV pip commands:
1. Aggregate deps from all plugin manifests
2. Install new deps with `uv pip install`
3. Uninstall removed deps with `uv pip uninstall`

This ensures:
- New plugin deps are installed
- Removed plugin deps are uninstalled
- Bridge package itself is never affected
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import structlog

from .config import BridgeConfig
from .plugins.discovery import discover_plugins

__all__ = [
    "SyncResult",
    "aggregate_dependencies",
    "normalize_dep_name",
    "run_uv_install",
    "run_uv_uninstall",
    "show_deps_status",
    "sync_dependencies",
]

logger = structlog.get_logger(__name__)

# Core bridge dependencies (always required)
BRIDGE_CORE_DEPS = [
    "fastapi>=0.109",
    "uvicorn>=0.27",
    "httpx>=0.25",
    "structlog>=24.0",
]


def compute_deps_hash(deps: list[str]) -> str:
    """Compute deterministic hash of dependencies."""
    normalized = sorted(set(d.strip().lower() for d in deps if d.strip()))
    content = "\n".join(normalized)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def get_stored_hash(config: BridgeConfig) -> str | None:
    """Read stored dependency hash."""
    hash_file = config.state_dir / "deps.hash"
    if hash_file.exists():
        return hash_file.read_text().strip()
    return None


def save_hash(config: BridgeConfig, hash_value: str) -> None:
    """Save dependency hash."""
    hash_file = config.state_dir / "deps.hash"
    hash_file.write_text(hash_value)
    logger.debug("deps_hash_saved", hash=hash_value)


def aggregate_dependencies(config: BridgeConfig) -> list[str]:
    """Aggregate dependencies from all plugin manifests."""
    all_deps = set(BRIDGE_CORE_DEPS)

    manifests = discover_plugins()
    for manifest in manifests:
        if manifest.dependencies:
            all_deps.update(manifest.dependencies)
            logger.debug(
                "plugin_deps_found",
                plugin=manifest.name,
                deps=manifest.dependencies,
            )

    return sorted(all_deps)


def find_uv() -> str | None:
    """Find UV executable."""
    return shutil.which("uv")


def get_target_venv() -> Path:
    """Get the virtual environment to sync.

    Uses current venv if running inside one, otherwise returns None
    to let UV create one in the project directory.
    """
    # Check VIRTUAL_ENV env var
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        return Path(venv)

    # Check if sys.prefix differs from sys.base_prefix (indicates venv)
    if sys.prefix != sys.base_prefix:
        return Path(sys.prefix)

    return None


def get_installed_plugin_deps(config: BridgeConfig) -> set[str]:
    """Get the set of currently tracked plugin dependencies.

    Reads from the stored deps list to know what we previously installed.
    """
    deps_file = config.state_dir / "deps.list"
    if deps_file.exists():
        return set(deps_file.read_text().strip().split("\n"))
    return set()


def save_installed_deps(config: BridgeConfig, deps: list[str]) -> None:
    """Save the list of installed plugin dependencies."""
    deps_file = config.state_dir / "deps.list"
    deps_file.write_text("\n".join(sorted(deps)))


def normalize_dep_name(dep: str) -> str:
    """Extract package name from dependency spec (e.g., 'foo>=1.0' -> 'foo')."""
    # Handle various specifiers: >=, <=, ==, ~=, !=, >, <, [extras]
    match = re.match(r"^([a-zA-Z0-9_-]+)", dep)
    return match.group(1).lower().replace("-", "_") if match else dep.lower()


def run_uv_install(config: BridgeConfig, deps: list[str], force_reinstall: bool = False) -> bool:
    """Install dependencies using uv pip install.

    Uses uv pip install to add deps without removing existing packages
    (like the bridge itself).

    Args:
        config: Bridge configuration
        deps: List of dependency specs to install
        force_reinstall: If True, reinstall packages

    Returns:
        True if install succeeded
    """
    uv = find_uv()
    if not uv:
        logger.error("uv_not_found")
        return False

    target_venv = get_target_venv()
    if not target_venv:
        logger.error("no_venv_found")
        return False

    # Build install command
    cmd = [uv, "pip", "install", "--python", str(target_venv / "bin" / "python")]

    if force_reinstall:
        cmd.append("--reinstall")

    cmd.extend(deps)

    logger.info("installing_deps", count=len(deps))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error("uv_install_failed", stderr=result.stderr)
        return False

    logger.info("deps_installed", count=len(deps))
    return True


def run_uv_uninstall(config: BridgeConfig, packages: list[str]) -> bool:
    """Uninstall packages using uv pip uninstall.

    Args:
        config: Bridge configuration
        packages: List of package names to uninstall

    Returns:
        True if uninstall succeeded
    """
    if not packages:
        return True

    uv = find_uv()
    if not uv:
        logger.error("uv_not_found")
        return False

    target_venv = get_target_venv()
    if not target_venv:
        logger.error("no_venv_found")
        return False

    # Build uninstall command
    cmd = [uv, "pip", "uninstall", "--python", str(target_venv / "bin" / "python")]
    cmd.extend(packages)

    logger.info("uninstalling_deps", packages=packages)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Uninstall failures are often due to packages not being installed - log but don't fail
        logger.warning("uv_uninstall_warning", stderr=result.stderr)

    logger.info("deps_uninstalled", packages=packages)
    return True


class SyncResult:
    """Result of dependency sync operation."""

    def __init__(
        self,
        success: bool = True,
        changed: bool = False,
        installed: list[str] | None = None,
        removed: list[str] | None = None,
    ):
        self.success = success
        self.changed = changed
        self.installed = installed or []
        self.removed = removed or []

    def __bool__(self) -> bool:
        return self.success


def sync_dependencies(config: BridgeConfig, force: bool = False) -> SyncResult:
    """Sync dependencies if they've changed.

    Main entry point for dependency management. Installs new deps and
    removes deps that are no longer needed by any plugin.

    Args:
        config: Bridge configuration
        force: Force resync even if hash matches

    Returns:
        SyncResult with success status and change info
    """
    config.ensure_dirs()

    # Aggregate all deps from current plugins
    deps = aggregate_dependencies(config)

    # Compute hash
    current_hash = compute_deps_hash(deps)
    stored_hash = get_stored_hash(config)

    logger.debug(
        "deps_hash_check",
        current=current_hash,
        stored=stored_hash,
        changed=current_hash != stored_hash,
    )

    # Check if update needed
    if not force and current_hash == stored_hash:
        logger.debug("deps_unchanged")
        return SyncResult(success=True, changed=False)

    # Get previously installed deps
    old_deps = get_installed_plugin_deps(config)
    new_dep_names = {normalize_dep_name(d) for d in deps}
    old_dep_names = {normalize_dep_name(d) for d in old_deps}

    # Compute what changed (always install all - uv handles already-installed efficiently)
    to_remove = old_dep_names - new_dep_names - {normalize_dep_name(d) for d in BRIDGE_CORE_DEPS}
    newly_installed = list(new_dep_names - old_dep_names)
    removed_list = list(to_remove)

    # Log what changed
    if current_hash != stored_hash:
        logger.info(
            "deps_changed",
            old_hash=stored_hash,
            new_hash=current_hash,
            to_install=newly_installed,
            to_remove=removed_list,
        )

    # Install deps
    if deps and not run_uv_install(config, deps, force_reinstall=force):
        return SyncResult(success=False)

    # Uninstall removed deps (only plugin-specific ones, not core deps)
    if to_remove:
        run_uv_uninstall(config, removed_list)

    # Save state
    save_hash(config, current_hash)
    save_installed_deps(config, deps)
    return SyncResult(
        success=True,
        changed=True,
        installed=newly_installed,
        removed=removed_list,
    )


def show_deps_status(config: BridgeConfig) -> dict:
    """Get current dependency status."""
    deps = aggregate_dependencies(config)
    current_hash = compute_deps_hash(deps)
    stored_hash = get_stored_hash(config)

    target_venv = get_target_venv()
    venv_exists = target_venv.exists() if target_venv else False

    return {
        "dependencies": deps,
        "current_hash": current_hash,
        "stored_hash": stored_hash,
        "in_sync": current_hash == stored_hash,
        "uv_available": find_uv() is not None,
        "venv_path": str(target_venv) if target_venv else None,
        "venv_exists": venv_exists,
        "runtime_dir": str(config.runtime_dir),
    }
