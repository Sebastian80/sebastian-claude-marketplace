"""
Health check endpoint.

Verify Jira connection is working properly.

Endpoints:
- GET /health - Check Jira connection health

Examples:
    jira health           # Quick connection check
    jira health --format human
"""

from fastapi import APIRouter, Query

from ..client import get_client, formatted_response

router = APIRouter()


@router.get("/health")
async def health_check(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Check Jira connection health.

    Verifies the connection to Jira is working by fetching
    your user profile. Returns connection status and user info.

    Use this to:
    - Verify API credentials are valid
    - Check Jira server is reachable
    - Confirm your session is active

    Examples:
        jira health
        jira health --format human
    """
    try:
        client = await get_client()
        user = client.myself()

        health_data = {
            "status": "healthy",
            "connected": True,
            "user": user.get("displayName", user.get("name", "Unknown")),
            "email": user.get("emailAddress"),
            "server": getattr(client, "url", "Unknown"),
        }
        return formatted_response(health_data, format, "health")
    except Exception as e:
        health_data = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }
        return formatted_response(health_data, format, "health")
