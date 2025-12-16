"""
Worklog operations (time tracking).

Endpoints:
- GET /worklogs/{key} - List worklogs on issue
- POST /worklog/{key} - Add worklog (log time)
- GET /worklog/{key}/{worklog_id} - Get specific worklog
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import success, formatted

router = APIRouter()


@router.get("/worklogs/{key}")
async def list_worklogs(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List worklogs on issue."""
    try:
        result = client.issue_get_worklog(key)
        worklogs = result.get("worklogs", [])
        return formatted(worklogs, format, "worklogs")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Issue {key} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/worklog/{key}")
async def add_worklog(
    key: str,
    time_spent: str = Query(..., alias="timeSpent", description="Time spent (e.g., '1h 30m', '2d', '30m')"),
    comment: str | None = Query(None, description="Work description"),
    started: str | None = Query(None, description="Start time (ISO 8601 format)"),
    client=Depends(jira),
):
    """Add worklog to issue."""
    try:
        kwargs = {"comment": comment} if comment else {}
        if started:
            kwargs["started"] = started

        result = client.issue_add_worklog(key, time_spent, **kwargs)
        return success(result)
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            raise HTTPException(status_code=404, detail=f"Issue {key} not found")
        elif "time" in error_msg.lower():
            raise HTTPException(status_code=400, detail=f"{error_msg}. Use format like '2h', '1d 4h', '30m'")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/worklog/{key}/{worklog_id}")
async def get_worklog(
    key: str,
    worklog_id: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get specific worklog by ID."""
    try:
        url = f"rest/api/2/issue/{key}/worklog/{worklog_id}"
        worklog = client.get(url)
        return formatted(worklog, format, "worklog")
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            raise HTTPException(status_code=404, detail=f"Worklog {worklog_id} not found on issue {key}")
        raise HTTPException(status_code=500, detail=error_msg)
