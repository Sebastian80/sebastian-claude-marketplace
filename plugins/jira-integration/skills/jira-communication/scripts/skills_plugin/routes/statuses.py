"""
Status reference data.

Endpoints:
- GET /statuses - List all statuses
- GET /status/{name} - Get status by name
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, formatted_response

router = APIRouter()


@router.get("/statuses")
async def list_statuses(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List all statuses.

    Returns all available issue statuses across the Jira instance.
    Use these values when transitioning issues or searching by status.

    Examples:
        jira statuses
        jira statuses --format human
    """
    client = await get_client()
    try:
        statuses = client.get_all_statuses()
        return formatted_response(statuses, format, "statuses")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{name}")
async def get_status(
    name: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get status by name.

    Retrieves detailed information about a specific status.
    Status name matching is case-insensitive.

    Examples:
        jira status "In Progress"
        jira status Done --format human
        jira status "To Do"
    """
    client = await get_client()
    try:
        # Get all statuses and filter by name (case-insensitive)
        all_statuses = client.get_all_statuses()
        name_lower = name.lower()
        for status in all_statuses:
            if status.get("name", "").lower() == name_lower:
                return formatted_response(status, format, "status")
        raise HTTPException(
            status_code=404,
            detail=f"Status '{name}' not found. Use 'jira statuses' to list available statuses."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
