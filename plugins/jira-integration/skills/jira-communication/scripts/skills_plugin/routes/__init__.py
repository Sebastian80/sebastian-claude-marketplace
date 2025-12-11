"""
Combined router for all Jira endpoints.

This module imports and combines all route modules into a single router.
Each module handles a specific domain of Jira functionality.

Route modules:
- health: Connection health check
- issues: Issue CRUD operations
- search: JQL search
- workflow: Transitions and workflows
- comments: Issue comments
- links: Issue links and web links
- user: Current user info
- attachments: File attachments
- watchers: Issue watchers
- worklogs: Time tracking
- projects: Project listing
- components: Project components
- versions: Project versions
- priorities: Priority levels
- statuses: Status values
- fields: Field metadata
- filters: Saved JQL filters
"""

from fastapi import APIRouter

from .health import router as health_router
from .issues import router as issues_router
from .search import router as search_router
from .workflow import router as workflow_router
from .comments import router as comments_router
from .links import router as links_router
from .user import router as user_router
from .attachments import router as attachments_router
from .watchers import router as watchers_router
from .worklogs import router as worklogs_router
from .projects import router as projects_router
from .components import router as components_router
from .versions import router as versions_router
from .priorities import router as priorities_router
from .statuses import router as statuses_router
from .fields import router as fields_router
from .filters import router as filters_router


def create_router() -> APIRouter:
    """Create and return the combined router with all endpoints."""
    router = APIRouter()

    # Health check (first for quick access)
    router.include_router(health_router)        # /health

    # Core issue operations
    router.include_router(issues_router)        # /issue/{key}, /create
    router.include_router(search_router)        # /search

    # Issue details
    router.include_router(workflow_router)      # /transitions, /transition, /workflows
    router.include_router(comments_router)      # /comment, /comments
    router.include_router(links_router)         # /links, /linktypes, /link, /weblink
    router.include_router(attachments_router)   # /attachments, /attachment
    router.include_router(watchers_router)      # /watchers, /watcher
    router.include_router(worklogs_router)      # /worklogs, /worklog

    # User info
    router.include_router(user_router)          # /user, /user/me

    # Project metadata
    router.include_router(projects_router)      # /projects, /project
    router.include_router(components_router)    # /components, /component
    router.include_router(versions_router)      # /versions, /version

    # System metadata
    router.include_router(priorities_router)    # /priorities
    router.include_router(statuses_router)      # /statuses, /status
    router.include_router(fields_router)        # /fields
    router.include_router(filters_router)       # /filters, /filter

    return router
