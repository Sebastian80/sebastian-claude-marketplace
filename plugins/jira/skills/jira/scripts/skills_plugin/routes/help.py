"""
Help endpoint - Self-describing API documentation.

Provides condensed, AI-friendly documentation extracted from OpenAPI spec.
Much smaller than raw OpenAPI JSON while retaining essential information.

Endpoints:
- GET /help - List all endpoints with condensed descriptions
- GET /help/{endpoint} - Detailed help for specific endpoint

Examples:
    jira help                    # All endpoints
    jira help search             # Help for search endpoint
    jira help --format ai        # AI-optimized format
"""

import re
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

router = APIRouter()


def extract_enum_from_description(description: str) -> list[str] | None:
    """Extract enum values from description patterns like 'format: json, human, ai'."""
    patterns = [
        r":\s*([a-zA-Z]+(?:,\s*[a-zA-Z]+)+)",  # "format: json, human, ai"
        r"\(([a-zA-Z]+(?:,\s*[a-zA-Z]+)+)\)",  # "(json, human, ai)"
    ]
    for pattern in patterns:
        match = re.search(pattern, description or "")
        if match:
            values = [v.strip() for v in match.group(1).split(",")]
            if len(values) >= 2:
                return values
    return None


def condense_parameter(param: dict[str, Any]) -> dict[str, Any]:
    """Condense a parameter to essential info."""
    schema = param.get("schema", {})
    desc = param.get("description", "")

    result = {
        "name": param.get("name"),
        "required": param.get("required", False),
        "type": schema.get("type", "string"),
    }

    # Add description if meaningful
    if desc and len(desc) < 100:
        result["description"] = desc

    # Extract enum from description or schema
    if "enum" in schema:
        result["enum"] = schema["enum"]
    else:
        enum = extract_enum_from_description(desc)
        if enum:
            result["enum"] = enum

    # Add default if present
    if "default" in schema:
        result["default"] = schema["default"]

    # Add constraints
    if "minimum" in schema:
        result["min"] = schema["minimum"]
    if "maximum" in schema:
        result["max"] = schema["maximum"]

    return result


