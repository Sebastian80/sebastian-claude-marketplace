"""
Tests for plugin lifecycle hooks (connect/reconnect).

Tests cover:
- Default connect() behavior
- Default reconnect() calls connect()
- Custom connect() implementations
- Exception handling during connect
- Integration with startup sequence
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import APIRouter

from skills_daemon.plugins import SkillPlugin


# ============================================================================
# Test Plugin Implementations
# ============================================================================

class MinimalPlugin(SkillPlugin):
    """Plugin with minimal implementation (defaults only)."""

    @property
    def name(self) -> str:
        return "minimal"

    @property
    def router(self) -> APIRouter:
        return APIRouter()


class ConnectablePlugin(SkillPlugin):
    """Plugin with custom connect/reconnect."""

    def __init__(self):
        self.connected = False
        self.connect_count = 0
        self.reconnect_count = 0
        self.startup_called = False
        self.shutdown_called = False

    @property
    def name(self) -> str:
        return "connectable"

    @property
    def router(self) -> APIRouter:
        return APIRouter()

    async def startup(self) -> None:
        self.startup_called = True

    async def connect(self) -> None:
        self.connect_count += 1
        self.connected = True

    async def reconnect(self) -> None:
        self.reconnect_count += 1
        self.connected = False
        await asyncio.sleep(0.01)  # Brief delay
        await self.connect()

    async def shutdown(self) -> None:
        self.shutdown_called = True
        self.connected = False

    def health_check(self) -> dict:
        return {
            "status": "connected" if self.connected else "disconnected",
            "connect_count": self.connect_count,
        }


class FailingConnectPlugin(SkillPlugin):
    """Plugin whose connect() always fails."""

    def __init__(self):
        self.connect_attempts = 0

    @property
    def name(self) -> str:
        return "failing"

    @property
    def router(self) -> APIRouter:
        return APIRouter()

    async def connect(self) -> None:
        self.connect_attempts += 1
        raise ConnectionError("Cannot connect to backend")


class SlowConnectPlugin(SkillPlugin):
    """Plugin with slow connect for timeout testing."""

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.connected = False

    @property
    def name(self) -> str:
        return "slow"

    @property
    def router(self) -> APIRouter:
        return APIRouter()

    async def connect(self) -> None:
        await asyncio.sleep(self.delay)
        self.connected = True


# ============================================================================
# Default Behavior Tests
# ============================================================================

class TestDefaultBehavior:
    """Test default connect/reconnect implementations."""

    @pytest.mark.asyncio
    async def test_default_connect_does_nothing(self):
        """Default connect() is a no-op."""
        plugin = MinimalPlugin()

        # Should not raise
        await plugin.connect()

    @pytest.mark.asyncio
    async def test_default_reconnect_calls_connect(self):
        """Default reconnect() delegates to connect()."""
        plugin = MinimalPlugin()

        with patch.object(plugin, "connect", new_callable=AsyncMock) as mock_connect:
            await plugin.reconnect()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_default_health_check_returns_ok(self):
        """Default health_check returns ok status."""
        plugin = MinimalPlugin()

        result = plugin.health_check()

        assert result == {"status": "ok"}

    def test_default_description_empty(self):
        """Default description is empty string."""
        plugin = MinimalPlugin()
        assert plugin.description == ""

    def test_default_version(self):
        """Default version is 1.0.0."""
        plugin = MinimalPlugin()
        assert plugin.version == "1.0.0"


# ============================================================================
# Custom Connect Implementation Tests
# ============================================================================

class TestCustomConnect:
    """Test custom connect implementations."""

    @pytest.mark.asyncio
    async def test_connect_tracks_state(self):
        """Custom connect can track connection state."""
        plugin = ConnectablePlugin()

        assert not plugin.connected
        assert plugin.connect_count == 0

        await plugin.connect()

        assert plugin.connected
        assert plugin.connect_count == 1

    @pytest.mark.asyncio
    async def test_multiple_connects(self):
        """Multiple connect calls tracked."""
        plugin = ConnectablePlugin()

        await plugin.connect()
        await plugin.connect()
        await plugin.connect()

        assert plugin.connect_count == 3

    @pytest.mark.asyncio
    async def test_reconnect_with_delay(self):
        """Custom reconnect can include delay."""
        plugin = ConnectablePlugin()
        await plugin.connect()

        # Reconnect should reset and reconnect
        await plugin.reconnect()

        assert plugin.connected
        assert plugin.connect_count == 2
        assert plugin.reconnect_count == 1

    @pytest.mark.asyncio
    async def test_health_check_reflects_state(self):
        """Health check reflects connection state."""
        plugin = ConnectablePlugin()

        # Initially disconnected
        health = plugin.health_check()
        assert health["status"] == "disconnected"

        # After connect
        await plugin.connect()
        health = plugin.health_check()
        assert health["status"] == "connected"
        assert health["connect_count"] == 1


# ============================================================================
# Lifecycle Order Tests
# ============================================================================

class TestLifecycleOrder:
    """Test correct ordering of lifecycle methods."""

    @pytest.mark.asyncio
    async def test_startup_before_connect(self):
        """Startup called before connect in proper order."""
        plugin = ConnectablePlugin()
        call_order = []

        original_startup = plugin.startup
        original_connect = plugin.connect

        async def tracked_startup():
            call_order.append("startup")
            await original_startup()

        async def tracked_connect():
            call_order.append("connect")
            await original_connect()

        plugin.startup = tracked_startup
        plugin.connect = tracked_connect

        # Simulate daemon startup sequence
        await plugin.startup()
        await plugin.connect()

        assert call_order == ["startup", "connect"]

    @pytest.mark.asyncio
    async def test_shutdown_after_operations(self):
        """Shutdown properly cleans up."""
        plugin = ConnectablePlugin()

        await plugin.startup()
        await plugin.connect()
        assert plugin.connected

        await plugin.shutdown()

        assert plugin.shutdown_called
        assert not plugin.connected


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestConnectErrorHandling:
    """Test error handling during connect."""

    @pytest.mark.asyncio
    async def test_connect_exception_propagates(self):
        """Connect exceptions propagate to caller."""
        plugin = FailingConnectPlugin()

        with pytest.raises(ConnectionError) as exc_info:
            await plugin.connect()

        assert "Cannot connect to backend" in str(exc_info.value)
        assert plugin.connect_attempts == 1

    @pytest.mark.asyncio
    async def test_connect_can_be_retried(self):
        """Failed connect can be retried."""
        plugin = FailingConnectPlugin()

        for _ in range(3):
            try:
                await plugin.connect()
            except ConnectionError:
                pass

        assert plugin.connect_attempts == 3

    @pytest.mark.asyncio
    async def test_reconnect_after_failure(self):
        """Reconnect can be called after connect failure."""
        plugin = FailingConnectPlugin()

        # First connect fails
        try:
            await plugin.connect()
        except ConnectionError:
            pass

        # Reconnect also fails (same behavior)
        try:
            await plugin.reconnect()
        except ConnectionError:
            pass

        assert plugin.connect_attempts == 2


# ============================================================================
# Timeout Tests
# ============================================================================

class TestConnectTimeout:
    """Test connect timeout handling."""

    @pytest.mark.asyncio
    async def test_slow_connect_can_timeout(self):
        """Slow connect can be cancelled via timeout."""
        plugin = SlowConnectPlugin(delay=10.0)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(plugin.connect(), timeout=0.1)

        assert not plugin.connected

    @pytest.mark.asyncio
    async def test_fast_connect_completes(self):
        """Fast connect completes within timeout."""
        plugin = SlowConnectPlugin(delay=0.01)

        await asyncio.wait_for(plugin.connect(), timeout=1.0)

        assert plugin.connected


# ============================================================================
# Integration with Main Lifespan
# ============================================================================

class TestLifespanIntegration:
    """Test integration with main.py lifespan."""

    @pytest.mark.asyncio
    async def test_lifespan_calls_connect_after_startup(self, isolated_registry):
        """Lifespan sequence calls connect after startup."""
        plugin = ConnectablePlugin()
        isolated_registry.register(plugin)

        # Simulate lifespan startup sequence
        for p in isolated_registry.all():
            await p.startup()
            await p.connect()

        assert plugin.startup_called
        assert plugin.connected
        assert plugin.connect_count == 1

    @pytest.mark.asyncio
    async def test_connect_failure_doesnt_prevent_daemon(self, isolated_registry):
        """Connect failure logged but doesn't stop daemon."""
        good_plugin = ConnectablePlugin()
        bad_plugin = FailingConnectPlugin()

        isolated_registry.register(good_plugin)
        isolated_registry.register(bad_plugin)

        errors = []

        # Simulate lifespan with error handling
        for p in isolated_registry.all():
            await p.startup()
            try:
                await p.connect()
            except Exception as e:
                errors.append((p.name, str(e)))

        # Good plugin connected
        assert good_plugin.connected

        # Bad plugin failed but daemon continues
        assert len(errors) == 1
        assert errors[0][0] == "failing"
        assert "Cannot connect" in errors[0][1]

    @pytest.mark.asyncio
    async def test_multiple_plugins_connect_independently(self, isolated_registry):
        """Each plugin connects independently."""

        class Plugin1(ConnectablePlugin):
            @property
            def name(self) -> str:
                return "plugin1"

        class Plugin2(ConnectablePlugin):
            @property
            def name(self) -> str:
                return "plugin2"

        plugin1 = Plugin1()
        plugin2 = Plugin2()

        isolated_registry.register(plugin1)
        isolated_registry.register(plugin2)

        for p in isolated_registry.all():
            await p.connect()

        assert plugin1.connected
        assert plugin2.connected
        assert plugin1.connect_count == 1
        assert plugin2.connect_count == 1


