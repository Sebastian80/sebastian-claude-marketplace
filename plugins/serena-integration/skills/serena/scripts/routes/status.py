"""
Status and activation endpoints.

Endpoints:
- GET /status - Get project status
- POST /activate - Activate a project
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..deps import serena
from ..response import success_response

router = APIRouter()


@router.get("/status")
async def status(client=Depends(serena)):
    """Get project status."""
    result = await client.get_status()
    return success_response(result)


@router.post("/activate")
async def activate(project: Optional[str] = Query(None), client=Depends(serena)):
    """Activate a project."""
    result = await client.activate_project(project)
    return success_response(result)
