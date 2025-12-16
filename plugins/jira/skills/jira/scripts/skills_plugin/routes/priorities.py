"""
Priority reference data.

Endpoints:
- GET /priorities - List all priority levels
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import formatted

router = APIRouter()


@router.get("/priorities")
async def list_priorities(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List all priority levels."""
    try:
        priorities = client.get_all_priorities()
        return formatted(priorities, format, "priorities")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
