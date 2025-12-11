"""Pytest configuration for Jira plugin tests."""

import subprocess
import pytest


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
