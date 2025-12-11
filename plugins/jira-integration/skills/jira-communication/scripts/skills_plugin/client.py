"""
Jira client connection management.

Handles:
- Persistent connection with auto-reconnect
- Retry logic for transient failures
- Health monitoring
- Response formatting helpers
"""

import logging
import time
from functools import wraps
from typing import Any, Callable

from fastapi import HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from skills_daemon.formatters import format_response, get_formatter

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 0.5
CONNECTION_CHECK_INTERVAL = 300  # 5 minutes

# Module state
Jira = None
jira_client = None
workflow_store = None
last_health_check = 0
logger = logging.getLogger("jira_plugin")


def is_connection_error(e: Exception) -> bool:
    """Check if exception indicates a connection problem."""
    error_str = str(e).lower()
    return any(x in error_str for x in [
        "connection", "timeout", "refused", "reset", "broken pipe",
        "network", "unavailable", "socket", "eof"
    ])


def reset_client():
    """Reset client to force reconnection."""
    global jira_client
    jira_client = None


def check_connection() -> bool:
    """Verify Jira connection is alive."""
    global last_health_check

    if jira_client is None:
        return False

    now = time.time()
    if now - last_health_check < CONNECTION_CHECK_INTERVAL:
        return True  # Skip check if recently verified

    try:
        jira_client.myself()
        last_health_check = now
        return True
    except Exception as e:
        logger.warning(f"Connection check failed: {e}")
        reset_client()
        return False


def get_client_sync():
    """Get or create persistent Jira client with auto-reconnect."""
    global Jira, jira_client, last_health_check

    # Check existing connection
    if jira_client is not None:
        if check_connection():
            return jira_client
        jira_client = None

    if Jira is None:
        try:
            from atlassian import Jira as JiraClass
            Jira = JiraClass
        except ImportError as e:
            raise HTTPException(
                status_code=503,
                detail=f"atlassian-python-api not installed: {e}",
            )

    if jira_client is None:
        try:
            from lib.client import get_jira_client
            jira_client = get_jira_client()
            last_health_check = time.time()
            logger.info("Jira client connected")
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to Jira: {e}",
            )

    return jira_client


async def get_client():
    """Get or create persistent Jira client (async wrapper)."""
    return get_client_sync()


def get_workflow_store_sync():
    """Get workflow store (lazy init)."""
    global workflow_store
    if workflow_store is None:
        from lib.workflow import WorkflowStore
        workflow_store = WorkflowStore()
    return workflow_store


def with_retry(retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """Decorator for retrying operations on transient failures."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if is_connection_error(e) and attempt < retries - 1:
                        logger.warning(f"Retry {attempt + 1}/{retries} after error: {e}")
                        time.sleep(delay)
                        reset_client()
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# Response Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def success_response(data: Any) -> JSONResponse:
    """Standard success response (JSON).

    Returns JSONResponse for proper JSON serialization (true/false not True/False).
    """
    return JSONResponse(content={"success": True, "data": data})


def error_response(message: str, hint: str | None = None, status: int = 400) -> JSONResponse:
    """Standard error response."""
    content = {"success": False, "error": message}
    if hint:
        content["hint"] = hint
    return JSONResponse(status_code=status, content=content)


def formatted_response(data: Any, fmt: str, data_type: str | None = None):
    """Return response in requested format.

    Args:
        data: The data to format
        fmt: Format name (human, json, ai, markdown)
        data_type: Jira data type (issue, search, transitions, comments)

    Returns:
        JSONResponse for json format, PlainTextResponse for others.
    """
    if fmt == "json":
        return JSONResponse(content={"success": True, "data": data})

    formatted = format_response(data, fmt, plugin="jira", data_type=data_type)
    return PlainTextResponse(content=formatted)


def formatted_error(message: str, hint: str | None = None, fmt: str = "json", status: int = 400):
    """Return error in requested format."""
    if fmt == "json":
        return error_response(message, hint, status)

    formatter = get_formatter(fmt)
    formatted = formatter.format_error(message, hint)
    return PlainTextResponse(content=formatted, status_code=status)
