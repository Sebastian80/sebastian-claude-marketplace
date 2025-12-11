"""
Search operations.

Endpoints:
- GET /search - Search issues with JQL
"""

from fastapi import APIRouter, Query

from ..client import get_client, formatted_response, formatted_error

router = APIRouter()


@router.get("/search")
async def search(
    jql: str = Query(..., description="JQL query string"),
    max_results: int = Query(50, alias="maxResults", description="Maximum results (1-100)"),
    fields: str = Query(
        "key,summary,status,assignee,priority,issuetype",
        description="Comma-separated fields to return"
    ),
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Search issues using JQL query.

    Returns issues matching the JQL query with specified fields.
    JQL (Jira Query Language) supports complex filters.

    Common JQL patterns:
    - project = PROJ
    - status = "In Progress"
    - assignee = currentUser()
    - created >= -7d (last 7 days)
    - labels in (bug, urgent)
    - ORDER BY created DESC

    Examples:
        jira search --jql "project = PROJ AND status = Open"
        jira search --jql "assignee = currentUser() AND status != Done"
        jira search --jql "project = PROJ ORDER BY priority DESC" --maxResults 100
        jira search --jql "labels = urgent" --format human
        jira search --jql "project = PROJ" --fields key,summary,status
    """
    client = await get_client()
    field_list = [f.strip() for f in fields.split(',')]

    try:
        results = client.jql(jql, limit=max_results, fields=field_list)
        return formatted_response(results.get('issues', []), format, "search")
    except Exception as e:
        error_msg = str(e)
        hint = "Check JQL syntax. Common issues: missing quotes around values with spaces"
        if "field" in error_msg.lower():
            hint = "Invalid field name. Check spelling and custom field IDs"
        return formatted_error(f"JQL error: {e}", hint=hint, fmt=format)
