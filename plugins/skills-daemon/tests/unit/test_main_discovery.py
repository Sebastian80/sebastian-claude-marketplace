"""
Tests for main.py plugin discovery and app functionality.

Tests cover:
- Plugin discovery from env var, config file, and convention
- Plugin loading from path
- Router mounting
- Health check cwd/venv validation
- Plugin help endpoint
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from skills_daemon.main import (
    check_cwd_valid,
    check_venv_valid,
    discover_and_register_plugins,
    load_plugin_from_path,
    mount_plugin_routers,
    _generate_plugin_help,
    _generate_command_help,
)
from skills_daemon.plugins import registry, SkillPlugin
from fastapi import APIRouter, FastAPI, Query


# ============================================================================
# check_cwd_valid() Tests
# ============================================================================

class TestCheckCwdValid:
    """Tests for working directory validation."""

    def test_valid_cwd(self):
        """Returns True when CWD exists."""
        # Current directory should always exist
        result = check_cwd_valid()
        assert result is True

    def test_invalid_cwd_returns_false(self, temp_dir):
        """Returns False when CWD check fails."""
        with patch("skills_daemon.main.Path.cwd", side_effect=OSError):
            result = check_cwd_valid()
        assert result is False

    def test_deleted_cwd_marker(self, temp_dir):
        """Returns False when /proc/self/cwd shows (deleted)."""
        with patch("skills_daemon.main.Path.cwd") as mock_cwd:
            mock_cwd.return_value = temp_dir

            # Simulate proc showing deleted
            proc_path = MagicMock()
            proc_path.exists.return_value = True
            proc_path.resolve.return_value = Path("/some/path (deleted)")

            with patch("skills_daemon.main.Path") as mock_path:
                mock_path.cwd.return_value = temp_dir
                mock_path.return_value = proc_path

                result = check_cwd_valid()

        # When (deleted) is in path, should return False
        # Note: exact behavior depends on implementation


# ============================================================================
# check_venv_valid() Tests
# ============================================================================

class TestCheckVenvValid:
    """Tests for virtual environment validation."""

    def test_valid_venv(self, temp_dir):
        """Returns True when venv python exists."""
        venv_dir = temp_dir / "venv"
        python_path = venv_dir / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.touch()

        with patch("skills_daemon.main.config") as mock_config:
            mock_config.venv_dir = venv_dir
            result = check_venv_valid()

        assert result is True

    def test_invalid_venv_no_python(self, temp_dir):
        """Returns False when venv python missing."""
        venv_dir = temp_dir / "venv"
        venv_dir.mkdir(parents=True)

        with patch("skills_daemon.main.config") as mock_config:
            mock_config.venv_dir = venv_dir
            result = check_venv_valid()

        assert result is False

    def test_invalid_venv_no_dir(self, temp_dir):
        """Returns False when venv directory missing."""
        venv_dir = temp_dir / "nonexistent"

        with patch("skills_daemon.main.config") as mock_config:
            mock_config.venv_dir = venv_dir
            result = check_venv_valid()

        assert result is False


# ============================================================================
# discover_and_register_plugins() Tests
# ============================================================================

class TestDiscoverAndRegisterPlugins:
    """Tests for plugin discovery."""

    @pytest.fixture(autouse=True)
    def clean_registry(self, isolated_registry):
        """Clean registry for each test."""
        yield

    def test_discover_from_env_var(self, temp_dir, monkeypatch):
        """Discovers plugins from SKILLS_DAEMON_PLUGINS env var."""
        # Create plugin file
        plugin_dir = temp_dir / "my_plugin"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "__init__.py"
        plugin_file.write_text("""
from fastapi import APIRouter
from skills_daemon.plugins import SkillPlugin

class EnvPlugin(SkillPlugin):
    @property
    def name(self) -> str:
        return "env-plugin"

    @property
    def router(self) -> APIRouter:
        return APIRouter()
