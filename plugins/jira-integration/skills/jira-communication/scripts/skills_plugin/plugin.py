"""
Jira plugin class.

Thin wrapper that:
- Implements SkillPlugin interface
- Wires together routes from routes/
- Manages lifecycle (startup, connect, shutdown)
- Provides health checks
"""

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter

from skills_daemon.plugins import SkillPlugin

from .routes import create_router
from . import client

logger = logging.getLogger("jira_plugin")


class JiraPlugin(SkillPlugin):
    """Jira issue tracking and workflow automation plugin.

    Provides:
    - Issue CRUD operations
    - JQL search
    - Smart workflow transitions
    - Comments and links
    - Persistent connection with auto-reconnect
    """

    @property
    def name(self) -> str:
        return "jira"

    @property
    def description(self) -> str:
        return "Jira issue tracking and workflow automation"

    @property
    def version(self) -> str:
        return "1.1.0"

    @property
    def router(self) -> APIRouter:
        return create_router()

    async def startup(self) -> None:
        """Load workflow cache on startup."""
        try:
            from lib.workflow import WorkflowStore
            client.workflow_store = WorkflowStore()
            logger.info("Jira: workflow store initialized")
        except Exception as e:
            logger.debug(f"Jira: workflow store init deferred: {e}")

    async def connect(self) -> None:
        """Establish Jira connection on daemon startup.

        Called automatically by daemon after startup().
        Connection failures are logged but don't prevent daemon from running.
        """
        try:
            client.jira_client = None
            client.get_client_sync()
            logger.info("Jira: connected to server")
        except Exception as e:
            logger.warning(f"Jira: connection failed (will retry on first request): {e}")
            raise

    async def reconnect(self) -> None:
        """Re-establish connection with exponential backoff.

        Called by daemon or health checks when connection is lost.
        """
        client.jira_client = None

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

        logger.error(f"Jira: reconnection failed after {len(delays)} attempts: {last_error}")
        raise last_error if last_error else RuntimeError("Reconnection failed")

    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        if client.jira_client:
            logger.info("Jira: closing connection")
        client.jira_client = None

    def health_check(self) -> dict[str, Any]:
        """Check Jira connection health with detailed status."""
        result = {
            "status": "not_connected",
            "workflows_cached": 0,
            "last_check_age_seconds": None,
            "can_reconnect": True,
        }

        if client.jira_client is None:
            return result

        try:
            client.jira_client.myself()
            result["status"] = "connected"
            result["last_check_age_seconds"] = int(time.time() - client.last_health_check)
        except Exception as e:
            result["status"] = "connection_error"
            result["error"] = str(e)[:100]
            client.reset_client()
            try:
                client.get_client_sync()
                result["status"] = "reconnected"
            except Exception:
                result["can_reconnect"] = False

        if client.workflow_store:
            try:
                result["workflows_cached"] = len(client.workflow_store.list_types())
            except Exception:
                pass

        return result
