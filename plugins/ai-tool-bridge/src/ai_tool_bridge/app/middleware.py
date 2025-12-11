"""
Middleware - Request processing and activity tracking.

Provides:
- Activity tracking for idle shutdown
- Request logging
- Error handling
"""

import time
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class ActivityMiddleware(BaseHTTPMiddleware):
    """Tracks request activity for idle monitoring.

    Calls a touch callback on each request to reset the idle timer.

    Example:
        app.add_middleware(
            ActivityMiddleware,
            on_activity=idle_monitor.touch,
        )
    """

    def __init__(self, app, on_activity: Callable[[], None] | None = None) -> None:
        super().__init__(app)
        self.on_activity = on_activity

    async def dispatch(self, request: Request, call_next) -> Response:
        # Record activity
        if self.on_activity:
            self.on_activity()

        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs request/response details.

    Logs method, path, status code, and duration.
    Excludes health check endpoints from verbose logging.
    """

    QUIET_PATHS = {"/health", "/healthz", "/ready", "/metrics"}

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000

        # Skip verbose logging for health checks
        if request.url.path not in self.QUIET_PATHS:
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        return response


class ErrorMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns JSON errors.

    Prevents stack traces from leaking to clients while
    logging full details server-side.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(
                "unhandled_error",
                method=request.method,
                path=request.url.path,
                error=str(e),
            )

            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred",
                },
            )
