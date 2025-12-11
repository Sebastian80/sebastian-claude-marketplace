"""
Priority reference data.

Endpoints:
- GET /priorities - List all priority levels
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, formatted_response

router = APIRouter()


@router.get("/priorities")
async def list_priorities(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List all priority levels.

    Returns available priority levels (e.g., Highest, High, Medium, Low, Lowest).
    Use these values when creating or updating issues.

    Examples:
        jira priorities
        jira priorities --format human
    """
    client = await get_client()
    try:
        priorities = client.get_all_priorities()
        return formatted_response(priorities, format, "priorities")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
