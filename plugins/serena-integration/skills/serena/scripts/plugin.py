"""
Serena plugin for AI Tool Bridge.

Implements PluginProtocol and manages SerenaConnector lifecycle.
"""

import logging
from typing import Any

from fastapi import APIRouter

from .connector import SerenaConnector
from .routes import create_router

logger = logging.getLogger("serena_plugin")


class SerenaPlugin:
    """Serena semantic code navigation plugin."""

    def __init__(self, bridge_context: dict[str, Any] | None = None) -> None:
        """Initialize Serena plugin.

        Args:
            bridge_context: Optional bridge services (connector_registry)
        """
        self._connector_registry = None
        self._connector = SerenaConnector()

        if bridge_context:
            self._connector_registry = bridge_context.get("connector_registry")

    @property
    def name(self) -> str:
        return "serena"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Semantic code navigation via LSP (30+ languages)"

    @property
    def router(self) -> APIRouter:
        return create_router()

    @property
    def connector(self) -> SerenaConnector:
        return self._connector

    async def startup(self) -> None:
        """Initialize plugin and register connector."""
        if self._connector_registry:
            try:
                self._connector_registry.register(self._connector)
                logger.info("Serena: connector registered")
            except ValueError:
                pass  # Already registered

        try:
            await self._connector.connect()
            logger.info("Serena: connected")
        except Exception as e:
            logger.warning(f"Serena: connection failed: {e}")

    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        await self._connector.disconnect()

        if self._connector_registry:
            try:
                self._connector_registry.unregister("serena")
            except Exception:
                pass

        logger.info("Serena: shutdown")

    async def health_check(self) -> dict[str, Any]:
        """Check connection health via connector."""
        status = self._connector.status()
        return {
            "status": "healthy" if status["healthy"] else "unhealthy",
            "circuit_state": status["circuit_state"],
            "failure_count": status.get("failure_count", 0),
            "can_reconnect": status["circuit_state"] != "open",
        }
