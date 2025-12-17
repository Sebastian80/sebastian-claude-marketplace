"""Shared test fixtures."""

import tempfile
from pathlib import Path

import pytest

from toolbus.config import BridgeConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def config(temp_dir):
    """Create a test configuration with temp directory."""
    return BridgeConfig(
        host="127.0.0.1",
        port=19100,  # Different port for tests
        idle_timeout=60,
        runtime_dir=temp_dir,
    )