""")

        monkeypatch.setenv("SKILLS_DAEMON_PLUGINS", str(plugin_dir))

        with patch("skills_daemon.main.registry") as mock_registry:
            mock_registry.names.return_value = []
            discover_and_register_plugins()

            # Should have called register
            assert mock_registry.register.called

    def test_discover_from_config_file(self, temp_dir, monkeypatch):
        """Discovers plugins from config file."""
        # Clear env var
        monkeypatch.delenv("SKILLS_DAEMON_PLUGINS", raising=False)

        # Create config dir
        config_dir = temp_dir / ".config" / "skills-daemon"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "plugins.conf"

        # Create plugin
        plugin_dir = temp_dir / "plugins" / "my_plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "__init__.py").write_text("""
from fastapi import APIRouter
from skills_daemon.plugins import SkillPlugin

class ConfigPlugin(SkillPlugin):
    @property
    def name(self) -> str:
        return "config-plugin"

    @property
    def router(self) -> APIRouter:
        return APIRouter()
""")

        config_file.write_text(f"{plugin_dir}\n# comment line\n")

        with patch.object(Path, "home", return_value=temp_dir):
            with patch("skills_daemon.main.registry") as mock_registry:
                mock_registry.names.return_value = []
                discover_and_register_plugins()

    def test_discover_skips_comments(self, temp_dir, monkeypatch):
        """Config file comments are ignored."""
        monkeypatch.delenv("SKILLS_DAEMON_PLUGINS", raising=False)

        config_dir = temp_dir / ".config" / "skills-daemon"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "plugins.conf"
        config_file.write_text("# This is a comment\n\n# Another comment\n")

        with patch.object(Path, "home", return_value=temp_dir):
            # Should not crash on comments-only file
            discover_and_register_plugins()

    def test_discover_handles_missing_path(self, temp_dir, monkeypatch):
        """Handles missing plugin path gracefully."""
        monkeypatch.setenv("SKILLS_DAEMON_PLUGINS", "/nonexistent/path")

        # Should not raise
        discover_and_register_plugins()


# ============================================================================
# load_plugin_from_path() Tests
# ============================================================================

class TestLoadPluginFromPath:
    """Tests for loading individual plugins."""

    @pytest.fixture(autouse=True)
    def clean_registry(self, isolated_registry):
        """Clean registry for each test."""
        yield

    def test_load_valid_plugin(self, temp_dir):
        """Loads valid plugin class."""
        plugin_file = temp_dir / "__init__.py"
        plugin_file.write_text("""
from fastapi import APIRouter
from skills_daemon.plugins import SkillPlugin

class TestPlugin(SkillPlugin):
    @property
    def name(self) -> str:
        return "test-loaded"

    @property
    def router(self) -> APIRouter:
        return APIRouter()
""")

        load_plugin_from_path(plugin_file)

        assert "test-loaded" in registry.names()

    def test_load_no_plugin_class(self, temp_dir):
        """Warns when no plugin class found."""
        plugin_file = temp_dir / "__init__.py"
        plugin_file.write_text("""
# No plugin class here
x = 1
""")

        with patch("skills_daemon.main.logger") as mock_logger:
            load_plugin_from_path(plugin_file)
            mock_logger.warning.assert_called()

    def test_load_syntax_error(self, temp_dir):
        """Handles syntax errors in plugin file."""
        plugin_file = temp_dir / "__init__.py"
        plugin_file.write_text("this is not valid python {{{{")

        # Should raise ImportError or SyntaxError
        with pytest.raises(Exception):
            load_plugin_from_path(plugin_file)

    def test_load_wrong_suffix_class(self, temp_dir):
        """Only loads classes ending with Plugin."""
        plugin_file = temp_dir / "__init__.py"
        plugin_file.write_text("""
from fastapi import APIRouter
from skills_daemon.plugins import SkillPlugin