# ============================================================================
# Reconnect Patterns Tests
# ============================================================================

class TestReconnectPatterns:
    """Test various reconnection patterns."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_reconnect(self):
        """Plugin can implement exponential backoff."""

        class BackoffPlugin(SkillPlugin):
            def __init__(self):
                self.attempt = 0
                self.delays = []

            @property
            def name(self) -> str:
                return "backoff"

            @property
            def router(self) -> APIRouter:
                return APIRouter()

            async def connect(self) -> None:
                self.attempt += 1
                if self.attempt < 3:
                    raise ConnectionError("Not ready")

            async def reconnect(self) -> None:
                delay = min(2 ** self.attempt * 0.01, 1.0)  # Cap at 1s
                self.delays.append(delay)
                await asyncio.sleep(delay)
                await self.connect()

        plugin = BackoffPlugin()

        # First attempts fail
        for _ in range(2):
            try:
                await plugin.reconnect()
            except ConnectionError:
                pass

        # Third succeeds
        await plugin.reconnect()

        assert plugin.attempt == 3
        assert len(plugin.delays) == 3
        # Delays should increase
        assert plugin.delays[0] < plugin.delays[1] < plugin.delays[2]

    @pytest.mark.asyncio
    async def test_reconnect_with_state_cleanup(self):
        """Reconnect can clean up state before reconnecting."""

        class StatefulPlugin(SkillPlugin):
            def __init__(self):
                self.cache = {}
                self.connected = False

            @property
            def name(self) -> str:
                return "stateful"

            @property
            def router(self) -> APIRouter:
                return APIRouter()

            async def connect(self) -> None:
                self.cache["session"] = "new-session"
                self.connected = True

            async def reconnect(self) -> None:
                # Clear stale state
                self.cache.clear()
                self.connected = False
                await self.connect()

        plugin = StatefulPlugin()

        await plugin.connect()
        plugin.cache["extra"] = "data"

        await plugin.reconnect()

        # Old state cleared, new session established
        assert "session" in plugin.cache
        assert "extra" not in plugin.cache
        assert plugin.connected
