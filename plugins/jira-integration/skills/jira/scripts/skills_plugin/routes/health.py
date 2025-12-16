"""
Health check endpoint.

Verify Jira connection is working properly.

Endpoints:
- GET /health - Check Jira connection health

Examples:
    jira health           # Quick connection check
    jira health --format human
"""

from fastapi import APIRouter, Depends, Query

from ..deps import jira
from ..response import formatted

router = APIRouter()


@router.get("/health")
async def health_check(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Check Jira connection health."""
    try:
        user = client.myself()
        health_data = {
            "status": "healthy",
            "connected": True,
            "user": user.get("displayName", user.get("name", "Unknown")),
            "email": user.get("emailAddress"),
            "server": getattr(client, "url", "Unknown"),
        }
        return formatted(health_data, format, "health")
    except Exception as e:
        health_data = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }
        return formatted(health_data, format, "health")
