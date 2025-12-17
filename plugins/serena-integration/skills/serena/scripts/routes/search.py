"""
Search and recipe endpoints.

Endpoints:
- GET /search - Regex search in code
- GET /recipe - Run pre-built search recipes
- GET /tools - List available Serena MCP tools
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..deps import serena
from ..response import success_response, error_response

router = APIRouter()


@router.get("/search")
async def search(
    pattern: str,
    path: Optional[str] = Query(None),
    glob: Optional[str] = Query(None),
    client=Depends(serena),
):
    """Regex search in code."""
    result = await client.search(pattern, glob=glob, path=path)
    return success_response(result)


@router.get("/recipe")
async def recipe(name: str = Query("list"), client=Depends(serena)):
    """Run pre-built search recipes."""
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
async def tools(client=Depends(serena)):
    """List available Serena MCP tools (dynamic discovery)."""
    result = await client.get_tools()
    return success_response(result)
