"""
Centralized configuration for AI Tool Bridge.

Configuration sources (priority order):
1. Environment variables (BRIDGE_*)
2. Default values

Environment variables:
- BRIDGE_HOST: Bind address (default: :: for dual-stack IPv4/IPv6)
- BRIDGE_PORT: Port number (default: 9100)
- BRIDGE_TIMEOUT: Idle timeout in seconds (default: 1800)
- BRIDGE_LOG_LEVEL: Log level (default: INFO)
- BRIDGE_RUNTIME_DIR: Runtime directory (default: ~/.local/share/ai-tool-bridge)
- BRIDGE_NOTIFICATIONS: Enable desktop notifications (default: true)
"""

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = ["BridgeConfig", "config", "DEFAULT_RUNTIME_DIR"]

DEFAULT_RUNTIME_DIR = Path.home() / ".local/share/ai-tool-bridge"


def _get_env(key: str, default: str) -> str:
    """Get environment variable with BRIDGE_ prefix."""
    return os.environ.get(f"BRIDGE_{key}", default)


def _get_env_int(key: str, default: int) -> int:
    """Get integer environment variable."""
    return int(_get_env(key, str(default)))


def _get_env_bool(key: str, default: bool) -> bool:
    """Get boolean environment variable."""
    val = os.environ.get(f"BRIDGE_{key}")
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")


def _get_env_path(key: str, default: Path) -> Path:
    """Get path environment variable."""
    val = os.environ.get(f"BRIDGE_{key}")
    return Path(val) if val else default


@dataclass(frozen=True)
class BridgeConfig:
    """Immutable bridge configuration."""

    host: str = _get_env("HOST", "::")
    port: int = _get_env_int("PORT", 9100)
    idle_timeout: int = _get_env_int("TIMEOUT", 1800)
    shutdown_timeout: int = _get_env_int("SHUTDOWN_TIMEOUT", 10)
    log_level: str = _get_env("LOG_LEVEL", "INFO")

    runtime_dir: Path = _get_env_path("RUNTIME_DIR", DEFAULT_RUNTIME_DIR)

    # Desktop notifications
    notifications_enabled: bool = _get_env_bool("NOTIFICATIONS", True)

    # Log rotation
    log_max_bytes: int = 5 * 1024 * 1024  # 5MB
    log_backup_count: int = 3

    # Connector defaults
    connector_timeout: float = 30.0
    connector_pool_size: int = 10
    connector_health_interval: float = 10.0

    # Circuit breaker defaults
    circuit_failure_threshold: int = 5
    circuit_reset_timeout: float = 30.0

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
        return self.log_dir / "bridge.log"

    @property
    def state_dir(self) -> Path:
        """State directory for PID, cache, etc."""
        return self.runtime_dir / "state"

    @property
    def pid_file(self) -> Path:
        """PID file path."""
        return self.state_dir / "bridge.pid"

    @property
    def bridge_url(self) -> str:
        """Full bridge URL using IPv6 loopback."""
        return f"http://[::1]:{self.port}"

    def ensure_dirs(self) -> None:
        """Create runtime directories if they don't exist."""
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.venv_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        self.state_dir.mkdir(exist_ok=True)


# Global singleton
config = BridgeConfig()
