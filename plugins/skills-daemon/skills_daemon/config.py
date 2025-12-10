"""
Centralized configuration for skills daemon.

Configuration sources (priority order):
1. Environment variables (SKILLS_DAEMON_*)
2. Default values

Environment variables:
- SKILLS_DAEMON_HOST: Bind address (default: 127.0.0.1)
- SKILLS_DAEMON_PORT: Port number (default: 9100)
- SKILLS_DAEMON_TIMEOUT: Idle timeout in seconds (default: 1800)
- SKILLS_DAEMON_LOG_LEVEL: Log level (default: INFO)
- SKILLS_DAEMON_RUNTIME_DIR: Runtime directory (default: ~/.local/share/skills-daemon)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


# Stable runtime location (survives plugin updates)
DEFAULT_RUNTIME_DIR = Path.home() / ".local/share/skills-daemon"


def _get_env(key: str, default: str) -> str:
    """Get environment variable with SKILLS_DAEMON_ prefix."""
    return os.environ.get(f"SKILLS_DAEMON_{key}", default)


def _get_env_int(key: str, default: int) -> int:
    """Get integer environment variable."""
    return int(_get_env(key, str(default)))


def _get_env_path(key: str, default: Path) -> Path:
    """Get path environment variable."""
    val = os.environ.get(f"SKILLS_DAEMON_{key}")
    return Path(val) if val else default


@dataclass(frozen=True)
class DaemonConfig:
    """Immutable daemon configuration."""

    host: str = _get_env("HOST", "127.0.0.1")
    port: int = _get_env_int("PORT", 9100)
    idle_timeout: int = _get_env_int("TIMEOUT", 1800)
    shutdown_timeout: int = _get_env_int("SHUTDOWN_TIMEOUT", 10)
    log_level: str = _get_env("LOG_LEVEL", "INFO")

    # Runtime directories (stable location, survives plugin updates)
    runtime_dir: Path = _get_env_path("RUNTIME_DIR", DEFAULT_RUNTIME_DIR)

    # Log rotation settings
    log_max_bytes: int = 5 * 1024 * 1024  # 5MB
    log_backup_count: int = 3

    @property
    def venv_dir(self) -> Path:
        """Virtual environment directory."""
        return self.runtime_dir / "venv"

    @property
    def log_dir(self) -> Path:
        """Log directory."""
        return self.runtime_dir / "logs"

    @property
    def log_file(self) -> Path:
        """Log file path."""
        return self.log_dir / "daemon.log"

    @property
    def state_dir(self) -> Path:
        """State directory for PID, cache, etc."""
        return self.runtime_dir / "state"

    @property
    def pid_file(self) -> Path:
        """PID file path."""
        return self.state_dir / "daemon.pid"

    @property
    def daemon_url(self) -> str:
        """Full daemon URL."""
        return f"http://{self.host}:{self.port}"

    def ensure_dirs(self) -> None:
        """Create runtime directories if they don't exist."""
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.venv_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        self.state_dir.mkdir(exist_ok=True)


# Global singleton
config = DaemonConfig()
