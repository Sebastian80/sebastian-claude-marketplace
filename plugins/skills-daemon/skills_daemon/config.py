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
- SKILLS_DAEMON_LOG_FILE: Log file path (default: /tmp/skills-daemon.log)
- SKILLS_DAEMON_PID_FILE: PID file path (default: /tmp/skills-daemon.pid)
"""

import os
from dataclasses import dataclass
from pathlib import Path


def _get_env(key: str, default: str) -> str:
    """Get environment variable with SKILLS_DAEMON_ prefix."""
    return os.environ.get(f"SKILLS_DAEMON_{key}", default)


def _get_env_int(key: str, default: int) -> int:
    """Get integer environment variable."""
    return int(_get_env(key, str(default)))


def _get_env_path(key: str, default: str) -> Path:
    """Get path environment variable."""
    return Path(_get_env(key, default))


@dataclass(frozen=True)
class DaemonConfig:
    """Immutable daemon configuration."""

    host: str = _get_env("HOST", "127.0.0.1")
    port: int = _get_env_int("PORT", 9100)
    idle_timeout: int = _get_env_int("TIMEOUT", 1800)
    shutdown_timeout: int = _get_env_int("SHUTDOWN_TIMEOUT", 10)
    log_level: str = _get_env("LOG_LEVEL", "INFO")
    log_file: Path = _get_env_path("LOG_FILE", "/tmp/skills-daemon.log")
    pid_file: Path = _get_env_path("PID_FILE", "/tmp/skills-daemon.pid")

    # Log rotation settings
    log_max_bytes: int = 5 * 1024 * 1024  # 5MB
    log_backup_count: int = 3

    @property
    def daemon_url(self) -> str:
        """Full daemon URL."""
        return f"http://{self.host}:{self.port}"


# Global singleton
config = DaemonConfig()
