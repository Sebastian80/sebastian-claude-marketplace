# Skills-Daemon Professional Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform skills-daemon from functional prototype to production-grade system with tests, proper architecture, self-healing, and professional logging.

**Architecture:** Centralized configuration, TTY-aware color system, request correlation IDs, HTTP retry with exponential backoff, pytest infrastructure with 80%+ coverage target.

**Tech Stack:** Python 3.11+, FastAPI, pytest, pytest-asyncio, uvicorn

---

## Phase 1: Critical Fixes (Must Do First)

### Task 1.1: Fix Broken Entry Point in pyproject.toml

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/pyproject.toml`

**Step 1: Read current pyproject.toml**

Check the current entry point configuration.

**Step 2: Fix entry point path**

The `cli/` directory is outside `skills_daemon/` package, so entry point path is wrong.

```toml
[project.scripts]
skills-daemon = "cli.daemon_ctl:main"
skills-client = "cli.skills_client:main"
```

**Step 3: Verify fix**

Run: `cd /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon && .venv/bin/pip install -e .`
Expected: No errors

**Step 4: Test entry points**

Run: `.venv/bin/skills-daemon --help`
Expected: Help text displays

**Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "fix: correct entry point paths in pyproject.toml"
```

---

### Task 1.2: Remove Unused httpx Dependency

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/pyproject.toml`

**Step 1: Verify httpx is unused**

Run: `grep -r "import httpx" /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/`
Expected: No matches (confirms unused)

**Step 2: Remove from dependencies**

Change:
```toml
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "httpx>=0.26.0",
]
```

To:
```toml
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
]
```

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: remove unused httpx dependency"
```

---

### Task 1.3: Create Centralized Configuration Module

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/skills_daemon/config.py`
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/skills_daemon/__init__.py`

**Step 1: Create config.py with environment variable support**

```python
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
```

**Step 2: Update __init__.py to use config**

Replace contents of `skills_daemon/__init__.py`:

```python
"""
Skills Daemon - Central daemon for Claude Code skills.

Provides a FastAPI-based HTTP server with plugin architecture.
Plugins are auto-discovered and provide their own endpoints.
"""

__version__ = "1.0.0"

# Import config for convenient access
from .config import config, DaemonConfig

# Re-export commonly used values for backward compatibility
DEFAULT_HOST = config.host
DEFAULT_PORT = config.port
IDLE_TIMEOUT = config.idle_timeout
PID_FILE = str(config.pid_file)
LOG_FILE = str(config.log_file)
```

**Step 3: Verify imports still work**

Run: `cd /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon && .venv/bin/python -c "from skills_daemon import config; print(config.daemon_url)"`
Expected: `http://127.0.0.1:9100`

**Step 4: Commit**

```bash
git add skills_daemon/config.py skills_daemon/__init__.py
git commit -m "feat: add centralized configuration with env var support"
```

---

### Task 1.4: Create TTY-Aware Color Module

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/skills_daemon/colors.py`

**Step 1: Create colors.py**

```python
"""
TTY-aware terminal colors for skills daemon.

Provides consistent color output that automatically disables
when stdout is not a terminal (piped, redirected, etc.).
"""

import sys
from typing import Callable


# ANSI color codes
_CODES = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def _is_tty() -> bool:
    """Check if stdout is a terminal."""
    return sys.stdout.isatty()


def colored(text: str, color: str) -> str:
    """Apply color to text if stdout is a TTY.

    Args:
        text: Text to colorize
        color: Color name (red, green, yellow, cyan, dim, bold, etc.)

    Returns:
        Colored text if TTY, plain text otherwise
    """
    if not _is_tty():
        return text
    code = _CODES.get(color, "")
    if not code:
        return text
    return f"{code}{text}{_CODES['reset']}"


def red(text: str) -> str:
    """Red text (errors)."""
    return colored(text, "red")


