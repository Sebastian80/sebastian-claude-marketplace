"""
Response formatting utilities.

Handles JSON and text formatting for API responses.
"""

from typing import Any

from fastapi.responses import JSONResponse, PlainTextResponse

from .formatters import formatter_registry


def success(data: Any) -> JSONResponse:
    """Standard success response."""
    return JSONResponse(content={"success": True, "data": data})


def error(message: str, hint: str | None = None, status: int = 400) -> JSONResponse:
    """Standard error response."""
    content = {"success": False, "error": message}
    if hint:
        content["hint"] = hint
    return JSONResponse(status_code=status, content=content)


def formatted(data: Any, fmt: str, data_type: str | None = None):
    """Return response in requested format."""
    if fmt == "json":
        return JSONResponse(content={"success": True, "data": data})

    formatter = formatter_registry.get(fmt, plugin="jira", data_type=data_type)
    if formatter is None:
        formatter = formatter_registry.get(fmt)

    if formatter is None:
        return JSONResponse(content={"success": True, "data": data})

    return PlainTextResponse(content=formatter.format(data))


def formatted_error(message: str, hint: str | None = None, fmt: str = "json", status: int = 400):
    """Return error in requested format."""
    if fmt == "json":
        return error(message, hint, status)

    formatter = formatter_registry.get(fmt)
    if formatter is None:
        return error(message, hint, status)

    return PlainTextResponse(content=formatter.format_error(message, hint), status_code=status)
