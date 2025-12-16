"""
Serena plugin for AI Tool Bridge.

Provides semantic code navigation via Serena MCP server.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger("serena_plugin")

# Add scripts dir to path for connector import
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Add serena_cli to path
SERENA_SCRIPTS = Path(__file__).parent.parent
if str(SERENA_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SERENA_SCRIPTS))

# Import connector after path setup
from connector import SerenaConnector


def success_response(data: Any) -> dict:
    """Standard success response."""
    return {"success": True, "data": data}


def error_response(message: str, hint: Optional[str] = None) -> JSONResponse:
    """Standard error response."""
    content = {"success": False, "error": message}
    if hint:
        content["hint"] = hint
    return JSONResponse(status_code=400, content=content)


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
    def connector(self) -> SerenaConnector:
        return self._connector

    @property
    def router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/status")
        async def status():
            """Get project status."""
            result = await self._connector.client.get_status()
            return success_response(result)

        @router.post("/activate")
        async def activate(project: Optional[str] = Query(None)):
            """Activate a project."""
            result = await self._connector.client.activate_project(project)
            return success_response(result)

        @router.get("/find")
        async def find(
            pattern: str,
            kind: Optional[str] = Query(None),
            path: Optional[str] = Query(None),
            body: bool = Query(False),
            depth: int = Query(0),
            exact: bool = Query(False),
        ):
            """Find symbols by pattern."""
            result = await self._connector.client.find_symbol(
                pattern,
                kind=kind,
                path=path,
                body=body,
                depth=depth,
                exact=exact,
            )
            return success_response(result)

        @router.get("/refs")
        async def refs(
            symbol: str,
            file: str,
            all: bool = Query(False, alias="all"),
        ):
            """Find references to a symbol."""
            result = await self._connector.client.find_refs(symbol, file, all_refs=all)
            return success_response(result)

        @router.get("/overview")
        async def overview(file: str):
            """Get file structure overview."""
            result = await self._connector.client.get_overview(file)
            return success_response(result)

        @router.get("/search")
        async def search(
            pattern: str,
            path: Optional[str] = Query(None),
            glob: Optional[str] = Query(None),
        ):
            """Regex search in code."""
            result = await self._connector.client.search(pattern, glob=glob, path=path)
            return success_response(result)

        @router.get("/recipe")
        async def recipe(name: str = Query("list")):
            """Run pre-built search recipes."""
            client = self._connector.client

            recipes = {
                # Project code (fast - src/ only)
                "entities": lambda: client.search(r"#\[ORM\\Entity", glob="src/**/*.php"),
                "controllers": lambda: client.find_symbol("Controller", kind="class", path="src/"),
                "services": lambda: client.find_symbol("Service", kind="class", path="src/"),
                "interfaces": lambda: client.find_symbol("Interface", kind="interface", path="src/"),
                "tests": lambda: client.find_symbol("Test", kind="class", path="src/"),
                # Oro framework - specific patterns
                "oro-payment": lambda: client.find_symbol("Payment", kind="class", path="vendor/oro"),
                "oro-checkout": lambda: client.find_symbol("Checkout", kind="class", path="vendor/oro"),
                "oro-order": lambda: client.find_symbol("Order", kind="class", path="vendor/oro"),
                "oro-product": lambda: client.find_symbol("Product", kind="class", path="vendor/oro"),
                "oro-customer": lambda: client.find_symbol("Customer", kind="class", path="vendor/oro"),
                "oro-shipping": lambda: client.find_symbol("Shipping", kind="class", path="vendor/oro"),
                "oro-events": lambda: client.find_symbol("Event", kind="class", path="vendor/oro/commerce/src/Oro/Bundle"),
                # Third-party integrations
                "mollie": lambda: client.find_symbol("Mollie", kind="class", path="vendor/mollie"),
                "netresearch-payment": lambda: client.find_symbol("Payment", kind="class", path="vendor/netresearch"),
                # Payment across ALL vendors (use specific pattern to limit results)
                "payment-methods": lambda: client.find_symbol("PaymentMethod", kind="class", path="vendor/"),
                "payment-providers": lambda: client.find_symbol("PaymentProvider", kind="class", path="vendor/"),
                "payment-factories": lambda: client.find_symbol("PaymentFactory", kind="class", path="vendor/"),
                "payment-interfaces": lambda: client.find_symbol("PaymentInterface", kind="interface", path="vendor/"),
            }

            if name == "list":
                categorized = {
                    "project": ["entities", "controllers", "services", "interfaces", "tests"],
                    "oro-framework": ["oro-payment", "oro-checkout", "oro-order",
                                     "oro-product", "oro-customer", "oro-shipping", "oro-events"],
                    "third-party": ["mollie", "netresearch-payment"],
                    "payment-all-vendors": ["payment-methods", "payment-providers",
                                           "payment-factories", "payment-interfaces"],
                }
                return success_response({"recipes": categorized})

            if name not in recipes:
                return error_response(
                    f"Unknown recipe: {name}",
                    f"Available: {', '.join(recipes.keys())}"
                )

            result = await recipes[name]()
            return success_response(result)

        @router.get("/tools")
        async def tools():
            """List available Serena MCP tools (dynamic discovery)."""
            result = await self._connector.client.get_tools()
            return success_response(result)

        # Memory endpoints
        @router.get("/memory/list")
        async def memory_list(folder: Optional[str] = Query(None)):
            """List memories."""
            result = await self._connector.client.memory_list(folder)
            return success_response(result)

        @router.get("/memory/read")
        async def memory_read(name: str):
            """Read a memory."""
            result = await self._connector.client.memory_read(name)
            return success_response(result)

        @router.post("/memory/write")
        async def memory_write(name: str, content: str):
            """Write a memory."""
            result = await self._connector.client.memory_write(name, content)
            return success_response(result)

        @router.post("/memory/delete")
        async def memory_delete(name: str):
            """Delete a memory."""
            result = await self._connector.client.memory_delete(name)
            return success_response(result)

        @router.post("/memory/move")
        async def memory_move(name: str, new_name: str):
            """Move/rename a memory."""
            result = await self._connector.client.memory_move(name, new_name)
            return success_response(result)

        @router.post("/memory/archive")
        async def memory_archive(name: str):
            """Archive a memory."""
            result = await self._connector.client.memory_archive(name)
            return success_response(result)

        @router.get("/memory/tree")
        async def memory_tree(folder: Optional[str] = Query(None)):
            """Get memory tree."""
            result = await self._connector.client.memory_tree(folder)
            return success_response(result)

        @router.get("/memory/search")
        async def memory_search(
            pattern: str,
            folder: Optional[str] = Query(None),
        ):
            """Search memories."""
            result = await self._connector.client.memory_search(pattern, folder)
            return success_response(result)

        @router.get("/memory/stats")
        async def memory_stats():
            """Get memory statistics."""
            result = await self._connector.client.memory_stats()
            return success_response(result)

        # Onboarding endpoints
        @router.get("/check_onboarding")
        async def check_onboarding():
            """Check if project onboarding was performed."""
            result = await self._connector.client.check_onboarding()
            return success_response(result)

        @router.get("/onboarding")
        async def onboarding():
            """Get onboarding instructions for new project."""
            result = await self._connector.client.onboarding()
            return success_response(result)

        @router.post("/init_memories")
        async def init_memories(include_templates: bool = Query(True)):
            """Initialize recommended memory folder structure."""
            result = await self._connector.client.init_memories(include_templates)
            return success_response(result)

        # Edit endpoints
        @router.post("/edit/replace")
        async def edit_replace(symbol: str, file: str, body: str):
            """Replace symbol body."""
            result = await self._connector.client.edit_replace(symbol, file, body)
            return success_response(result)

        @router.post("/edit/after")
        async def edit_after(symbol: str, file: str, code: str):
            """Insert code after symbol."""
            result = await self._connector.client.edit_after(symbol, file, code)
            return success_response(result)

        @router.post("/edit/before")
        async def edit_before(symbol: str, file: str, code: str):
            """Insert code before symbol."""
            result = await self._connector.client.edit_before(symbol, file, code)
            return success_response(result)

        @router.post("/edit/rename")
        async def edit_rename(symbol: str, file: str, new_name: str):
            """Rename symbol."""
            result = await self._connector.client.edit_rename(symbol, file, new_name)
            return success_response(result)

        return router

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


__all__ = ["SerenaPlugin"]