def green(text: str) -> str:
    """Green text (success)."""
    return colored(text, "green")


def yellow(text: str) -> str:
    """Yellow text (warnings)."""
    return colored(text, "yellow")


def cyan(text: str) -> str:
    """Cyan text (info)."""
    return colored(text, "cyan")


def dim(text: str) -> str:
    """Dim text (secondary info)."""
    return colored(text, "dim")


def bold(text: str) -> str:
    """Bold text (emphasis)."""
    return colored(text, "bold")


# For backward compatibility with inline tuple pattern
def get_color_tuple() -> tuple[str, str, str, str, str, str, str]:
    """Get color codes tuple (RED, GREEN, YELLOW, CYAN, DIM, BOLD, RESET).

    Returns empty strings if not a TTY.
    """
    if _is_tty():
        return (
            _CODES["red"],
            _CODES["green"],
            _CODES["yellow"],
            _CODES["cyan"],
            _CODES["dim"],
            _CODES["bold"],
            _CODES["reset"],
        )
    return ("", "", "", "", "", "", "")
```

**Step 2: Verify module works**

Run: `cd /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon && .venv/bin/python -c "from skills_daemon.colors import red, green; print(green('OK'), red('ERROR'))"`
Expected: Colored output if terminal, plain if piped

**Step 3: Commit**

```bash
git add skills_daemon/colors.py
git commit -m "feat: add TTY-aware color module"
```

---

### Task 1.5: Update CLI Files to Use Shared Colors

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/cli/daemon_ctl.py`
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/cli/skills_client.py`

**Step 1: Update daemon_ctl.py imports**

Replace lines 22-25:
```python
RED, GREEN, YELLOW, DIM, BOLD, RESET = (
    ("\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[1m", "\033[0m")
    if sys.stdout.isatty() else ("", "", "", "", "", "")
)
```

With:
```python
# Add to imports at top
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from skills_daemon.colors import get_color_tuple

RED, GREEN, YELLOW, DIM, BOLD, RESET = get_color_tuple()[:6]
```

**Step 2: Update skills_client.py imports**

Replace lines 33-36:
```python
RED, GREEN, YELLOW, CYAN, DIM, BOLD, RESET = (
    ("\033[31m", "\033[32m", "\033[33m", "\033[36m", "\033[2m", "\033[1m", "\033[0m")
    if sys.stdout.isatty() else ("", "", "", "", "", "", "")
)
```

With:
```python
# Add to imports at top
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from skills_daemon.colors import get_color_tuple

RED, GREEN, YELLOW, CYAN, DIM, BOLD, RESET = get_color_tuple()
```

**Step 3: Test both CLIs**

Run: `skills-daemon status`
Expected: Colored output

Run: `skills-daemon status | cat`
Expected: Plain text (no ANSI codes)

**Step 4: Commit**

```bash
git add cli/daemon_ctl.py cli/skills_client.py
git commit -m "refactor: use shared color module in CLI files (DRY)"
```

---

### Task 1.6: Fix TTY Detection in Formatters

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/skills_daemon/formatters.py`

**Step 1: Update HumanFormatter to use colors module**

At top of file, add import:
```python
from .colors import red, green, yellow, cyan, dim, bold, colored
```

Replace the hardcoded ANSI codes in HumanFormatter (around lines 76-82):
```python
class HumanFormatter(BaseFormatter):
    """Human-readable formatter with colors."""
    # Remove these hardcoded codes:
    # RED = "\033[31m"
    # GREEN = "\033[32m"
    # etc.
```

Update methods to use functions:
```python
def format_error(self, message: str, hint: str | None = None) -> str:
    result = f"{red('Error:')} {message}"
    if hint:
        result += f"\n{dim('Hint:')} {hint}"
    return result

def format_success(self, message: str, data: Any = None) -> str:
    result = f"{green('✓')} {message}"
    if data:
        result += f"\n{self.format(data)}"
    return result
```

