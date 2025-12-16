"""
Search operations.

Search for issues using JQL (Jira Query Language).

Endpoints:
- GET /search - Search issues with JQL
"""

from fastapi import APIRouter, Depends, Query

from ..deps import jira
from ..response import formatted, formatted_error

router = APIRouter()


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

    try:
        results = client.jql(jql, limit=max_results, start=start_at, fields=field_list)
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
