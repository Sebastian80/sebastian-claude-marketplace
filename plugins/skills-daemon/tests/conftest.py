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
