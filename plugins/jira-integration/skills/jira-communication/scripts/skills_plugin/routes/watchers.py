"""
Watcher operations.

Endpoints:
- GET /watchers/{key} - List watchers on issue
- POST /watcher/{key} - Add watcher to issue
- DELETE /watcher/{key}/{username} - Remove watcher from issue
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import success, error, formatted, formatted_error

router = APIRouter()


@router.get("/watchers/{key}")
async def list_watchers(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List watchers on issue."""
    try:
        watchers = client.issue_get_watchers(key)
        return formatted(watchers, format, "watchers")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            return formatted_error(f"Issue {key} not found", fmt=format, status=404)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watcher/{key}")
async def add_watcher(
    key: str,
    username: str = Query(..., description="Username of user to add as watcher"),
    client=Depends(jira),
):
    """Add watcher to issue."""
    try:
        client.issue_add_watcher(key, username)
        return success({"issue_key": key, "username": username, "added": True})
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            return error(f"Issue {key} not found")
        elif "user" in error_msg.lower() and "not found" in error_msg.lower():
            return error(f"User {username} not found")
        elif "permission" in error_msg.lower():
            return error("Permission denied")
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/watcher/{key}/{username}")
async def remove_watcher(key: str, username: str, client=Depends(jira)):
    """Remove watcher from issue."""
    try:
        client.issue_delete_watcher(key, username)
        return success({"issue_key": key, "username": username, "removed": True})
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            return error(f"Issue {key} or watcher {username} not found")
        elif "permission" in error_msg.lower():
            return error("Permission denied")
        raise HTTPException(status_code=500, detail=error_msg)
