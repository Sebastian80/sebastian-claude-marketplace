"""
Search operations.

Search for issues using JQL (Jira Query Language).

Endpoints:
- GET /search - Search issues with JQL

Examples:
    jira search --jql "project = PROJ"
    jira search --jql "assignee = currentUser()" --maxResults 100
    jira search --jql "project = PROJ" --startAt 50 --maxResults 50  # Page 2
    jira search --jql "status = Open" --fields key,summary,status
"""

from fastapi import APIRouter, Query

from ..client import get_client, formatted_response, formatted_error

router = APIRouter()


@router.get("/search")
async def search(
    jql: str = Query(..., description="JQL query string (e.g., 'project = PROJ AND status = Open')"),
    max_results: int = Query(50, alias="maxResults", ge=1, le=100, description="Maximum results to return (1-100)"),
    start_at: int = Query(0, alias="startAt", ge=0, description="Index of first result (for pagination)"),
    fields: str = Query(
        "key,summary,status,assignee,priority,issuetype",
        description="Comma-separated fields to return"
    ),
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Search issues using JQL query.

    Returns issues matching the JQL query with specified fields.
    JQL (Jira Query Language) supports complex filters.

    Pagination:
    - Use --startAt to skip results (0 = first page)
    - Use --maxResults to limit results per page
    - Page 1: --startAt 0 --maxResults 50
    - Page 2: --startAt 50 --maxResults 50

    Common JQL patterns:
    - project = PROJ
    - status = "In Progress"
    - status NOT IN (Done, Closed)
    - assignee = currentUser()
    - assignee IS EMPTY
    - created >= -7d (last 7 days)
    - updated >= startOfWeek()
    - labels IN (bug, urgent)
    - summary ~ "search text"
    - ORDER BY created DESC

    Examples:
        jira search --jql "project = PROJ AND status = Open"
        jira search --jql "assignee = currentUser() AND status != Done"
        jira search --jql "project = PROJ ORDER BY priority DESC" --maxResults 100
        jira search --jql "labels = urgent" --format human
        jira search --jql "project = PROJ" --fields key,summary,status
        jira search --jql "project = PROJ" --startAt 50 --maxResults 50
    """
    client = await get_client()
    field_list = [f.strip() for f in fields.split(',')]

    try:
        results = client.jql(jql, limit=max_results, start=start_at, fields=field_list)
        issues = results.get('issues', [])

        # Include pagination info in response
        if format == "json":
            return {
                "success": True,
                "data": issues,
                "pagination": {
                    "startAt": start_at,
                    "maxResults": max_results,
                    "total": results.get('total', len(issues)),
                    "returned": len(issues),
                }
            }
        return formatted_response(issues, format, "search")
    except Exception as e:
        error_msg = str(e)
        hint = "Check JQL syntax. Common issues: missing quotes around values with spaces"
        if "field" in error_msg.lower():
            hint = "Invalid field name. Check spelling and custom field IDs"
        elif "does not exist" in error_msg.lower() or "existiert nicht" in error_msg.lower():
            hint = "Value does not exist. Check project keys, status names, or field values"
        return formatted_error(f"JQL error: {e}", hint=hint, fmt=format)