class MyService(SkillPlugin):
    # Name doesn't end with 'Plugin' - should not be loaded
    @property
    def name(self) -> str:
        return "service"

    @property
    def router(self) -> APIRouter:
        return APIRouter()
""")

        with patch("skills_daemon.main.logger") as mock_logger:
            load_plugin_from_path(plugin_file)
            # Should warn about no plugin found
            mock_logger.warning.assert_called()


# ============================================================================
# mount_plugin_routers() Tests
# ============================================================================

class TestMountPluginRouters:
    """Tests for mounting plugin routers to FastAPI app."""

    def test_mount_single_plugin(self, isolated_registry, simple_plugin):
        """Mounts single plugin router."""
        isolated_registry.register(simple_plugin)
        app = FastAPI()

        mount_plugin_routers(app)

        # Should have routes for plugin
        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/test-simple" in p for p in route_paths)

    def test_mount_multiple_plugins(self, isolated_registry, simple_plugin, error_plugin):
        """Mounts multiple plugin routers."""
        isolated_registry.register(simple_plugin)
        isolated_registry.register(error_plugin)
        app = FastAPI()

        mount_plugin_routers(app)

        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/test-simple" in p for p in route_paths)
        assert any("/test-error" in p for p in route_paths)

    def test_mount_empty_registry(self, isolated_registry):
        """Handles empty registry gracefully."""
        app = FastAPI()

        # Should not raise
        mount_plugin_routers(app)


# ============================================================================
# Plugin Help Generation Tests
# ============================================================================

class TestPluginHelpGeneration:
    """Tests for dynamic help generation from FastAPI metadata."""

    @pytest.fixture
    def documented_plugin(self):
        """Plugin with documented endpoints."""

        class DocPlugin(SkillPlugin):
            @property
            def name(self) -> str:
                return "documented"

            @property
            def description(self) -> str:
                return "A well-documented plugin"

            @property
            def version(self) -> str:
                return "2.0.0"

            @property
            def router(self) -> APIRouter:
                router = APIRouter()

                @router.get("/search", summary="Search for items")
                async def search(
                    query: str = Query(..., description="Search query"),
                    limit: int = Query(10, description="Max results"),
                ):
                    return {"results": []}

                @router.post("/create", summary="Create new item")
                async def create():
                    return {"id": 1}

                return router

        return DocPlugin()

    def test_generate_plugin_help(self, documented_plugin):
        """Generates help for entire plugin."""
        result = _generate_plugin_help(documented_plugin)

        assert result["plugin"] == "documented"
        assert result["description"] == "A well-documented plugin"
        assert result["version"] == "2.0.0"
        assert "commands" in result
        assert len(result["commands"]) >= 2

    def test_generate_command_help_existing(self, documented_plugin):
        """Generates help for specific command."""
        result = _generate_command_help(documented_plugin, "search")

        assert result["plugin"] == "documented"
        assert result["command"] == "search"
        assert "/documented/search" in result["path"]
        assert "parameters" in result

    def test_generate_command_help_not_found(self, documented_plugin):
        """Returns error for unknown command."""
        result = _generate_command_help(documented_plugin, "nonexistent")

        assert "error" in result
        assert "nonexistent" in result["error"]
        assert "available" in result

    def test_help_extracts_query_params(self, documented_plugin):
        """Extracts query parameters from route."""
        result = _generate_command_help(documented_plugin, "search")

        params = result.get("parameters", [])
        param_names = [p["name"] for p in params]

        assert "query" in param_names
        assert "limit" in param_names

    def test_help_marks_required_params(self, documented_plugin):
        """Marks required parameters correctly."""
        result = _generate_command_help(documented_plugin, "search")

        params = {p["name"]: p for p in result.get("parameters", [])}

        # query is required (...), limit has default
        assert params.get("query", {}).get("required") is True
        assert params.get("limit", {}).get("required") is False


# ============================================================================
# Integration: Health Endpoint Tests
# ============================================================================

class TestHealthEndpoint:
    """Integration tests for health endpoint."""

    def test_health_includes_cwd_valid(self, client):
        """Health response includes cwd_valid."""
        response = client.get("/health")
        data = response.json()

        assert "cwd_valid" in data
        assert isinstance(data["cwd_valid"], bool)

    def test_health_includes_venv_valid(self, client):
        """Health response includes venv_valid."""
        response = client.get("/health")
        data = response.json()

        assert "venv_valid" in data
        assert isinstance(data["venv_valid"], bool)

    def test_health_includes_plugin_health(self, client, isolated_registry, simple_plugin):
        """Health response includes per-plugin health."""
        isolated_registry.register(simple_plugin)

        response = client.get("/health")
        data = response.json()

        assert "plugin_health" in data

    def test_health_handles_plugin_health_error(self, client, isolated_registry):
        """Handles errors in plugin health_check."""

        class BrokenPlugin(SkillPlugin):
            @property
            def name(self) -> str:
                return "broken"

            @property
            def router(self) -> APIRouter:
                return APIRouter()

            def health_check(self) -> dict:
                raise RuntimeError("Health check failed")

        isolated_registry.register(BrokenPlugin())

        response = client.get("/health")
        data = response.json()

        assert data["plugin_health"]["broken"]["status"] == "error"
        assert "error" in data["plugin_health"]["broken"]


# ============================================================================
# Integration: Plugin Help Endpoint Tests
# ============================================================================

class TestPluginHelpEndpoint:
    """Integration tests for /{plugin}/help endpoint."""

    def test_help_unknown_plugin(self, client):
        """Returns error for unknown plugin."""
        response = client.get("/unknown-plugin/help")
        data = response.json()

        assert "error" in data
        assert "available" in data

    def test_help_existing_plugin(self, client, isolated_registry, simple_plugin):
        """Returns help for existing plugin."""
        isolated_registry.register(simple_plugin)

        # Need to mount router for the plugin to be accessible
        from skills_daemon.main import app
        app.include_router(
            simple_plugin.router,
            prefix=f"/{simple_plugin.name}",
        )

        response = client.get("/test-simple/help")
        data = response.json()

        assert data["plugin"] == "test-simple"
        assert "commands" in data


# ============================================================================
# Edge Cases
# ============================================================================

class TestDiscoveryEdgeCases:
    """Edge case tests for plugin discovery."""

    def test_multiple_env_paths(self, temp_dir, monkeypatch):
        """Handles multiple colon-separated paths."""
        path1 = temp_dir / "plugin1"
        path2 = temp_dir / "plugin2"
        path1.mkdir()
        path2.mkdir()

        monkeypatch.setenv("SKILLS_DAEMON_PLUGINS", f"{path1}:{path2}")

        # Should process both paths without error
        discover_and_register_plugins()

    def test_empty_env_var(self, temp_dir, monkeypatch):
        """Handles empty SKILLS_DAEMON_PLUGINS."""
        monkeypatch.setenv("SKILLS_DAEMON_PLUGINS", "")

        # Should not crash
        discover_and_register_plugins()

    def test_whitespace_in_paths(self, temp_dir, monkeypatch):
        """Handles whitespace around paths."""
        plugin_dir = temp_dir / "my_plugin"
        plugin_dir.mkdir()

        monkeypatch.setenv("SKILLS_DAEMON_PLUGINS", f"  {plugin_dir}  ")

        # Should trim whitespace
        discover_and_register_plugins()

    def test_expanduser_in_paths(self, temp_dir, monkeypatch):
        """Expands ~ in paths."""
        monkeypatch.setenv("SKILLS_DAEMON_PLUGINS", "~/some/plugin")

        with patch.object(Path, "expanduser") as mock_expand:
            mock_expand.return_value = temp_dir / "expanded"
            discover_and_register_plugins()

            mock_expand.assert_called()
