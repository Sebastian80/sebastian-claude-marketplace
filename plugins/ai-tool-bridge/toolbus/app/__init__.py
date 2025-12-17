"""
App - FastAPI application and HTTP layer.

Provides:
- Application factory for creating configured FastAPI instances
- Core routes (health, status, plugin management)
- Middleware (activity tracking, logging, error handling)

Example:
    from toolbus.app import create_app
    from toolbus.config import BridgeConfig

    config = BridgeConfig()
    app = create_app(config)

    # Run with uvicorn
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
"""

from .factory import create_app
from .middleware import ActivityMiddleware, ErrorMiddleware, LoggingMiddleware
from .routes import router as core_router

__all__ = [
    "create_app",
    "core_router",
    "ActivityMiddleware",
    "ErrorMiddleware",
    "LoggingMiddleware",
]
