"""
Jira plugin for skills daemon.

Provides Jira issue tracking and workflow automation via persistent connection.

Features:
- Persistent connection with auto-reconnect
- Retry logic for transient failures
- Health monitoring and self-healing
- Multiple output formats (human, json, ai, markdown)
"""

import asyncio
import sys
import time
import logging
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

# Import SkillPlugin from skills-daemon (sibling plugin in plugins/)
SKILLS_DAEMON = Path(__file__).parent.parent.parent.parent.parent.parent / "skills-daemon"
if str(SKILLS_DAEMON) not in sys.path:
    sys.path.insert(0, str(SKILLS_DAEMON))

from skills_daemon.plugins import SkillPlugin
from skills_daemon.formatters import format_response, get_formatter

# Add lib/ to path for shared Jira utilities
LIB_PATH = Path(__file__).parent.parent
if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))

# Import and auto-register Jira formatters
from skills_plugin.formatters import register_jira_formatters
register_jira_formatters()

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 0.5
CONNECTION_CHECK_INTERVAL = 300  # 5 minutes

# Lazy imports - avoid loading heavy dependencies until needed
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
                        # Force reconnect on connection errors
                        reset_client()
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator


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
        # Lightweight check - get current user
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
        # Connection dead, reset and reconnect
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


