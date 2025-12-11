"""
Worklog operations (time tracking).

Endpoints:
- GET /worklogs/{key} - List worklogs on issue
- POST /worklog/{key} - Add worklog (log time)
- GET /worklog/{key}/{worklog_id} - Get specific worklog
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import (
    get_client,
    success_response,
    formatted_response,
)

router = APIRouter()


@router.get("/worklogs/{key}")
async def list_worklogs(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List worklogs on issue.

    Returns all time logged against the specified issue.
    Each worklog includes time spent, author, and comment.

    Examples:
        jira worklogs PROJ-123
        jira worklogs PROJ-123 --format human
        jira worklogs PROJ-123 --format ai
    """
    client = await get_client()
    try:
        result = client.issue_get_worklog(key)
        worklogs = result.get('worklogs', [])
        return formatted_response(worklogs, format, "worklogs")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Issue {key} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/worklog/{key}")
async def add_worklog(
    key: str,
    time_spent: str = Query(..., alias="timeSpent", description="Time spent (e.g., '1h 30m', '2d', '30m')"),
    comment: str | None = Query(None, description="Work description (use Jira wiki markup, not Markdown)"),
    started: str | None = Query(None, description="Start time (ISO 8601 format, e.g., '2025-01-15T10:00:00.000+0000')"),
):
    """Add worklog to issue.

    Log time spent on an issue. Time format: Xd Xh Xm (days, hours, minutes).
    Examples: "2h", "1d 4h", "30m", "1d 2h 30m"

    IMPORTANT: Use Jira wiki markup in comment, NOT Markdown:
    - Bold: *text* (not **text**)
    - Code: {{code}} (not `code`)
    - Headings: h2. Title (not ## Title)

    Examples:
        jira worklog PROJ-123 --timeSpent "2h"
        jira worklog PROJ-123 --timeSpent "1d 4h" --comment "Implementation complete"
        jira worklog PROJ-123 --timeSpent "30m" --comment "Code review"
        jira worklog PROJ-123 --timeSpent "3h" --started "2025-01-15T10:00:00.000+0000"
    """
    client = await get_client()
    try:
        kwargs = {'comment': comment} if comment else {}
        if started:
            kwargs['started'] = started

        result = client.issue_add_worklog(key, time_spent, **kwargs)
        return success_response(result)
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            raise HTTPException(status_code=404, detail=f"Issue {key} not found")
        elif "time" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"{error_msg}. Use format like '2h', '1d 4h', '30m'"
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/worklog/{key}/{worklog_id}")
async def get_worklog(
    key: str,
    worklog_id: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get specific worklog by ID.

    Returns details of a single worklog entry including author,
    time spent, comment, and timestamps.

    Examples:
        jira worklog PROJ-123 12345
        jira worklog PROJ-123 12345 --format human
    """
    client = await get_client()
    try:
        worklog = client.issue_worklog(key, worklog_id)
        return formatted_response(worklog, format, "worklog")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Worklog {worklog_id} not found on issue {key}")
        raise HTTPException(status_code=500, detail=str(e))
