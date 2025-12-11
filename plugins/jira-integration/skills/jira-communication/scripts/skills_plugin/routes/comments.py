"""
Comment operations.

Endpoints:
- POST /comment/{key} - Add comment to issue
- GET /comments/{key} - List comments on issue
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, success_response, formatted_response

router = APIRouter()


@router.post("/comment/{key}")
async def add_comment(
    key: str,
    text: str = Query(..., description="Comment text (use Jira wiki markup, not Markdown)"),
):
    """Add comment to issue.

    Creates a new comment on the specified issue.

    IMPORTANT: Use Jira wiki markup syntax, NOT Markdown:
    - Bold: *text* (not **text**)
    - Italic: _text_ (not *text*)
    - Code inline: {{code}} (not `code`)
    - Code block: {code}...{code} (not ```)
    - Links: [title|url] (not [title](url))
    - Headings: h2. Title (not ## Title)
    - Lists: * item or # item (not - item)

    Examples:
        jira comment PROJ-123 --text "Working on this now"
        jira comment PROJ-123 --text "*Important:* Found the root cause"
        jira comment PROJ-123 --text "See [docs|https://example.com]"
    """
    client = await get_client()
    try:
        result = client.issue_add_comment(key, text)
        return success_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comments/{key}")
async def list_comments(
    key: str,
    limit: int = Query(10, description="Maximum comments to return (most recent first)"),
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List comments on issue.

    Returns comments in reverse chronological order (most recent first).

    Examples:
        jira comments PROJ-123
        jira comments PROJ-123 --limit 5
        jira comments PROJ-123 --format human
    """
    client = await get_client()
    try:
        issue = client.issue(key, fields='comment')
        comments = issue.get('fields', {}).get('comment', {}).get('comments', [])
        return formatted_response(list(reversed(comments))[:limit], format, "comments")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
