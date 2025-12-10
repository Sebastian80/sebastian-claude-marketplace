"""Unit tests for plugin registry."""

import pytest
from skills_daemon.plugins import PluginRegistry, SkillPlugin


class TestPluginRegistry:
    """Test plugin registry operations."""

    def test_register_plugin(self, isolated_registry, simple_plugin):
        """Can register a plugin."""
        isolated_registry.register(simple_plugin)

        assert "test-simple" in isolated_registry.names()

    def test_get_registered_plugin(self, isolated_registry, simple_plugin):
        """Can retrieve registered plugin."""
        isolated_registry.register(simple_plugin)

        plugin = isolated_registry.get("test-simple")

        assert plugin == simple_plugin

    def test_get_nonexistent_returns_none(self, isolated_registry):
        """Getting nonexistent plugin returns None."""
        result = isolated_registry.get("nonexistent")

        assert result is None

    def test_unregister_plugin(self, isolated_registry, simple_plugin):
        """Can unregister a plugin."""
        isolated_registry.register(simple_plugin)

        removed = isolated_registry.unregister("test-simple")

        assert removed == simple_plugin
        assert "test-simple" not in isolated_registry.names()

    def test_clear_registry(self, isolated_registry, simple_plugin, error_plugin):
        """Can clear all plugins."""
        isolated_registry.register(simple_plugin)
        isolated_registry.register(error_plugin)

        names = isolated_registry.clear()

        assert len(names) == 2
        assert isolated_registry.names() == []

    def test_all_returns_list(self, isolated_registry, simple_plugin):
        """all() returns list of plugins."""
        isolated_registry.register(simple_plugin)

        plugins = isolated_registry.all()

        assert isinstance(plugins, list)
        assert simple_plugin in plugins

    def test_names_returns_list(self, isolated_registry, simple_plugin):
        """names() returns list of plugin names."""
        isolated_registry.register(simple_plugin)

        names = isolated_registry.names()

        assert isinstance(names, list)
        assert "test-simple" in names