**Step 2: Test formatter TTY behavior**

Run: `.venv/bin/python -c "from skills_daemon.formatters import HumanFormatter; f = HumanFormatter(); print(f.format_error('test', 'hint'))"`
Expected: Colored if terminal, plain if piped

**Step 3: Commit**

```bash
git add skills_daemon/formatters.py
git commit -m "fix: use TTY-aware colors in formatters"
```

---

## Phase 2: Testing Infrastructure

### Task 2.1: Create Test Directory Structure

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/__init__.py`
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/unit/__init__.py`
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/integration/__init__.py`
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/cli/__init__.py`
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/fixtures/__init__.py`

**Step 1: Create directory structure**

```bash
cd /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon
mkdir -p tests/unit tests/integration tests/cli tests/fixtures/plugins
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py tests/cli/__init__.py tests/fixtures/__init__.py
```

**Step 2: Commit**

```bash
git add tests/
git commit -m "chore: create test directory structure"
```

---

### Task 2.2: Create conftest.py with Core Fixtures

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/conftest.py`

**Step 1: Create conftest.py**

```python
"""
Shared pytest fixtures for skills-daemon tests.
"""

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import AsyncIterator, Iterator

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from skills_daemon.plugins import SkillPlugin, registry


# ============================================================================
# Async Support
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Temporary Directories
# ============================================================================

@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Create temporary directory for test files."""
    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def mock_pid_file(temp_dir: Path, monkeypatch) -> Path:
    """Mock PID file location."""
    pid_file = temp_dir / "test-daemon.pid"
    monkeypatch.setenv("SKILLS_DAEMON_PID_FILE", str(pid_file))
    return pid_file


@pytest.fixture
def mock_log_file(temp_dir: Path, monkeypatch) -> Path:
    """Mock log file location."""
    log_file = temp_dir / "test-daemon.log"
    monkeypatch.setenv("SKILLS_DAEMON_LOG_FILE", str(log_file))
    return log_file


# ============================================================================
# Plugin Registry Isolation
# ============================================================================

@pytest.fixture
def isolated_registry():
    """Isolate plugin registry for tests."""
    original_plugins = registry._plugins.copy()
    registry.clear()
    yield registry
    registry._plugins = original_plugins


# ============================================================================
# Mock Plugins
# ============================================================================

@pytest.fixture
def simple_plugin():
    """Simple test plugin."""

    class SimplePlugin(SkillPlugin):
        @property
        def name(self) -> str:
            return "test-simple"

        @property
        def description(self) -> str:
            return "Simple test plugin"

        @property
        def router(self) -> APIRouter:
            router = APIRouter()

            @router.get("/ping")
            async def ping():
                return {"message": "pong"}

            @router.get("/echo")
            async def echo(text: str):
                return {"echo": text}

            return router

    return SimplePlugin()


@pytest.fixture
def error_plugin():
    """Plugin that raises errors for testing."""

    class ErrorPlugin(SkillPlugin):
        @property
        def name(self) -> str:
            return "test-error"

        @property
        def description(self) -> str:
            return "Error test plugin"

        @property
        def router(self) -> APIRouter:
            router = APIRouter()

            @router.get("/fail")
            async def fail():
                raise RuntimeError("Intentional test error")

            return router

        async def startup(self) -> None:
            pass  # Can be modified to raise

        def health_check(self) -> dict:
            return {"status": "ok"}

    return ErrorPlugin()


# ============================================================================
# FastAPI Test Client
# ============================================================================

@pytest.fixture
def test_app(isolated_registry):
    """Create FastAPI app for testing."""
    from skills_daemon.main import app
    return app


@pytest.fixture
def client(test_app) -> Iterator[TestClient]:
    """Synchronous test client."""
    with TestClient(test_app) as c:
        yield c
```

**Step 2: Commit**

