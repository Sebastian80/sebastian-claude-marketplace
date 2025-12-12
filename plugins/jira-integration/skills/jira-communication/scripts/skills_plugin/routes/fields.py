"""
Field reference data.

Endpoints:
- GET /fields - List all fields
- GET /fields/custom - List only custom fields
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import formatted

router = APIRouter()


@router.get("/fields")
async def list_fields(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List all fields."""
    try:
        fields = client.get_all_fields()
        return formatted(fields, format, "fields")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fields/custom")
async def list_custom_fields(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List only custom fields."""
    try:
        all_fields = client.get_all_fields()
        custom_fields = [f for f in all_fields if f.get("id", "").startswith("customfield_")]
        return formatted(custom_fields, format, "custom_fields")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
