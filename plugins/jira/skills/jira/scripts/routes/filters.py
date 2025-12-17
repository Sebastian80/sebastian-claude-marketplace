"""
Saved filter operations.

Endpoints:
- GET /filters - List your favorite filters
- GET /filter/{filter_id} - Get filter details including JQL
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import formatted

router = APIRouter()


@router.get("/filters")
async def list_filters(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List your favorite filters."""
    try:
        endpoint = "rest/api/2/filter/favourite"
        response = client._session.get(f"{client.url}/{endpoint}")
        response.raise_for_status()
        filters = response.json()
        return formatted(filters, format, "filters")
    except Exception as e:
        error_msg = str(e).lower()
        if "404" in error_msg or "not found" in error_msg:
            return formatted([], format, "filters")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter/{filter_id}")
async def get_filter(
    filter_id: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get filter details."""
    try:
        filter_data = client.get_filter(filter_id)
        return formatted(filter_data, format, "filter")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