```bash
git add tests/conftest.py
git commit -m "feat: add pytest fixtures for daemon testing"
```

---

### Task 2.3: Add pytest Configuration to pyproject.toml

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/pyproject.toml`

**Step 1: Add pytest configuration**

Add to pyproject.toml:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
    "--asyncio-mode=auto",
]
markers = [
    "unit: Unit tests (no I/O)",
    "integration: Integration tests",
    "cli: CLI tests",
    "slow: Slow tests",
]
asyncio_mode = "auto"

[tool.coverage.run]
source = ["skills_daemon", "cli"]
omit = ["*/tests/*", "*/.venv/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "@abstractmethod",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
]
```

**Step 2: Install dev dependencies**

Run: `cd /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon && .venv/bin/pip install -e ".[dev]"`

**Step 3: Verify pytest runs**

Run: `.venv/bin/pytest --collect-only`
Expected: Shows test collection (even if empty)

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add pytest configuration and dev dependencies"
```

---

### Task 2.4: Write Unit Tests for Config Module

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/unit/test_config.py`

**Step 1: Write test_config.py**

```python
"""Unit tests for configuration module."""

import os
import pytest
from skills_daemon.config import DaemonConfig, _get_env, _get_env_int


class TestConfig:
    """Test configuration loading."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = DaemonConfig()

        assert config.host == "127.0.0.1"
        assert config.port == 9100
        assert config.idle_timeout == 1800
        assert config.log_level == "INFO"

    def test_daemon_url_property(self):
        """daemon_url combines host and port."""
        config = DaemonConfig()

        assert config.daemon_url == "http://127.0.0.1:9100"

    def test_env_override_host(self, monkeypatch):
        """Environment variables override defaults."""
        monkeypatch.setenv("SKILLS_DAEMON_HOST", "0.0.0.0")

        # Need to reimport to pick up new env
        config = DaemonConfig(
            host=os.environ.get("SKILLS_DAEMON_HOST", "127.0.0.1")
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
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/unit/test_config.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/unit/test_config.py
git commit -m "test: add unit tests for config module"
```

---

### Task 2.5: Write Unit Tests for Colors Module

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/unit/test_colors.py`

**Step 1: Write test_colors.py**

```python
"""Unit tests for colors module."""

import sys
from unittest.mock import patch

import pytest
from skills_daemon.colors import (
    colored,
    red,
    green,
    yellow,
    dim,
    bold,
    get_color_tuple,
    _is_tty,
)


class TestColoredFunction:
    """Test the colored() function."""

    def test_colored_with_tty(self):
        """Colors applied when TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = colored("test", "red")
            assert "\033[31m" in result
            assert "\033[0m" in result
            assert "test" in result

    def test_colored_without_tty(self):
        """Colors stripped when not TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=False):
            result = colored("test", "red")
            assert result == "test"
            assert "\033[" not in result

    def test_colored_unknown_color(self):
        """Unknown color returns plain text."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = colored("test", "unknown")
            assert result == "test"


class TestColorHelpers:
    """Test color helper functions."""

    def test_red(self):
        """red() applies red color."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = red("error")
            assert "\033[31m" in result

    def test_green(self):
        """green() applies green color."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = green("success")
            assert "\033[32m" in result

    def test_dim(self):
        """dim() applies dim styling."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = dim("secondary")
            assert "\033[2m" in result


class TestGetColorTuple:
    """Test get_color_tuple() for backward compatibility."""

    def test_returns_tuple_with_tty(self):
        """Returns color codes tuple when TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = get_color_tuple()
            assert len(result) == 7
            assert all(isinstance(c, str) for c in result)
            assert "\033[31m" in result[0]  # RED

    def test_returns_empty_strings_without_tty(self):
        """Returns empty strings when not TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=False):
            result = get_color_tuple()
            assert len(result) == 7
            assert all(c == "" for c in result)
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/unit/test_colors.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/unit/test_colors.py
git commit -m "test: add unit tests for colors module"
```

---

### Task 2.6: Write Unit Tests for Plugin Registry

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/unit/test_registry.py`

