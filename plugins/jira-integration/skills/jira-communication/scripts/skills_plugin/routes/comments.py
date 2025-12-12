"""
Comment operations.

Endpoints:
- POST /comment/{key} - Add comment to issue
- GET /comments/{key} - List comments on issue
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import success, formatted

router = APIRouter()


@router.post("/comment/{key}")
async def add_comment(
    key: str,
    text: str = Query(..., description="Comment text (use Jira wiki markup, not Markdown)"),
    client=Depends(jira),
):
    """Add comment to issue."""
    try:
        result = client.issue_add_comment(key, text)
        return success(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comments/{key}")
async def list_comments(
    key: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum comments to return"),
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List comments on issue."""
    try:
        issue = client.issue(key, fields="comment")
        comments = issue.get("fields", {}).get("comment", {}).get("comments", [])
        return formatted(list(reversed(comments))[:limit], format, "comments")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