def success_response(data: Any) -> dict:
    """Standard success response (JSON)."""
    return {"success": True, "data": data}


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
    """
    if fmt == "json":
        return success_response(data)

    # Use plugin formatter if available, else base formatter
    formatted = format_response(data, fmt, plugin="jira", data_type=data_type)
    return PlainTextResponse(content=formatted)


def formatted_error(message: str, hint: str | None = None, fmt: str = "json", status: int = 400):
    """Return error in requested format."""
    if fmt == "json":
        return error_response(message, hint, status)

    formatter = get_formatter(fmt)
    formatted = formatter.format_error(message, hint)
    return PlainTextResponse(content=formatted, status_code=status)


class JiraPlugin(SkillPlugin):
    """Jira issue tracking and workflow automation plugin."""

    @property
    def name(self) -> str:
        return "jira"

    @property
    def description(self) -> str:
        return "Jira issue tracking and workflow automation"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def router(self) -> APIRouter:
        router = APIRouter()

        # ═══════════════════════════════════════════════════════════════════
        # CORE: Issue Operations
        # ═══════════════════════════════════════════════════════════════════

        @router.get("/issue/{key}")
        async def get_issue(
            key: str,
            fields: str | None = Query(None, description="Comma-separated fields"),
            expand: str | None = Query(None, description="Fields to expand"),
            format: str = Query("json", description="Output format: json, human, ai, markdown"),
        ):
            """Get issue details."""
            client = await get_client()
            params = {}
            if fields:
                params['fields'] = fields
            if expand:
                params['expand'] = expand

            try:
                issue = client.issue(key, **params)
                return formatted_response(issue, format, "issue")
            except Exception as e:
                if "does not exist" in str(e).lower() or "404" in str(e):
                    return formatted_error(f"Issue {key} not found", fmt=format, status=404)
                raise HTTPException(status_code=500, detail=str(e))

        @router.patch("/issue/{key}")
        async def update_issue(
            key: str,
            summary: str | None = Query(None),
            priority: str | None = Query(None),
            labels: str | None = Query(None, description="Comma-separated labels"),
            assignee: str | None = Query(None),
        ):
            """Update issue fields."""
            client = await get_client()
            update_fields = {}

            if summary:
                update_fields['summary'] = summary
            if priority:
                update_fields['priority'] = {'name': priority}
            if labels:
                update_fields['labels'] = [l.strip() for l in labels.split(',')]
            if assignee:
                # Detect if email or username
                if '@' in assignee:
                    update_fields['assignee'] = {'emailAddress': assignee}
                else:
                    update_fields['assignee'] = {'name': assignee}

            if not update_fields:
                return error_response("No fields specified to update")

            try:
                client.update_issue_field(key, update_fields)
                return success_response({"key": key, "updated": list(update_fields.keys())})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ═══════════════════════════════════════════════════════════════════
        # CORE: Search
        # ═══════════════════════════════════════════════════════════════════

        @router.get("/search")
        async def search(
            jql: str,
            max_results: int = Query(50, alias="maxResults"),
            fields: str = Query("key,summary,status,assignee,priority"),
            format: str = Query("json", description="Output format: json, human, ai, markdown"),
        ):
            """Search issues using JQL."""
            client = await get_client()
            field_list = [f.strip() for f in fields.split(',')]

            try:
                results = client.jql(jql, limit=max_results, fields=field_list)
                return formatted_response(results.get('issues', []), format, "search")
            except Exception as e:
                return formatted_error(f"JQL error: {e}", hint="Check JQL syntax", fmt=format)

        # ═══════════════════════════════════════════════════════════════════
        # CORE: Transitions
        # ═══════════════════════════════════════════════════════════════════

        @router.get("/transitions/{key}")
        async def list_transitions(
            key: str,
            format: str = Query("json", description="Output format: json, human, ai, markdown"),
        ):
            """List available transitions for an issue."""
            client = await get_client()
            try:
                transitions = client.get_issue_transitions(key)
                return formatted_response(transitions, format, "transitions")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/transition/{key}")
        async def do_transition(
            key: str,
            target: str,
            comment: bool = Query(False, description="Add transition trail as comment"),
            dry_run: bool = Query(False, alias="dryRun"),
        ):
            """Transition issue to target state (smart multi-step)."""
            client = await get_client()
            store = get_workflow_store_sync()

            try:
                from lib.workflow import smart_transition
                executed = smart_transition(
                    client=client,
                    issue_key=key,
                    target_state=target,
                    store=store,
                    add_comment=comment,
                    dry_run=dry_run,
                )

                return success_response({
                    "key": key,
                    "dry_run": dry_run,
                    "transitions": [{"id": t.id, "name": t.name, "to": t.to} for t in executed],
                    "final_state": executed[-1].to if executed else target,
                })
            except Exception as e:
                error_msg = str(e)
                if "path" in error_msg.lower():
                    return error_response(f"No path to '{target}'", hint="Check available states")
                raise HTTPException(status_code=500, detail=error_msg)

        # ═══════════════════════════════════════════════════════════════════
        # COMMON: Comments
        # ═══════════════════════════════════════════════════════════════════

        @router.post("/comment/{key}")
        async def add_comment(key: str, text: str):
            """Add comment to issue (use Jira wiki markup, not Markdown)."""
            client = await get_client()
            try:
                result = client.issue_add_comment(key, text)
                return success_response(result)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/comments/{key}")
        async def list_comments(
            key: str,
            limit: int = Query(10),
            format: str = Query("json", description="Output format: json, human, ai, markdown"),
        ):
            """List comments on issue."""
            client = await get_client()
            try:
                issue = client.issue(key, fields='comment')
                comments = issue.get('fields', {}).get('comment', {}).get('comments', [])
                return formatted_response(list(reversed(comments))[:limit], format, "comments")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ═══════════════════════════════════════════════════════════════════
        # COMMON: Create
        # ═══════════════════════════════════════════════════════════════════

        @router.post("/create")
        async def create_issue(
            project: str,
            summary: str,
            issue_type: str = Query(..., alias="type"),
            description: str | None = Query(None),
            priority: str | None = Query(None),
            labels: str | None = Query(None),
            assignee: str | None = Query(None),
        ):
            """Create new issue."""
            client = await get_client()
            fields = {
                'project': {'key': project},
                'summary': summary,
                'issuetype': {'name': issue_type},
            }
            if description:
                fields['description'] = description
            if priority:
                fields['priority'] = {'name': priority}
            if labels:
                fields['labels'] = [l.strip() for l in labels.split(',')]
            if assignee:
                if '@' in assignee:
                    fields['assignee'] = {'emailAddress': assignee}
                else:
                    fields['assignee'] = {'name': assignee}

            try:
                result = client.create_issue(fields=fields)
                return success_response(result)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ═══════════════════════════════════════════════════════════════════
        # UTILITY: Links
        # ═══════════════════════════════════════════════════════════════════

        @router.post("/link")
        async def create_link(
            from_key: str = Query(..., alias="from"),
            to_key: str = Query(..., alias="to"),
            link_type: str = Query(..., alias="type"),
        ):
            """Create link between two issues."""
            client = await get_client()
            try:
                # atlassian-python-api 4.x uses data dict instead of kwargs
                link_data = {
                    "type": {"name": link_type},
                    "inwardIssue": {"key": to_key},
                    "outwardIssue": {"key": from_key},
                }
                client.create_issue_link(link_data)
                return success_response({"from": from_key, "to": to_key, "type": link_type})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/link/types")
        async def list_link_types():
            """List available issue link types."""
            client = await get_client()
            try:
                types = client.get_issue_link_types()
                return success_response(types)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ═══════════════════════════════════════════════════════════════════
        # UTILITY: Web Links (Remote Links)
        # ═══════════════════════════════════════════════════════════════════

        @router.post("/weblink/{key}")
        async def add_weblink(
            key: str,
            url: str,
            title: str | None = Query(None),
        ):
            """Add web link (remote link) to issue."""
            client = await get_client()
            link_title = title or url

            try:
                link_object = {"url": url, "title": link_title}
                endpoint = f"rest/api/2/issue/{key}/remotelink"
                response = client._session.post(
                    f"{client.url}/{endpoint}",
                    json={"object": link_object}
                )
                response.raise_for_status()
                result = response.json()
                return success_response({
                    "key": key,
                    "url": url,
                    "title": link_title,
                    "id": result.get('id'),
                })
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/weblinks/{key}")
        async def list_weblinks(key: str):
            """List web links on issue."""
            client = await get_client()
            try:
                endpoint = f"rest/api/2/issue/{key}/remotelink"
                response = client._session.get(f"{client.url}/{endpoint}")
                response.raise_for_status()
                links = response.json()
                return success_response(links)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.delete("/weblink/{key}/{link_id}")
        async def remove_weblink(key: str, link_id: str):
            """Remove web link from issue."""
            client = await get_client()
            try:
                endpoint = f"rest/api/2/issue/{key}/remotelink/{link_id}"
                response = client._session.delete(f"{client.url}/{endpoint}")
                response.raise_for_status()
                return success_response({"key": key, "link_id": link_id, "removed": True})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ═══════════════════════════════════════════════════════════════════
        # UTILITY: Workflows
        # ═══════════════════════════════════════════════════════════════════

        @router.get("/workflows")
        async def list_workflows():
            """List cached workflows."""
            store = get_workflow_store_sync()
            types = store.list_types()
            return success_response(types)

        @router.get("/workflow/{issue_type:path}")
        async def get_workflow(issue_type: str):
            """Get cached workflow for issue type."""
            store = get_workflow_store_sync()
            graph = store.get(issue_type)
            if graph is None:
                return error_response(
                    f"Workflow for '{issue_type}' not cached",
                    hint="Use 'jira workflow discover ISSUE-KEY' to cache",
                    status=404,
                )
            return success_response(graph.to_dict())

        @router.post("/workflow/discover/{key}")
        async def discover_workflow(key: str):
            """Discover and cache workflow from an issue."""
            client = await get_client()
            store = get_workflow_store_sync()

            try:
                from lib.workflow import discover_workflow
                graph = discover_workflow(client, key, verbose=False)
                store.save(graph)
                return success_response({
                    "issue_type": graph.issue_type,
                    "states": len(graph.all_states()),
                    "cached": True,
                })
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ═══════════════════════════════════════════════════════════════════
        # UTILITY: User
        # ═══════════════════════════════════════════════════════════════════

        @router.get("/user/me")
        async def get_current_user():
            """Get current authenticated user."""
            client = await get_client()
            try:
                user = client.myself()
                return success_response(user)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        return router

    async def startup(self) -> None:
        """Load workflow cache on startup."""
        global workflow_store
        try:
            from lib.workflow import WorkflowStore
            workflow_store = WorkflowStore()
            logger.info("Jira: workflow store initialized")
        except Exception as e:
            logger.debug(f"Jira: workflow store init deferred: {e}")

    async def connect(self) -> None:
        """Establish Jira connection on daemon startup.

        Called automatically by daemon after startup().
        Connection failures are logged but don't prevent daemon from running.
        """
        global jira_client, last_health_check
        try:
            # Force fresh connection
            jira_client = None
            get_client_sync()
            logger.info("Jira: connected to server")
        except Exception as e:
            logger.warning(f"Jira: connection failed (will retry on first request): {e}")
            raise  # Let daemon know connection failed

    async def reconnect(self) -> None:
        """Re-establish connection with exponential backoff.

        Called by daemon or health checks when connection is lost.
        """
        global jira_client

        # Reset existing connection
        jira_client = None

        # Exponential backoff: 0.5s, 1s, 2s
        delays = [0.5, 1.0, 2.0]
        last_error = None

        for attempt, delay in enumerate(delays, 1):
            try:
                await asyncio.sleep(delay)
                await self.connect()
                logger.info(f"Jira: reconnected after {attempt} attempts")
                return
            except Exception as e:
                last_error = e
                logger.warning(f"Jira: reconnect attempt {attempt}/{len(delays)} failed: {e}")

        # All retries failed
        logger.error(f"Jira: reconnection failed after {len(delays)} attempts: {last_error}")
        raise last_error if last_error else RuntimeError("Reconnection failed")

    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        global jira_client
        if jira_client:
            logger.info("Jira: closing connection")
        jira_client = None

    def health_check(self) -> dict[str, Any]:
        """Check Jira connection health with detailed status."""
        global jira_client, workflow_store, last_health_check

        result = {
            "status": "not_connected",
            "workflows_cached": 0,
            "last_check_age_seconds": None,
            "can_reconnect": True,
        }

        if jira_client is None:
            return result

        # Check connection health
        try:
            jira_client.myself()
            result["status"] = "connected"
            result["last_check_age_seconds"] = int(time.time() - last_health_check)
        except Exception as e:
            result["status"] = "connection_error"
            result["error"] = str(e)[:100]
            # Try to reconnect
            reset_client()
            try:
                get_client_sync()
                result["status"] = "reconnected"
            except Exception:
                result["can_reconnect"] = False

        if workflow_store:
            try:
                result["workflows_cached"] = len(workflow_store.list_types())
            except Exception:
                pass

        return result