**Step 1: Write test_registry.py**

```python
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
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/unit/test_registry.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/unit/test_registry.py
git commit -m "test: add unit tests for plugin registry"
```

---

### Task 2.7: Write Integration Tests for Core Endpoints

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/tests/integration/test_endpoints.py`

**Step 1: Write test_endpoints.py**

```python
"""Integration tests for core daemon endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_returns_ok(self, client: TestClient):
        """Health endpoint returns running status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "version" in data
        assert "plugins" in data

    def test_health_includes_plugin_health(self, client: TestClient, isolated_registry, simple_plugin):
        """Health endpoint includes plugin health."""
        isolated_registry.register(simple_plugin)

        response = client.get("/health")
        data = response.json()

        assert "plugin_health" in data


class TestPluginsEndpoint:
    """Test /plugins endpoint."""

    def test_plugins_returns_list(self, client: TestClient):
        """Plugins endpoint returns plugin list."""
        response = client.get("/plugins")

        assert response.status_code == 200
        data = response.json()
        assert "plugins" in data
        assert isinstance(data["plugins"], list)


class TestShutdownEndpoint:
    """Test /shutdown endpoint."""

    def test_shutdown_returns_success(self, client: TestClient):
        """Shutdown endpoint initiates shutdown."""
        response = client.post("/shutdown")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestErrorHandling:
    """Test global error handling."""

    def test_404_for_unknown_route(self, client: TestClient):
        """Returns 404 for unknown routes."""
        response = client.get("/nonexistent/route")

        assert response.status_code == 404
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/integration/test_endpoints.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/integration/test_endpoints.py
git commit -m "test: add integration tests for core endpoints"
```

---

## Phase 3: Logging Improvements

### Task 3.1: Add Request Correlation IDs

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/skills_daemon/logging.py`
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/skills_daemon/main.py`

**Step 1: Add context variable for request ID**

Add to `logging.py` after imports:

```python
import contextvars
import uuid

# Context variable for request correlation
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    'request_id', default=None
)


def get_request_id() -> str | None:
    """Get current request ID from context."""
    return request_id_ctx.get()


def set_request_id(request_id: str) -> contextvars.Token:
    """Set request ID in context."""
    return request_id_ctx.set(request_id)


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())[:8]  # Short ID for readability
```

**Step 2: Update StructuredFormatter to include request_id**

In `logging.py`, update `StructuredFormatter.format()`:

```python
def format(self, record: logging.LogRecord) -> str:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
    }

    # Add request_id from context if available
    request_id = request_id_ctx.get()
    if request_id:
        entry["request_id"] = request_id

    # Add extra fields
    if hasattr(record, "event"):
        entry["event"] = record.event
    if hasattr(record, "context"):
        entry.update(record.context)

    # Add exception info if present
    if record.exc_info:
        entry["exception"] = self.formatException(record.exc_info)

    return json.dumps(entry)
