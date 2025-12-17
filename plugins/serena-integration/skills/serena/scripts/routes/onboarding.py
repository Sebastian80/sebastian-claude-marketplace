"""
Onboarding and initialization endpoints.

Endpoints:
- GET /check_onboarding - Check if project onboarding was performed
- GET /onboarding - Get onboarding instructions
- POST /init_memories - Initialize recommended memory folder structure
"""

from fastapi import APIRouter, Depends, Query

from ..deps import serena
from ..response import success_response

router = APIRouter()


@router.get("/check_onboarding")
async def check_onboarding(client=Depends(serena)):
    """Check if project onboarding was performed."""
    result = await client.check_onboarding()
    return success_response(result)


@router.get("/onboarding")
async def onboarding(client=Depends(serena)):
    """Get onboarding instructions for new project."""
    result = await client.onboarding()
    return success_response(result)


@router.post("/init_memories")
async def init_memories(include_templates: bool = Query(True), client=Depends(serena)):
    """Initialize recommended memory folder structure."""
    result = await client.init_memories(include_templates)
    return success_response(result)
