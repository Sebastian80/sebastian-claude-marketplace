"""
Search operations.

Search for issues using JQL (Jira Query Language).

Endpoints:
- GET /search - Search issues with JQL
"""

import re

from fastapi import APIRouter, Depends, Query

from ..deps import jira
from ..response import formatted, formatted_error

router = APIRouter()


def preprocess_jql(jql: str) -> str:
    """Pre-process JQL to fix common issues.

    Converts:
    - `field != value` → `NOT field = value`
    - `field \!= value` → `NOT field = value` (escaped variant)
    - `field !~ value` → `NOT field ~ value`
    - `field \!~ value` → `NOT field ~ value` (escaped variant)

    This works around bash/Claude Code escaping and
    library escaping bugs in atlassian-python-api.
    """
    # Match: field != or \!= value (with optional quotes around value)
    # Captures: field name, value (including quotes if present)
    jql = re.sub(
        r'(\w+)\s*\\?!=\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\S+)',
        r'NOT \1 = \2',
        jql
    )
    # Match: field !~ or \!~ value
    jql = re.sub(
        r'(\w+)\s*\\?!~\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\S+)',
        r'NOT \1 ~ \2',
        jql
    )
    return jql


@router.get("/search")
async def search(
    jql: str = Query(..., description="JQL query string"),
    max_results: int = Query(50, alias="maxResults", ge=1, le=100, description="Maximum results (1-100)"),
    start_at: int = Query(0, alias="startAt", ge=0, description="Index of first result (for pagination)"),
    fields: str = Query("key,summary,status,assignee,priority,issuetype", description="Comma-separated fields"),
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Search issues using JQL query."""
    field_list = [f.strip() for f in fields.split(",")]

    # Pre-process JQL to fix != and !~ operators
    processed_jql = preprocess_jql(jql)

    try:
        results = client.jql(processed_jql, limit=max_results, start=start_at, fields=field_list)
        issues = results.get("issues", [])

        if format == "json":
            return {
                "success": True,
                "data": issues,
                "pagination": {
                    "startAt": start_at,
                    "maxResults": max_results,
                    "total": results.get("total", len(issues)),
                    "returned": len(issues),
                },
            }
        return formatted(issues, format, "search")
    except Exception as e:
        error_msg = str(e)
        hint = "Check JQL syntax"
        if "field" in error_msg.lower():
            hint = "Invalid field name"
        elif "does not exist" in error_msg.lower() or "existiert nicht" in error_msg.lower():
            hint = "Value does not exist"
        return formatted_error(f"JQL error: {e}", hint=hint, fmt=format)
