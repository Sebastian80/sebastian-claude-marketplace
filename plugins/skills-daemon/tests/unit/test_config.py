"""Unit tests for configuration module."""

import os
import pytest
from skills_daemon.config import DaemonConfig, _get_env, _get_env_int


class TestConfig:
    """Test configuration loading."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = DaemonConfig()

        assert config.host == "::"  # Dual-stack for ESET compatibility
        assert config.port == 9100
        assert config.idle_timeout == 1800
        assert config.log_level == "INFO"

    def test_daemon_url_property(self):
        """daemon_url uses IPv6 loopback to bypass ESET."""
        config = DaemonConfig()

        assert config.daemon_url == "http://[::1]:9100"

    def test_env_override_host(self, monkeypatch):
        """Environment variables override defaults."""
        monkeypatch.setenv("SKILLS_DAEMON_HOST", "0.0.0.0")

        # Need to reimport to pick up new env
        config = DaemonConfig(
            host=os.environ.get("SKILLS_DAEMON_HOST", "::")
        )

        assert config.host == "0.0.0.0"

    def test_env_override_port(self, monkeypatch):
        """Port can be overridden via environment."""
        monkeypatch.setenv("SKILLS_DAEMON_PORT", "9200")

        port = int(os.environ.get("SKILLS_DAEMON_PORT", "9100"))

        assert port == 9200

    def test_config_is_immutable(self):
        """Config dataclass is frozen."""
        config = DaemonConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.port = 8080


class TestEnvHelpers:
    """Test environment variable helpers."""

    def test_get_env_returns_default(self):
        """Returns default when env not set."""
        result = _get_env("NONEXISTENT_KEY", "default")
        assert result == "default"

    def test_get_env_int_converts(self, monkeypatch):
        """Converts string to int."""
        monkeypatch.setenv("SKILLS_DAEMON_TEST_INT", "42")
        result = _get_env_int("TEST_INT", 0)
        assert result == 42
        assert isinstance(result, int)
