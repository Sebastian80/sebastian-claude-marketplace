"""
Code editing endpoints.

Endpoints:
- POST /edit/replace - Replace symbol body
- POST /edit/after - Insert code after symbol
- POST /edit/before - Insert code before symbol
- POST /edit/rename - Rename symbol
"""

from fastapi import APIRouter, Depends

from ..deps import serena
from ..response import success_response

router = APIRouter()


@router.post("/edit/replace")
async def edit_replace(symbol: str, file: str, body: str, client=Depends(serena)):
    """Replace symbol body."""
    result = await client.edit_replace(symbol, file, body)
    return success_response(result)


@router.post("/edit/after")
async def edit_after(symbol: str, file: str, code: str, client=Depends(serena)):
    """Insert code after symbol."""
    result = await client.edit_after(symbol, file, code)
    return success_response(result)


@router.post("/edit/before")
async def edit_before(symbol: str, file: str, code: str, client=Depends(serena)):
    """Insert code before symbol."""
    result = await client.edit_before(symbol, file, code)
    return success_response(result)


@router.post("/edit/rename")
async def edit_rename(symbol: str, file: str, new_name: str, client=Depends(serena)):
    """Rename symbol."""
    result = await client.edit_rename(symbol, file, new_name)
    return success_response(result)
