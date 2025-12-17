"""Tests for plugin discovery and registry."""

import json
import tempfile
from pathlib import Path

import pytest

from toolbus.plugins import (
    PluginManifest,
    PluginRegistry,
    discover_plugins,
    find_plugin,
)


class MockPlugin:
    """Mock plugin for testing."""

    name = "mock-plugin"
    version = "1.0.0"
    description = "A mock plugin for testing"
    router = None

    def __init__(self):
        self._started = False

    async def startup(self):
        self._started = True

    async def shutdown(self):
        self._started = False

    async def health_check(self):
        return {"name": self.name, "status": "healthy" if self._started else "stopped"}


class TestPluginManifest:
    """Test plugin manifest parsing."""

    def test_from_file(self, temp_dir):
        """Loads manifest from file."""
        manifest_data = {
            "name": "test-plugin",
            "version": "1.0.0",
            "entry_point": "test_plugin:TestPlugin",
            "description": "A test plugin",
        }
        manifest_path = temp_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data))

        manifest = PluginManifest.from_file(manifest_path)

        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.entry_point == "test_plugin:TestPlugin"
        assert manifest.path == temp_dir

    def test_missing_required_field(self, temp_dir):
        """Raises KeyError for missing required fields."""
        manifest_data = {"name": "test"}  # Missing version and entry_point
        manifest_path = temp_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(KeyError):
            PluginManifest.from_file(manifest_path)

    def test_to_dict(self, temp_dir):
        """Converts manifest to dict."""
        manifest_data = {
            "name": "test",
            "version": "1.0.0",
            "entry_point": "test:Test",
        }
        manifest_path = temp_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data))
        manifest = PluginManifest.from_file(manifest_path)

        result = manifest.to_dict()

        assert result["name"] == "test"
        assert result["path"] == str(temp_dir)


class TestPluginDiscovery:
    """Test plugin auto-discovery."""

    def test_discover_plugins(self, temp_dir):
        """Discovers plugins in directory."""
        # Create a plugin structure
        plugin_dir = temp_dir / "my-plugin"
        plugin_dir.mkdir()
        manifest = {
            "name": "my-plugin",
            "version": "1.0.0",
            "entry_point": "my_plugin:MyPlugin",
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

        manifests = discover_plugins([temp_dir])

        assert len(manifests) == 1
        assert manifests[0].name == "my-plugin"

    def test_discover_skips_invalid_manifests(self, temp_dir):
        """Skips manifests with invalid JSON."""
        plugin_dir = temp_dir / "bad-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text("not json")

        manifests = discover_plugins([temp_dir])

        assert len(manifests) == 0

    def test_find_plugin(self, temp_dir):
        """Finds specific plugin by name."""
        plugin_dir = temp_dir / "target"
        plugin_dir.mkdir()
        manifest = {
            "name": "target",
            "version": "1.0.0",
            "entry_point": "target:Target",
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

        result = find_plugin("target", [temp_dir])

        assert result is not None
        assert result.name == "target"

    def test_find_plugin_not_found(self, temp_dir):
        """Returns None when plugin not found."""
        result = find_plugin("nonexistent", [temp_dir])

        assert result is None


class TestPluginRegistry:
    """Test plugin registry operations."""

    def test_register_plugin(self):
        """Can register a plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()

        registry.register(plugin)

        assert "mock-plugin" in registry
        assert len(registry) == 1

    def test_get_plugin(self):
        """Can retrieve registered plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        registry.register(plugin)

        result = registry.get("mock-plugin")

        assert result is plugin

    def test_unregister_plugin(self):
        """Can unregister a plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        registry.register(plugin)

        result = registry.unregister("mock-plugin")

        assert result is plugin
        assert "mock-plugin" not in registry

    def test_list_plugins(self):
        """Lists all registered plugins."""
        registry = PluginRegistry()
        registry.register(MockPlugin())

        plugins = registry.list_plugins()

        assert len(plugins) == 1
        assert plugins[0]["name"] == "mock-plugin"
        assert plugins[0]["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_startup_plugin(self):
        """Starts a specific plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        registry.register(plugin)

        result = await registry.startup("mock-plugin")

        assert result is True
        assert plugin._started is True

    @pytest.mark.asyncio
    async def test_shutdown_plugin(self):
        """Shuts down a specific plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        registry.register(plugin)
        await registry.startup("mock-plugin")

        result = await registry.shutdown("mock-plugin")

        assert result is True
        assert plugin._started is False

    @pytest.mark.asyncio
    async def test_startup_all(self):
        """Starts all plugins."""
        registry = PluginRegistry()
        p1 = MockPlugin()
        p1.name = "p1"
        p2 = MockPlugin()
        p2.name = "p2"
        registry.register(p1)
        registry.register(p2)

        results = await registry.startup_all()

        assert results["p1"] is True
        assert results["p2"] is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Gets health status of plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        registry.register(plugin)
        await registry.startup("mock-plugin")

        health = await registry.health_check("mock-plugin")

        assert health["status"] == "healthy"

    def test_get_routers(self):
        """Gets routers from plugins that have them."""
        from fastapi import APIRouter

        registry = PluginRegistry()
        plugin = MockPlugin()
        plugin.router = APIRouter()
        registry.register(plugin)

        routers = registry.get_routers()

        assert len(routers) == 1
        assert routers[0][0] == "/mock-plugin"


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
