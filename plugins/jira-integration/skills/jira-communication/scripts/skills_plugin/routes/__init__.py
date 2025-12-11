"""
Combined router for all Jira endpoints.

Import and combine all route modules into a single router.
"""

from fastapi import APIRouter

from .issues import router as issues_router
from .search import router as search_router
from .workflow import router as workflow_router
from .comments import router as comments_router
from .links import router as links_router
from .user import router as user_router


def create_router() -> APIRouter:
    """Create and return the combined router with all endpoints."""
    router = APIRouter()

    # Include all route modules
    router.include_router(issues_router)      # /issue/{key}, /create
    router.include_router(search_router)      # /search
    router.include_router(workflow_router)    # /transitions, /transition, /workflows
    router.include_router(comments_router)    # /comment, /comments
    router.include_router(links_router)       # /link, /weblink
    router.include_router(user_router)        # /user/me

    return router