```

**Step 3: Update request middleware in main.py**

Update the middleware in `main.py`:

```python
from .logging import logger, set_request_id, generate_request_id

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and update idle timeout."""
    # Generate and set request ID
    request_id = request.headers.get('X-Request-ID', generate_request_id())
    token = set_request_id(request_id)

    start = time.time()

    # Update last request time
    if lifecycle:
        lifecycle.touch()

    try:
        response = await call_next(request)

        duration_ms = (time.time() - start) * 1000
        logger.debug(
            "request",
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        # Reset context
        from .logging import request_id_ctx
        request_id_ctx.reset(token)
```

**Step 4: Test correlation IDs**

Run: `skills-daemon restart && curl -v http://127.0.0.1:9100/health 2>&1 | grep -i request-id`
Expected: `X-Request-ID` header in response

**Step 5: Commit**

```bash
git add skills_daemon/logging.py skills_daemon/main.py
git commit -m "feat: add request correlation IDs for tracing"
```

---

### Task 3.2: Add Slow Request Detection

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/skills_daemon/main.py`

**Step 1: Add slow request threshold**

Add constant at top of `main.py`:

```python
# Slow request threshold (1 second)
SLOW_REQUEST_THRESHOLD_MS = 1000
```

**Step 2: Update middleware to log slow requests**

In the request middleware, add slow request detection:

```python
duration_ms = (time.time() - start) * 1000

# Log at DEBUG level normally
logger.debug(
    "request",
    request_id=request_id,
    method=request.method,
    path=str(request.url.path),
    status=response.status_code,
    duration_ms=round(duration_ms, 2),
)

# Log slow requests at WARNING level
if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
    logger.warning(
        "slow_request",
        request_id=request_id,
        method=request.method,
        path=str(request.url.path),
        status=response.status_code,
        duration_ms=round(duration_ms, 2),
        threshold_ms=SLOW_REQUEST_THRESHOLD_MS,
    )
```

**Step 3: Commit**

```bash
git add skills_daemon/main.py
git commit -m "feat: add slow request detection and logging"
```

---

### Task 3.3: Add Configurable Log Level

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/skills_daemon/logging.py`

**Step 1: Update DaemonLogger to use config**

Update `DaemonLogger.__init__()`:

```python
def __init__(self, name: str = "skills-daemon"):
    from . import config

    self.logger = logging.getLogger(name)

    # Use log level from config/environment
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    self.logger.setLevel(log_level)

    self._queue_listener = None
    # ... rest of init
```

**Step 2: Test configurable log level**

Run: `SKILLS_DAEMON_LOG_LEVEL=DEBUG skills-daemon restart`
Expected: Debug logs appear in output

**Step 3: Commit**

```bash
git add skills_daemon/logging.py
git commit -m "feat: add configurable log level via environment"
```

---

## Phase 4: Self-Healing Capabilities

### Task 4.1: Add HTTP Retry Logic with Exponential Backoff

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/cli/skills_client.py`

**Step 1: Add retry function**

Add near top of `skills_client.py`:

```python
import time

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.5  # seconds


def request_with_retry(
    path: str,
    params: dict | None = None,
    method: str = "GET",
    retries: int = MAX_RETRIES,
) -> dict:
    """Make HTTP request with exponential backoff retry.

    Args:
        path: URL path (e.g., /health)
        params: Query params (GET) or JSON body (POST)
        method: HTTP method
        retries: Max retry attempts

    Returns:
        Response dict
    """
    last_error = None

    for attempt in range(retries):
        try:
            return request(path, params or {}, method)
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                wait_time = RETRY_BACKOFF_BASE * (2 ** attempt)
                print(f"{DIM}Retry {attempt + 1}/{retries} in {wait_time}s...{RESET}", file=sys.stderr)
                time.sleep(wait_time)

    # All retries failed
    return {
        "success": False,
        "error": f"Failed after {retries} attempts: {last_error}",
        "hint": "Check if daemon is running: skills-daemon status",
    }
```

**Step 2: Update main() to use retry**

In `main()`, replace direct `request()` calls with `request_with_retry()` for critical operations.

**Step 3: Commit**

```bash
git add cli/skills_client.py
git commit -m "feat: add HTTP retry with exponential backoff"
```

---

### Task 4.2: Add Systemd Service File for Auto-Restart

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/scripts/skills-daemon.service`

**Step 1: Create systemd service file**

```ini
# Skills Daemon systemd service
# Install: cp scripts/skills-daemon.service ~/.config/systemd/user/
# Enable: systemctl --user enable skills-daemon
# Start: systemctl --user start skills-daemon

[Unit]
Description=Skills Daemon for Claude Code
After=network.target

[Service]
Type=simple
ExecStart=%h/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/.venv/bin/python -m skills_daemon.main
Restart=on-failure
RestartSec=5
Environment=SKILLS_DAEMON_LOG_LEVEL=INFO

# Graceful shutdown
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=default.target
```

**Step 2: Create scripts directory**

```bash
mkdir -p /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/scripts
```

**Step 3: Commit**

```bash
git add scripts/skills-daemon.service
git commit -m "feat: add systemd service file for auto-restart"
```

---

### Task 4.3: Add Shutdown Timeout Protection

**Files:**
- Modify: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/skills_daemon/lifecycle.py`

**Step 1: Add timeout to shutdown callbacks**

Update `run_shutdown_callbacks()`:

```python
async def run_shutdown_callbacks(self) -> None:
    """Run all registered shutdown callbacks with timeout protection."""
    CALLBACK_TIMEOUT = 10  # seconds

    for callback in self._shutdown_callbacks:
        try:
            if asyncio.iscoroutinefunction(callback):
                await asyncio.wait_for(callback(), timeout=CALLBACK_TIMEOUT)
            else:
                callback()
        except asyncio.TimeoutError:
            logger.error(f"Shutdown callback timed out after {CALLBACK_TIMEOUT}s")
        except Exception as e:
            logger.error(f"Shutdown callback failed: {e}")
```

**Step 2: Commit**

```bash
git add skills_daemon/lifecycle.py
git commit -m "feat: add timeout protection for shutdown callbacks"
```

---

## Phase 5: Documentation

### Task 5.1: Create Developer Documentation

**Files:**
- Create: `/home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon/docs/development.md`

**Step 1: Write development.md**

```markdown
# Skills Daemon Developer Guide

## Architecture Overview

```
skills-daemon/
├── cli/                    # CLI entry points
│   ├── daemon_ctl.py       # Daemon management (start/stop/status)
│   └── skills_client.py    # Thin HTTP client for plugins
├── skills_daemon/          # Core package
│   ├── __init__.py         # Package + backward compat exports
│   ├── config.py           # Centralized configuration
│   ├── colors.py           # TTY-aware terminal colors
│   ├── main.py             # FastAPI app + plugin discovery
│   ├── lifecycle.py        # PID, signals, idle timeout
│   ├── logging.py          # Structured JSON logging
│   ├── formatters.py       # Output formatters
│   └── plugins/            # Plugin system
│       └── __init__.py     # SkillPlugin ABC + registry
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Shared fixtures
└── docs/                   # Documentation
```

## Configuration

All configuration via environment variables with `SKILLS_DAEMON_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILLS_DAEMON_HOST` | 127.0.0.1 | Bind address |
| `SKILLS_DAEMON_PORT` | 9100 | Port number |
| `SKILLS_DAEMON_TIMEOUT` | 1800 | Idle timeout (seconds) |
| `SKILLS_DAEMON_LOG_LEVEL` | INFO | Log level |
| `SKILLS_DAEMON_LOG_FILE` | /tmp/skills-daemon.log | Log file path |
| `SKILLS_DAEMON_PID_FILE` | /tmp/skills-daemon.pid | PID file path |

## Plugin Development

### Minimal Plugin

```python
from fastapi import APIRouter
from skills_daemon.plugins import SkillPlugin

class MyPlugin(SkillPlugin):
    @property
    def name(self) -> str:
        return "my-plugin"

    @property
    def router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/hello")
        async def hello():
            return {"message": "Hello!"}

        return router

# Plugin is auto-discovered from ~/.claude/plugins/**/skills_plugin/
```

### Plugin Lifecycle Hooks

```python
async def startup(self) -> None:
    """Called when daemon starts. Initialize resources."""
    self.db = await connect_database()

async def shutdown(self) -> None:
    """Called when daemon stops. Cleanup resources."""
    await self.db.close()

def health_check(self) -> dict:
    """Called by /health endpoint."""
    return {"status": "ok", "db_connected": self.db.is_connected}
```

## Testing

```bash
# Run all tests
.venv/bin/pytest

# Run with coverage
.venv/bin/pytest --cov --cov-report=html

# Run specific test file
.venv/bin/pytest tests/unit/test_config.py -v

# Run only unit tests
.venv/bin/pytest tests/unit/ -v
```

## Debugging

### Enable Debug Logging

```bash
SKILLS_DAEMON_LOG_LEVEL=DEBUG skills-daemon start
```

### Trace Requests

Every request gets a correlation ID:
- Logged in JSON as `request_id`
- Returned in response header `X-Request-ID`
- Pass your own via request header `X-Request-ID`

### Check Logs

```bash
# Tail logs
skills-daemon logs

# Or directly
tail -f /tmp/skills-daemon.log | jq
```

## Common Issues

### Daemon Won't Start

1. Check if already running: `skills-daemon status`
2. Kill stale process: `rm /tmp/skills-daemon.pid`
3. Check logs: `tail /tmp/skills-daemon.log`

### Plugin Not Loading

1. Verify plugin location: `~/.claude/plugins/**/skills_plugin/__init__.py`
2. Check plugin class name ends with `Plugin`
3. Restart daemon: `skills-daemon restart`

### Slow Requests

Requests >1s logged at WARNING level with `slow_request` event.
Check logs: `grep slow_request /tmp/skills-daemon.log`
```

**Step 2: Commit**

```bash
git add docs/development.md
git commit -m "docs: add developer guide"
```

---

## Phase 6: Final Verification

### Task 6.1: Run Full Test Suite

**Step 1: Run all tests with coverage**

```bash
cd /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon
.venv/bin/pytest --cov --cov-report=term-missing
```

Expected: All tests pass, coverage >80%

### Task 6.2: Verify Daemon Functionality

**Step 1: Restart daemon**

```bash
skills-daemon restart
```

**Step 2: Test health endpoint**

```bash
curl http://127.0.0.1:9100/health | jq
```

Expected: JSON response with status, version, plugins

**Step 3: Verify request correlation**

```bash
curl -v http://127.0.0.1:9100/health 2>&1 | grep -i x-request-id
```

Expected: X-Request-ID header present

### Task 6.3: Create Final Commit

```bash
git add -A
git commit -m "feat: professional refactor complete - tests, logging, self-healing"
```

---

## Summary

### Files Created
- `skills_daemon/config.py` - Centralized configuration
- `skills_daemon/colors.py` - TTY-aware colors
- `tests/conftest.py` - Pytest fixtures
- `tests/unit/test_config.py` - Config tests
- `tests/unit/test_colors.py` - Colors tests
- `tests/unit/test_registry.py` - Registry tests
- `tests/integration/test_endpoints.py` - Endpoint tests
- `scripts/skills-daemon.service` - Systemd service
- `docs/development.md` - Developer guide

### Files Modified
- `pyproject.toml` - Fixed entry points, added pytest config
- `skills_daemon/__init__.py` - Use config module
- `skills_daemon/logging.py` - Request correlation, configurable level
- `skills_daemon/main.py` - Correlation IDs, slow request detection
- `skills_daemon/formatters.py` - TTY-aware colors
- `skills_daemon/lifecycle.py` - Shutdown timeout protection
- `cli/daemon_ctl.py` - Shared colors
- `cli/skills_client.py` - Shared colors, retry logic

### Improvements
- ✅ Centralized configuration with env vars
- ✅ TTY-aware color handling (no broken piped output)
- ✅ Request correlation IDs for tracing
- ✅ Slow request detection and logging
- ✅ HTTP retry with exponential backoff
- ✅ Shutdown timeout protection
- ✅ Systemd service for auto-restart
- ✅ Full pytest infrastructure
- ✅ Developer documentation
