"""
User operations.

Get information about users in Jira.

Endpoints:
- GET /user - Get current authenticated user (alias for /user/me)
- GET /user/me - Get current authenticated user

Examples:
    jira user             # Your user info
    jira user --format human
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, formatted_response

router = APIRouter()


@router.get("/user")
async def get_user(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get current authenticated user.

    Returns your Jira user profile including:
    - Username and display name
    - Email address
    - Account ID
    - Time zone
    - Avatar URLs

    Useful for verifying your Jira connection is working.

    Examples:
        jira user
        jira user --format human
    """
    client = await get_client()
    try:
        user = client.myself()
        return formatted_response(user, format, "user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/me")
async def get_current_user(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get current authenticated user (alias for /user).

    Examples:
        jira user/me
    """
    client = await get_client()
    try:
        user = client.myself()
        return formatted_response(user, format, "user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
