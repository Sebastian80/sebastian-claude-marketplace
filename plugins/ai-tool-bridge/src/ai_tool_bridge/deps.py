"""
Dependency Management - UV-based automatic dependency installation.

On daemon startup:
1. Scans all plugin manifest.json files
2. Aggregates dependencies
3. Computes hash of all deps
4. If hash changed since last install, runs `uv pip install`
5. Saves new hash

This ensures plugins can add dependencies and they're auto-installed.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import structlog

from .config import BridgeConfig
from .plugins.discovery import discover_plugins

logger = structlog.get_logger(__name__)


def compute_deps_hash(deps: list[str]) -> str:
    """Compute deterministic hash of dependencies.

    Args:
        deps: List of dependency strings (e.g., ["httpx>=0.25", "rich>=13.0"])

    Returns:
        SHA256 hash of sorted, normalized dependencies
    """
    # Sort and normalize for deterministic hash
    normalized = sorted(set(d.strip().lower() for d in deps if d.strip()))
    content = "\n".join(normalized)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def get_stored_hash(config: BridgeConfig) -> str | None:
    """Read stored dependency hash.

    Args:
        config: Bridge configuration

    Returns:
        Stored hash string or None if not found
    """
    hash_file = config.state_dir / "deps.hash"
    if hash_file.exists():
        return hash_file.read_text().strip()
    return None


def save_hash(config: BridgeConfig, hash_value: str) -> None:
    """Save dependency hash.

    Args:
        config: Bridge configuration
        hash_value: Hash to save
    """
    hash_file = config.state_dir / "deps.hash"
    hash_file.write_text(hash_value)
    logger.debug("deps_hash_saved", hash=hash_value)


def aggregate_dependencies(config: BridgeConfig) -> list[str]:
    """Aggregate dependencies from all plugin manifests.

    Args:
        config: Bridge configuration

    Returns:
        Combined list of all plugin dependencies
    """
    all_deps = set()

    # Get bridge's own dependencies
    bridge_deps = _get_bridge_deps()
    all_deps.update(bridge_deps)

    # Get dependencies from all discovered plugins
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


def _get_bridge_deps() -> list[str]:
    """Get the bridge's own core dependencies.

    These are the deps needed by ai-tool-bridge itself,
    not from plugins.
    """
    # Core deps that bridge always needs
    return [
        "fastapi>=0.109",
        "uvicorn>=0.27",
        "httpx>=0.25",
        "structlog>=24.0",
    ]


def find_uv() -> str | None:
    """Find UV executable.

    Returns:
        Path to uv or None if not found
    """
    return shutil.which("uv")


def get_current_venv() -> Path | None:
    """Get the currently active virtual environment.

    Returns:
        Path to current venv or None if not in a venv
    """
    # Check VIRTUAL_ENV env var first
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        return Path(venv)

    # Check if sys.prefix differs from sys.base_prefix (indicates venv)
    if sys.prefix != sys.base_prefix:
        return Path(sys.prefix)

    return None


def ensure_venv(config: BridgeConfig) -> Path:
    """Ensure virtual environment exists.

    Uses the current venv if running inside one, otherwise creates
    a shared venv at config.venv_dir.

    Args:
        config: Bridge configuration

    Returns:
        Path to venv directory

    Raises:
        RuntimeError: If UV not found or venv creation fails
    """
    # Prefer current venv if we're in one
    current_venv = get_current_venv()
    if current_venv and (current_venv / "bin" / "python").exists():
        logger.debug("using_current_venv", path=str(current_venv))
        return current_venv

    # Fall back to shared venv
    venv_dir = config.venv_dir

    if (venv_dir / "bin" / "python").exists():
        return venv_dir

    uv = find_uv()
    if not uv:
        raise RuntimeError(
            "UV not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )

    logger.info("creating_venv", path=str(venv_dir))

    result = subprocess.run(
        [uv, "venv", str(venv_dir), "--python", f"python{sys.version_info.major}.{sys.version_info.minor}"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to create venv: {result.stderr}")

    return venv_dir


def install_deps(config: BridgeConfig, deps: list[str]) -> bool:
    """Install dependencies using UV.

    Args:
        config: Bridge configuration
        deps: List of dependencies to install

    Returns:
        True if installation succeeded
    """
    uv = find_uv()
    if not uv:
        logger.error("uv_not_found")
        return False

    venv_dir = ensure_venv(config)

    logger.info("installing_deps", count=len(deps))

    # Build install command
    cmd = [
        uv, "pip", "install",
        "--python", str(venv_dir / "bin" / "python"),
        *deps,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error("deps_install_failed", stderr=result.stderr)
        return False

    logger.info("deps_installed", count=len(deps))
    return True


def sync_dependencies(config: BridgeConfig, force: bool = False) -> bool:
    """Sync dependencies if they've changed.

    Main entry point for dependency management.
    Called before daemon startup.

    Args:
        config: Bridge configuration
        force: Force reinstall even if hash matches

    Returns:
        True if deps are in sync (either unchanged or successfully updated)
    """
    config.ensure_dirs()

    # Aggregate all deps
    deps = aggregate_dependencies(config)
    if not deps:
        logger.debug("no_deps_to_sync")
        return True

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
        return True

    # Install deps
    if current_hash != stored_hash:
        logger.info(
            "deps_changed",
            old_hash=stored_hash,
            new_hash=current_hash,
            deps=deps,
        )

    if not install_deps(config, deps):
        return False

    # Save new hash
    save_hash(config, current_hash)
    return True


def show_deps_status(config: BridgeConfig) -> dict:
    """Get current dependency status.

    Returns:
        Status dict with deps, hash, and sync state
    """
    deps = aggregate_dependencies(config)
    current_hash = compute_deps_hash(deps)
    stored_hash = get_stored_hash(config)

    # Check which venv would be used
    current_venv = get_current_venv()
    if current_venv:
        venv_path = current_venv
        venv_exists = (current_venv / "bin" / "python").exists()
    else:
        venv_path = config.venv_dir
        venv_exists = (config.venv_dir / "bin" / "python").exists()

    return {
        "dependencies": deps,
        "current_hash": current_hash,
        "stored_hash": stored_hash,
        "in_sync": current_hash == stored_hash,
        "uv_available": find_uv() is not None,
        "venv_exists": venv_exists,
        "venv_path": str(venv_path),
    }
