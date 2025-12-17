"""
Combined router for all Serena endpoints.

This module imports and combines all route modules into a single router.
Each module handles a specific domain of Serena functionality.

Route modules:
- help: CLI help documentation
- status: Project status and activation
- find: Symbol finding and references
- search: Regex search and recipes
- memory: Memory management
- edit: Code editing
- onboarding: Project onboarding
"""

from fastapi import APIRouter

from .help import router as help_router
from .status import router as status_router
from .find import router as find_router
from .search import router as search_router
from .memory import router as memory_router
from .edit import router as edit_router
from .onboarding import router as onboarding_router


def create_router() -> APIRouter:
    """Create and return the combined router with all endpoints."""
    router = APIRouter()

    # Help (first for quick access)
    router.include_router(help_router)          # /help

    # Status and activation
    router.include_router(status_router)        # /status, /activate

    # Symbol operations
    router.include_router(find_router)          # /find, /refs, /overview

    # Search operations
    router.include_router(search_router)        # /search, /recipe, /tools

    # Memory management
    router.include_router(memory_router)        # /memory/*

    # Code editing
    router.include_router(edit_router)          # /edit/*

    # Onboarding
    router.include_router(onboarding_router)    # /check_onboarding, /onboarding, /init_memories

    return router