def condense_endpoint(path: str, method: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Condense an endpoint spec to essential info."""
    # Extract first line of description as summary
    desc = spec.get("description", "")
    summary = desc.split("\n")[0] if desc else spec.get("summary", "")

    result = {
        "method": method.upper(),
        "path": path,
        "summary": summary,
    }

    # Condense parameters
    params = spec.get("parameters", [])
    if params:
        condensed_params = []
        for p in params:
            if p.get("in") in ("query", "path"):
                condensed_params.append(condense_parameter(p))
        if condensed_params:
            result["params"] = condensed_params

    return result


def format_help_text(endpoints: list[dict], endpoint_filter: str | None = None) -> str:
    """Format endpoints as human-readable text."""
    lines = ["Jira CLI - Available Commands", "=" * 40, ""]

    for ep in endpoints:
        path = ep["path"].replace("/jira", "jira")
        method = ep["method"]

        # Show method only if not GET
        if method != "GET":
            lines.append(f"{path} [{method}]")
        else:
            lines.append(path)

        lines.append(f"  {ep['summary']}")

        if ep.get("params"):
            for p in ep["params"]:
                req = "*" if p["required"] else ""
                default = f" (default: {p['default']})" if "default" in p else ""
                enum = f" [{', '.join(p['enum'])}]" if "enum" in p else ""
                lines.append(f"    --{p['name']}{req}{enum}{default}")

        lines.append("")

    return "\n".join(lines)


def format_help_ai(endpoints: list[dict]) -> str:
    """Format endpoints as AI-optimized condensed text."""
    lines = ["# Jira API Endpoints", ""]

    for ep in endpoints:
        path = ep["path"]
        method = ep["method"]
        params = ep.get("params", [])

        # Compact format: METHOD /path - summary
        lines.append(f"## {method} {path}")
        lines.append(ep["summary"])

        if params:
            param_strs = []
            for p in params:
                s = p["name"]
                if p["required"]:
                    s += "*"
                if "enum" in p:
                    s += f":[{','.join(p['enum'])}]"
                elif p["type"] != "string":
                    s += f":{p['type']}"
                param_strs.append(s)
            lines.append(f"Params: {', '.join(param_strs)}")

        lines.append("")

    return "\n".join(lines)


@router.get("/help")
async def get_help(
    request: Request,
    endpoint: str | None = Query(None, description="Filter to specific endpoint name"),
    format: str = Query("human", description="Output format: json, human, ai"),
):
    """Get condensed API documentation.

    Returns AI-friendly documentation extracted from OpenAPI spec.
    Much smaller than raw /openapi.json while retaining essential info.

    Formats:
    - human: Readable CLI help format
    - ai: Ultra-condensed for LLM consumption
    - json: Structured data

    Examples:
        jira help                    # All endpoints (human format)
        jira help --format ai        # AI-optimized format
        jira help --endpoint search  # Filter to search endpoint
        jira help search             # Same as above
    """
    # Get OpenAPI spec from the app
    app = request.app
    openapi = app.openapi()

    # Extract Jira endpoints
    endpoints = []
    for path, methods in openapi.get("paths", {}).items():
        if not path.startswith("/jira"):
            continue

        # Skip if filtering and doesn't match
        if endpoint:
            # Match endpoint name in path
            if endpoint.lower() not in path.lower():
                continue

        for method, spec in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                endpoints.append(condense_endpoint(path, method, spec))

    # Sort by path
    endpoints.sort(key=lambda e: (e["path"], e["method"]))

    if format == "human":
        return PlainTextResponse(format_help_text(endpoints))
    elif format == "ai":
        return PlainTextResponse(format_help_ai(endpoints))
    else:
        return {"endpoints": endpoints, "count": len(endpoints)}


@router.get("/help/{endpoint_name}")
async def get_endpoint_help(
    request: Request,
    endpoint_name: str,
    format: str = Query("human", description="Output format: json, human, ai"),
):
    """Get help for specific endpoint.

    Returns detailed documentation for a single endpoint.
    Matches endpoint by name (e.g., 'search', 'issue', 'transition').

    Examples:
        jira help search         # Search endpoint help
        jira help transition     # Transition endpoint help
        jira help create         # Create issue help
    """
    # Get OpenAPI spec from the app
    app = request.app
    openapi = app.openapi()

    # Find matching endpoints
    endpoints = []
    for path, methods in openapi.get("paths", {}).items():
        if not path.startswith("/jira"):
            continue

        # Match endpoint name in path
        if endpoint_name.lower() not in path.lower():
            continue

        for method, spec in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                ep = condense_endpoint(path, method, spec)
                # Include full description for specific endpoint
                ep["description"] = spec.get("description", "")
                endpoints.append(ep)

    if not endpoints:
        return PlainTextResponse(
            f"No endpoint found matching '{endpoint_name}'\n"
            "Use 'jira help' to list all endpoints.",
            status_code=404,
        )

    if format == "human":
        lines = [f"Help for '{endpoint_name}'", "=" * 40, ""]
        for ep in endpoints:
            lines.append(f"{ep['method']} {ep['path']}")
            lines.append("")
            if ep.get("description"):
                lines.append(ep["description"])
            lines.append("")
            if ep.get("params"):
                lines.append("Parameters:")
                for p in ep["params"]:
                    req = " (required)" if p["required"] else ""
                    desc = f" - {p.get('description', '')}" if p.get("description") else ""
                    lines.append(f"  --{p['name']}{req}{desc}")
            lines.append("")
        return PlainTextResponse("\n".join(lines))
    elif format == "ai":
        return PlainTextResponse(format_help_ai(endpoints))
    else:
        return {"endpoints": endpoints, "count": len(endpoints)}
