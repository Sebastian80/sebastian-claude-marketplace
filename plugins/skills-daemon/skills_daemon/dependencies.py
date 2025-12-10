"""
Dependency management for skills daemon.

Automatically installs plugin dependencies from manifest.json files.
"""

import json
import subprocess
from pathlib import Path

from .config import config
from .logging import logger


def discover_manifests() -> list[Path]:
    """Find all plugin manifest.json files.

    Searches:
    1. ~/.claude/plugins/**/skills_plugin/manifest.json
    """
    manifests = []

    claude_plugins = Path.home() / ".claude" / "plugins"
    if claude_plugins.exists():
        for manifest in claude_plugins.rglob("skills_plugin/manifest.json"):
            manifests.append(manifest)

    return manifests


def collect_dependencies() -> set[str]:
    """Collect all dependencies from plugin manifests."""
    all_deps = set()

    for manifest_path in discover_manifests():
        try:
            manifest = json.loads(manifest_path.read_text())
            deps = manifest.get("dependencies", [])
            all_deps.update(deps)
            logger.debug(
                f"Found dependencies in {manifest_path.parent.name}",
                plugin=manifest.get("name", "unknown"),
                deps=deps,
            )
        except Exception as e:
            logger.warning(f"Failed to read manifest: {manifest_path}", error=str(e))

    return all_deps


def get_installed_packages() -> dict[str, str]:
    """Get dict of installed packages and versions.

    Uses uv pip list since uv-created venvs don't include pip.
    """
    venv_python = config.venv_dir / "bin" / "python"

    try:
        result = subprocess.run(
            ["uv", "pip", "list", "--python", str(venv_python), "--format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            packages = json.loads(result.stdout)
            # Normalize names: lowercase and replace underscores/dots with dashes
            return {
                p["name"].lower().replace("_", "-").replace(".", "-"): p["version"]
                for p in packages
            }
    except Exception as e:
        logger.warning("Failed to get installed packages", error=str(e))

    return {}


def parse_requirement(req: str) -> tuple[str, str]:
    """Parse requirement string into (package_name, version_spec).

    Examples:
        "httpx>=0.25" -> ("httpx", ">=0.25")
        "atlassian-python-api" -> ("atlassian-python-api", "")
    """
    for op in [">=", "<=", "==", "!=", "~=", ">", "<"]:
        if op in req:
            idx = req.index(op)
            return req[:idx].strip(), req[idx:].strip()
    return req.strip(), ""


def is_satisfied(req: str, installed: dict[str, str]) -> bool:
    """Check if a requirement is satisfied by installed packages."""
    name, version_spec = parse_requirement(req)
    # Normalize: lowercase, replace underscores/dots with dashes
    name_normalized = name.lower().replace("_", "-").replace(".", "-")

    # Check if package is installed
    if name_normalized not in installed:
        return False

    # For now, just check presence (full version comparison is complex)
    # TODO: Use packaging library for proper version comparison
    return True


def sync_plugin_dependencies() -> dict:
    """Install missing dependencies from plugin manifests.

    Returns:
        dict with keys: installed, already_satisfied, failed
    """
    result = {
        "installed": [],
        "already_satisfied": [],
        "failed": [],
    }

    all_deps = collect_dependencies()
    if not all_deps:
        logger.info("No plugin dependencies to install")
        return result

    installed = get_installed_packages()
    missing = []

    for dep in all_deps:
        if is_satisfied(dep, installed):
            result["already_satisfied"].append(dep)
        else:
            missing.append(dep)

    if not missing:
        logger.info(
            "All plugin dependencies satisfied",
            count=len(result["already_satisfied"]),
        )
        return result

    logger.info(f"Installing {len(missing)} missing dependencies", deps=missing)

    # Install using uv pip for speed
    venv_python = config.venv_dir / "bin" / "python"

    try:
        cmd = ["uv", "pip", "install", "--python", str(venv_python)] + missing
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if proc.returncode == 0:
            result["installed"] = missing
            logger.info(
                "Dependencies installed successfully",
                installed=missing,
            )
        else:
            result["failed"] = missing
            logger.error(
                "Dependency installation failed",
                stderr=proc.stderr,
                deps=missing,
            )
    except subprocess.TimeoutExpired:
        result["failed"] = missing
        logger.error("Dependency installation timed out", deps=missing)
    except Exception as e:
        result["failed"] = missing
        logger.error("Dependency installation error", error=str(e), deps=missing)

    return result
