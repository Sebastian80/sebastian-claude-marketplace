"""
Issue CRUD operations.

Core operations for working with Jira issues: viewing, creating, and updating.

Endpoints:
- GET /issue/{key} - Get issue details with optional field filtering
- POST /create - Create new issue with required and optional fields
- PATCH /issue/{key} - Update specific fields on existing issue
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import success, error, formatted, formatted_error

router = APIRouter()


@router.get("/issue/{key}")
async def get_issue(
    key: str,
    fields: str | None = Query(None, description="Comma-separated fields to return"),
    expand: str | None = Query(None, description="Fields to expand (e.g., 'changelog')"),
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get issue details by key."""
    params = {}
    if fields:
        params["fields"] = fields
    if expand:
        params["expand"] = expand

    try:
        issue = client.issue(key, **params)
        return formatted(issue, format, "issue")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            return formatted_error(f"Issue {key} not found", fmt=format, status=404)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_issue(
    project: str = Query(..., description="Project key"),
    summary: str = Query(..., description="Issue title/summary"),
    issue_type: str = Query(..., alias="type", description="Issue type: Story, Bug, Task, etc."),
    description: str | None = Query(None, description="Issue description"),
    priority: str | None = Query(None, description="Priority: Highest, High, Medium, Low, Lowest"),
    labels: str | None = Query(None, description="Comma-separated labels"),
    assignee: str | None = Query(None, description="Username or email of assignee"),
    parent: str | None = Query(None, description="Parent issue key (for subtasks)"),
    client=Depends(jira),
):
    """Create new issue in Jira."""
    issue_fields = {
        "project": {"key": project},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }
    if description:
        issue_fields["description"] = description
    if priority:
        issue_fields["priority"] = {"name": priority}
    if labels:
        issue_fields["labels"] = [label.strip() for label in labels.split(",")]
    if assignee:
        if "@" in assignee:
            issue_fields["assignee"] = {"emailAddress": assignee}
        else:
            issue_fields["assignee"] = {"name": assignee}
    if parent:
        issue_fields["parent"] = {"key": parent}

    try:
        result = client.create_issue(fields=issue_fields)
        return success(result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/issue/{key}")
async def update_issue(
    key: str,
    summary: str | None = Query(None, description="New issue summary/title"),
    priority: str | None = Query(None, description="Priority: Highest, High, Medium, Low, Lowest"),
    labels: str | None = Query(None, description="Comma-separated labels (replaces existing)"),
    assignee: str | None = Query(None, description="Username or email of assignee"),
    client=Depends(jira),
):
    """Update issue fields."""
    update_fields = {}

    if summary:
        update_fields["summary"] = summary
    if priority:
        update_fields["priority"] = {"name": priority}
    if labels:
        update_fields["labels"] = [label.strip() for label in labels.split(",")]
    if assignee:
        if "@" in assignee:
            update_fields["assignee"] = {"emailAddress": assignee}
        else:
            update_fields["assignee"] = {"name": assignee}

    if not update_fields:
        return error("No fields specified to update")

    try:
        client.update_issue_field(key, update_fields)
        return success({"key": key, "updated": list(update_fields.keys())})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
