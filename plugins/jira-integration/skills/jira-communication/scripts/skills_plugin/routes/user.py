"""
User operations.

Endpoints:
- GET /user/me - Get current authenticated user
"""

from fastapi import APIRouter, HTTPException

from ..client import get_client, success_response

router = APIRouter()


@router.get("/user/me")
async def get_current_user():
    """Get current authenticated user.

    Returns details about the authenticated Jira user.
    Useful for verifying connection and getting your username.

    Examples:
        jira user/me
    """
    client = await get_client()
    try:
        user = client.myself()
        return success_response(user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
