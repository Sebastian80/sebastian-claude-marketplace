"""
Memory management endpoints.

Endpoints:
- GET /memory/list - List memories
- GET /memory/read - Read a memory
- POST /memory/write - Write a memory
- POST /memory/delete - Delete a memory
- POST /memory/move - Move/rename a memory
- POST /memory/archive - Archive a memory
- GET /memory/tree - Get memory tree
- GET /memory/search - Search memories
- GET /memory/stats - Get memory statistics
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..deps import serena
from ..response import success_response

router = APIRouter()


@router.get("/memory/list")
async def memory_list(folder: Optional[str] = Query(None), client=Depends(serena)):
    """List memories."""
    result = await client.memory_list(folder)
    return success_response(result)


@router.get("/memory/read")
async def memory_read(name: str, client=Depends(serena)):
    """Read a memory."""
    result = await client.memory_read(name)
    return success_response(result)


@router.post("/memory/write")
async def memory_write(name: str, content: str, client=Depends(serena)):
    """Write a memory."""
    result = await client.memory_write(name, content)
    return success_response(result)


@router.post("/memory/delete")
async def memory_delete(name: str, client=Depends(serena)):
    """Delete a memory."""
    result = await client.memory_delete(name)
    return success_response(result)


@router.post("/memory/move")
async def memory_move(name: str, new_name: str, client=Depends(serena)):
    """Move/rename a memory."""
    result = await client.memory_move(name, new_name)
    return success_response(result)


@router.post("/memory/archive")
async def memory_archive(name: str, client=Depends(serena)):
    """Archive a memory."""
    result = await client.memory_archive(name)
    return success_response(result)


@router.get("/memory/tree")
async def memory_tree(folder: Optional[str] = Query(None), client=Depends(serena)):
    """Get memory tree."""
    result = await client.memory_tree(folder)
    return success_response(result)


@router.get("/memory/search")
async def memory_search(
    pattern: str,
    folder: Optional[str] = Query(None),
    client=Depends(serena),
):
    """Search memories."""
    result = await client.memory_search(pattern, folder)
    return success_response(result)


@router.get("/memory/stats")
async def memory_stats(client=Depends(serena)):
    """Get memory statistics."""
    result = await client.memory_stats()
    return success_response(result)
