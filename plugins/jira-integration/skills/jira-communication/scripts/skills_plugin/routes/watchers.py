"""
Watcher operations.

Endpoints:
- GET /watchers/{key} - List watchers on issue
- POST /watcher/{key} - Add watcher to issue
- DELETE /watcher/{key}/{username} - Remove watcher from issue
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import (
    get_client,
    success_response,
    error_response,
    formatted_response,
    formatted_error,
)

router = APIRouter()


@router.get("/watchers/{key}")
async def list_watchers(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List watchers on issue.

    Returns all users watching the specified issue.
    Watchers receive notifications when the issue is updated.

    Examples:
        jira watchers PROJ-123
        jira watchers PROJ-123 --format human
        jira watchers PROJ-123 --format markdown
    """
    client = await get_client()
    try:
        watchers = client.issue_get_watchers(key)
        return formatted_response(watchers, format, "watchers")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            return formatted_error(f"Issue {key} not found", fmt=format, status=404)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watcher/{key}")
async def add_watcher(
    key: str,
    username: str = Query(..., description="Username of user to add as watcher"),
):
    """Add or remove a watcher from an issue.

    This command supports two operations:
    - POST: Add watcher (with --username)
    - DELETE: Remove watcher (jira watcher/remove ISSUE-KEY USERNAME)

    Add watcher examples:
        jira watcher PROJ-123 --username john.doe
        jira watcher PROJ-123 --username jane.smith

    Remove watcher examples:
        jira watcher/remove PROJ-123 john.doe
        jira watchers PROJ-123  # list current watchers first
    """
    client = await get_client()
    try:
        client.issue_add_watcher(key, username)
        return success_response({
            "issue_key": key,
            "username": username,
            "added": True
        })
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            return error_response(
                f"Issue {key} not found",
                hint="Verify issue key is correct"
            )
        elif "user" in error_msg.lower() and "not found" in error_msg.lower():
            return error_response(
                f"User {username} not found",
                hint="Verify username is correct"
            )
        elif "permission" in error_msg.lower():
            return error_response(
                "Permission denied",
                hint="You may not have permission to add watchers to this issue"
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/watcher/{key}/{username}")
async def remove_watcher(
    key: str,
    username: str,
):
    """Remove watcher from issue.

    Removes a user from the watchers list of the specified issue.
    The user will no longer receive notifications for this issue.

    Examples:
        jira watcher/remove PROJ-123 john.doe
        jira watchers PROJ-123  # to see current watchers first
    """
    client = await get_client()
    try:
        client.issue_delete_watcher(key, username)
        return success_response({
            "issue_key": key,
            "username": username,
            "removed": True
        })
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            return error_response(
                f"Issue {key} or watcher {username} not found",
                hint="Verify issue key and username are correct"
            )
        elif "permission" in error_msg.lower():
            return error_response(
                "Permission denied",
                hint="You may not have permission to remove watchers from this issue"
            )
        raise HTTPException(status_code=500, detail=error_msg)
