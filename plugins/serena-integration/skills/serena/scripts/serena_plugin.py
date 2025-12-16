"""
Serena plugin for AI Tool Bridge.

Provides semantic code navigation via Serena MCP server.
"""


import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

# Add serena_cli to path
SERENA_SCRIPTS = Path(__file__).parent.parent
if str(SERENA_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SERENA_SCRIPTS))

# Import SerenaClient (lazy, fails gracefully if not available)
SerenaClient = None
client = None


async def get_client():
    """Get or create SerenaClient instance."""
    global SerenaClient, client

    if SerenaClient is None:
        try:
            from serena_cli.client import SerenaClient as SC
            SerenaClient = SC
        except ImportError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Serena client not available: {e}",
            )

    if client is None:
        client = SerenaClient()
        await client.connect()

    return client


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
            bridge_context: Optional bridge services (unused)
        """
        pass

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
        router = APIRouter()

        @router.get("/status")
        async def status():
            """Get project status."""
            c = await get_client()
            result = await c.get_status()
            return success_response(result)

        @router.post("/activate")
        async def activate(project: Optional[str] = Query(None)):
            """Activate a project."""
            c = await get_client()
            result = await c.activate_project(project)
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
            c = await get_client()
            result = await c.find_symbol(
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
            c = await get_client()
            result = await c.find_refs(symbol, file, all_refs=all)
            return success_response(result)

        @router.get("/overview")
        async def overview(file: str):
            """Get file structure overview."""
            c = await get_client()
            result = await c.get_overview(file)
            return success_response(result)

        @router.get("/search")
        async def search(
            pattern: str,
            path: Optional[str] = Query(None),
            glob: Optional[str] = Query(None),
        ):
            """Regex search in code."""
            c = await get_client()
            result = await c.search(pattern, glob=glob, path=path)
            return success_response(result)

        @router.get("/recipe")
        async def recipe(name: str = Query("list")):
            """Run pre-built search recipes."""
            c = await get_client()

            recipes = {
                # Project code (fast - src/ only)
                "entities": lambda: c.search(r"#\[ORM\\Entity", glob="src/**/*.php"),
                "controllers": lambda: c.find_symbol("Controller", kind="class", path="src/"),
                "services": lambda: c.find_symbol("Service", kind="class", path="src/"),
                "interfaces": lambda: c.find_symbol("Interface", kind="interface", path="src/"),
                "tests": lambda: c.find_symbol("Test", kind="class", path="src/"),
                # Oro framework - specific patterns
                "oro-payment": lambda: c.find_symbol("Payment", kind="class", path="vendor/oro"),
                "oro-checkout": lambda: c.find_symbol("Checkout", kind="class", path="vendor/oro"),
                "oro-order": lambda: c.find_symbol("Order", kind="class", path="vendor/oro"),
                "oro-product": lambda: c.find_symbol("Product", kind="class", path="vendor/oro"),
                "oro-customer": lambda: c.find_symbol("Customer", kind="class", path="vendor/oro"),
                "oro-shipping": lambda: c.find_symbol("Shipping", kind="class", path="vendor/oro"),
                "oro-events": lambda: c.find_symbol("Event", kind="class", path="vendor/oro/commerce/src/Oro/Bundle"),
                # Third-party integrations
                "mollie": lambda: c.find_symbol("Mollie", kind="class", path="vendor/mollie"),
                "netresearch-payment": lambda: c.find_symbol("Payment", kind="class", path="vendor/netresearch"),
                # Payment across ALL vendors (use specific pattern to limit results)
                "payment-methods": lambda: c.find_symbol("PaymentMethod", kind="class", path="vendor/"),
                "payment-providers": lambda: c.find_symbol("PaymentProvider", kind="class", path="vendor/"),
                "payment-factories": lambda: c.find_symbol("PaymentFactory", kind="class", path="vendor/"),
                "payment-interfaces": lambda: c.find_symbol("PaymentInterface", kind="interface", path="vendor/"),
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
            c = await get_client()
            result = await c.get_tools()
            return success_response(result)

        # Memory endpoints
        @router.get("/memory/list")
        async def memory_list(folder: Optional[str] = Query(None)):
            """List memories."""
            c = await get_client()
            result = await c.memory_list(folder)
            return success_response(result)

        @router.get("/memory/read")
        async def memory_read(name: str):
            """Read a memory."""
            c = await get_client()
            result = await c.memory_read(name)
            return success_response(result)

        @router.post("/memory/write")
        async def memory_write(name: str, content: str):
            """Write a memory."""
            c = await get_client()
            result = await c.memory_write(name, content)
            return success_response(result)

        @router.post("/memory/delete")
        async def memory_delete(name: str):
            """Delete a memory."""
            c = await get_client()
            result = await c.memory_delete(name)
            return success_response(result)

        @router.post("/memory/move")
        async def memory_move(name: str, new_name: str):
            """Move/rename a memory."""
            c = await get_client()
            result = await c.memory_move(name, new_name)
            return success_response(result)

        @router.post("/memory/archive")
        async def memory_archive(name: str):
            """Archive a memory."""
            c = await get_client()
            result = await c.memory_archive(name)
            return success_response(result)

        @router.get("/memory/tree")
        async def memory_tree(folder: Optional[str] = Query(None)):
            """Get memory tree."""
            c = await get_client()
            result = await c.memory_tree(folder)
            return success_response(result)

        @router.get("/memory/search")
        async def memory_search(
            pattern: str,
            folder: Optional[str] = Query(None),
        ):
            """Search memories."""
            c = await get_client()
            result = await c.memory_search(pattern, folder)
            return success_response(result)

        @router.get("/memory/stats")
        async def memory_stats():
            """Get memory statistics."""
            c = await get_client()
            result = await c.memory_stats()
            return success_response(result)

        # Onboarding endpoints
        @router.get("/check_onboarding")
        async def check_onboarding():
            """Check if project onboarding was performed."""
            c = await get_client()
            result = await c.check_onboarding()
            return success_response(result)

        @router.get("/onboarding")
        async def onboarding():
            """Get onboarding instructions for new project."""
            c = await get_client()
            result = await c.onboarding()
            return success_response(result)

        @router.post("/init_memories")
        async def init_memories(include_templates: bool = Query(True)):
            """Initialize recommended memory folder structure."""
            c = await get_client()
            result = await c.init_memories(include_templates)
            return success_response(result)

        # Edit endpoints
        @router.post("/edit/replace")
        async def edit_replace(symbol: str, file: str, body: str):
            """Replace symbol body."""
            c = await get_client()
            result = await c.edit_replace(symbol, file, body)
            return success_response(result)

        @router.post("/edit/after")
        async def edit_after(symbol: str, file: str, code: str):
            """Insert code after symbol."""
            c = await get_client()
            result = await c.edit_after(symbol, file, code)
            return success_response(result)

        @router.post("/edit/before")
        async def edit_before(symbol: str, file: str, code: str):
            """Insert code before symbol."""
            c = await get_client()
            result = await c.edit_before(symbol, file, code)
            return success_response(result)

        @router.post("/edit/rename")
        async def edit_rename(symbol: str, file: str, new_name: str):
            """Rename symbol."""
            c = await get_client()
            result = await c.edit_rename(symbol, file, new_name)
            return success_response(result)

        return router

    async def startup(self) -> None:
        """Initialize Serena client on startup."""
        # Client is initialized lazily on first request
        pass

    async def shutdown(self) -> None:
        """Close Serena client on shutdown."""
        global client
        if client is not None:
            await client.close()
            client = None

    def health_check(self) -> dict[str, Any]:
        """Check Serena connection health."""
        if client is None:
            return {"status": "not_connected"}
        return {"status": "connected"}


__all__ = ["SerenaPlugin"]
