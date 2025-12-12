"""
Jira plugin for AI Tool Bridge.

Implements PluginProtocol and manages JiraConnector lifecycle.
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter

from .connector import JiraConnector
from .routes import create_router

logger = logging.getLogger("jira_plugin")


class JiraPlugin:
    """Jira issue tracking and workflow automation plugin."""

    def __init__(self, bridge_context: dict[str, Any] | None = None) -> None:
        self._connector_registry = None
        self._connector = JiraConnector()

        if bridge_context:
            self._connector_registry = bridge_context.get("connector_registry")

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

    @property
    def connector(self) -> JiraConnector:
        return self._connector

    async def startup(self) -> None:
        """Initialize plugin and register connector."""
        if self._connector_registry:
            try:
                self._connector_registry.register(self._connector)
                logger.info("Jira: connector registered")
            except ValueError:
                pass  # Already registered

        try:
            await self._connector.connect()
            logger.info("Jira: connected")
        except Exception as e:
            logger.warning(f"Jira: connection failed: {e}")

    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        await self._connector.disconnect()

        if self._connector_registry:
            try:
                self._connector_registry.unregister("jira")
            except Exception:
                pass

        logger.info("Jira: shutdown")

    def health_check(self) -> dict[str, Any]:
        """Check connection health via connector."""
        status = self._connector.status()
        return {
            "status": "connected" if status["healthy"] else "not_connected",
            "circuit_state": status["circuit_state"],
            "failure_count": status.get("failure_count", 0),
            "can_reconnect": status["circuit_state"] != "open",
        }
