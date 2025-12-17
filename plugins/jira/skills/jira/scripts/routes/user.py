"""
User operations.

Get information about users in Jira.

Endpoints:
- GET /user - Get current authenticated user (alias for /user/me)
- GET /user/me - Get current authenticated user
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import formatted

router = APIRouter()


@router.get("/user")
async def get_user(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get current authenticated user."""
    try:
        user = client.myself()
        return formatted(user, format, "user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/me")
async def get_current_user(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get current authenticated user (alias for /user)."""
    try:
        user = client.myself()
        return formatted(user, format, "user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
