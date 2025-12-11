"""
Saved filter operations.

Manage saved JQL queries (filters) in Jira. Filters let you save and reuse
complex JQL searches.

Endpoints:
- GET /filters - List your favorite filters
- GET /filter/{filter_id} - Get filter details including JQL

Note: Jira's REST API only provides access to your favorite filters.
To access a specific filter, use its ID with 'jira filter <id>'.

Examples:
    jira filters              # List your favorite filters
    jira filter 12345         # Get filter details + JQL query
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, formatted_response

router = APIRouter()


@router.get("/filters")
async def list_filters(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List your favorite filters.

    Returns filters you have marked as favorites in Jira.
    These are saved JQL queries you can quickly reuse.

    To get the JQL of a filter: jira filter <filter_id>

    Note: Due to Jira API limitations, this only shows favorites.
    To access any filter by ID, use 'jira filter <id>'.

    Examples:
        jira filters
        jira filters --format human
    """
    client = await get_client()
    try:
        # Use REST API directly - get favorite filters
        endpoint = "rest/api/2/filter/favourite"
        response = client._session.get(f"{client.url}/{endpoint}")
        response.raise_for_status()
        filters = response.json()
        return formatted_response(filters, format, "filters")
    except Exception as e:
        error_msg = str(e).lower()
        if "404" in error_msg or "not found" in error_msg:
            # No favorites - return empty list
            return formatted_response([], format, "filters")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/{filter_id}")
async def get_filter(
    filter_id: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get filter details.

    Returns filter details including the JQL query.
    Useful for understanding what a saved filter searches for.

    Examples:
        jira filter 12345
        jira filter 12345 --format human
    """
    client = await get_client()
    try:
        filter_data = client.get_filter(filter_id)
        return formatted_response(filter_data, format, "filter")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
