"""
Status reference data.

Endpoints:
- GET /statuses - List all statuses
- GET /status/{name} - Get status by name
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import formatted

router = APIRouter()


@router.get("/statuses")
async def list_statuses(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List all statuses."""
    try:
        statuses = client.get_all_statuses()
        return formatted(statuses, format, "statuses")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{name}")
async def get_status(
    name: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get status by name."""
    try:
        all_statuses = client.get_all_statuses()
        name_lower = name.lower()
        for status in all_statuses:
            if status.get("name", "").lower() == name_lower:
                return formatted(status, format, "status")
        raise HTTPException(status_code=404, detail=f"Status '{name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
