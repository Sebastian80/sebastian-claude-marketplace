"""
Symbol finding and reference endpoints.

Endpoints:
- GET /find - Find symbols by pattern
- GET /refs - Find references to a symbol
- GET /overview - Get file structure overview
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..deps import serena
from ..response import success_response

router = APIRouter()


@router.get("/find")
async def find(
    pattern: str,
    kind: Optional[str] = Query(None),
    path: Optional[str] = Query(None),
    body: bool = Query(False),
    depth: int = Query(0),
    exact: bool = Query(False),
    client=Depends(serena),
):
    """Find symbols by pattern."""
    result = await client.find_symbol(
        pattern,
        kind=kind,
        path=path,
        body=body,
        depth=depth,
        exact=exact,
    )
    return success_response(result)


@router.get("/refs")
async def refs(
    symbol: str,
    file: str,
    all: bool = Query(False, alias="all"),
    client=Depends(serena),
):
    """Find references to a symbol."""
    result = await client.find_refs(symbol, file, all_refs=all)
    return success_response(result)


@router.get("/overview")
async def overview(file: str, client=Depends(serena)):
    """Get file structure overview."""
    result = await client.get_overview(file)
    return success_response(result)
