"""
Saved filter operations.

Endpoints:
- GET /filters - List all accessible filters
- GET /filters/my - List my filters
- GET /filters/favorites - List favorite filters
- GET /filter/{filter_id} - Get filter details
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, formatted_response

router = APIRouter()


@router.get("/filters")
async def list_filters(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List all accessible filters.

    Returns saved JQL filters you have access to.
    Use filter IDs to quickly run saved searches.

    Examples:
        jira filters
        jira filters --format human
    """
    client = await get_client()
    try:
        filters = client.get_all_filters()
        return formatted_response(filters, format, "filters")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters/my")
async def list_my_filters(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List my filters.

    Returns filters owned by the current user.
    These are filters you have created.

    Examples:
        jira filters my
        jira filters my --format human
    """
    client = await get_client()
    try:
        filters = client.my_filters()
        return formatted_response(filters, format, "my_filters")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters/favorites")
async def list_favorite_filters(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List favorite filters.

    Returns filters marked as favorites by the current user.
    Quick access to your most-used saved searches.

    Examples:
        jira filters favorites
        jira filters favorites --format human
    """
    client = await get_client()
    try:
        filters = client.favourite_filters()
        return formatted_response(filters, format, "favorite_filters")
    except Exception as e:
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
