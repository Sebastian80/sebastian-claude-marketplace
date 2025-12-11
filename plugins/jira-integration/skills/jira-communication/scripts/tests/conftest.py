"""Pytest configuration for Jira plugin tests.

This file configures pytest options and fixtures. Shared helper functions
are in helpers.py to avoid import issues.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Add tests directory to path for helpers import
sys.path.insert(0, str(Path(__file__).parent))


# ==============================================================================
# Pytest Hooks
# ==============================================================================

def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-write-tests",
        action="store_true",
        default=False,
        help="Run tests that modify Jira data (create issues, comments, etc.)"
    )


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "write_test: marks tests that modify Jira data"
    )


def pytest_collection_modifyitems(config, items):
    """Skip write tests unless --run-write-tests is passed."""
    if config.getoption("--run-write-tests"):
        # Don't skip write tests
        return

    skip_write = pytest.mark.skip(reason="Write test - run with --run-write-tests")
    for item in items:
        if "write_test" in item.keywords:
            item.add_marker(skip_write)


@pytest.fixture(scope="session", autouse=True)
def ensure_daemon_running():
    """Ensure skills daemon is running before tests."""
    result = subprocess.run(
        ["skills-client", "health"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0 or "running" not in result.stdout:
        pytest.skip("Skills daemon not running. Start with: skills-daemon start")
