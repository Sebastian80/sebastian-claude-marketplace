"""
Standard response helpers for Serena routes.
"""

from typing import Any, Optional

from fastapi.responses import JSONResponse


def success_response(data: Any) -> dict:
    """Standard success response."""
    return {"success": True, "data": data}


def error_response(message: str, hint: Optional[str] = None) -> JSONResponse:
    """Standard error response."""
    content = {"success": False, "error": message}
    if hint:
        content["hint"] = hint
    return JSONResponse(status_code=400, content=content)
