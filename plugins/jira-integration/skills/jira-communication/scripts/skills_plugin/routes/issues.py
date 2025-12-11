"""
Issue CRUD operations.

Endpoints:
- GET /issue/{key} - Get issue details
- POST /create - Create new issue
- PATCH /issue/{key} - Update issue fields
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


@router.get("/issue/{key}")
async def get_issue(
    key: str,
    fields: str | None = Query(None, description="Comma-separated fields to return"),
    expand: str | None = Query(None, description="Fields to expand (e.g., 'changelog')"),
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get issue details by key.

    Fetches full issue details including all fields by default.
    Use --fields to limit returned data for faster responses.

    Examples:
        jira issue PROJ-123
        jira issue PROJ-123 --format human
        jira issue PROJ-123 --fields summary,status,assignee
        jira issue PROJ-123 --expand changelog
    """
    client = await get_client()
    params = {}
    if fields:
        params['fields'] = fields
    if expand:
        params['expand'] = expand

    try:
        issue = client.issue(key, **params)
        return formatted_response(issue, format, "issue")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            return formatted_error(f"Issue {key} not found", fmt=format, status=404)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_issue(
    project: str = Query(..., description="Project key (e.g., 'PROJ')"),
    summary: str = Query(..., description="Issue title/summary"),
    issue_type: str = Query(..., alias="type", description="Issue type: Story, Bug, Task, 'Technical task', etc."),
    description: str | None = Query(None, description="Issue description (use Jira wiki markup, not Markdown)"),
    priority: str | None = Query(None, description="Priority: Highest, High, Medium, Low, Lowest"),
    labels: str | None = Query(None, description="Comma-separated labels"),
    assignee: str | None = Query(None, description="Username or email of assignee"),
    parent: str | None = Query(None, description="Parent issue key (for subtasks)"),
):
    """Create new issue in Jira.

    Creates an issue with the specified type, summary, and optional fields.
    For subtasks, provide --parent with the parent issue key.

    IMPORTANT: Use Jira wiki markup in description, NOT Markdown:
    - Bold: *text* (not **text**)
    - Code: {{code}} (not `code`)
    - Headings: h2. Title (not ## Title)

    Examples:
        jira create --project PROJ --type Story --summary "New feature"
        jira create --project PROJ --type Bug --summary "Fix login" --priority High
        jira create --project PROJ --type "Technical task" --summary "Refactor" --labels "tech-debt"
        jira create --project PROJ --type Sub-task --summary "Subtask" --parent PROJ-100
    """
    client = await get_client()
    fields = {
        'project': {'key': project},
        'summary': summary,
        'issuetype': {'name': issue_type},
    }
    if description:
        fields['description'] = description
    if priority:
        fields['priority'] = {'name': priority}
    if labels:
        fields['labels'] = [l.strip() for l in labels.split(',')]
    if assignee:
        if '@' in assignee:
            fields['assignee'] = {'emailAddress': assignee}
        else:
            fields['assignee'] = {'name': assignee}
    if parent:
        fields['parent'] = {'key': parent}

    try:
        result = client.create_issue(fields=fields)
        return success_response(result)
    except Exception as e:
        error_msg = str(e)
        hint = None
        if "issuetype" in error_msg.lower():
            hint = "Use 'jira search --jql \"project=PROJ\" --fields issuetype' to see valid types"
        elif "project" in error_msg.lower():
            hint = "Check project key is correct"
        raise HTTPException(status_code=400, detail=error_msg)


@router.patch("/issue/{key}")
async def update_issue(
    key: str,
    summary: str | None = Query(None, description="New issue summary/title"),
    priority: str | None = Query(None, description="Priority: Highest, High, Medium, Low, Lowest"),
    labels: str | None = Query(None, description="Comma-separated labels (replaces existing)"),
    assignee: str | None = Query(None, description="Username or email of assignee"),
):
    """Update issue fields.

    Updates one or more fields on an existing issue.
    Only specified fields are updated; others remain unchanged.

    Examples:
        jira issue PROJ-123 --summary "Updated title"
        jira issue PROJ-123 --priority High --assignee john.doe
        jira issue PROJ-123 --labels "urgent,backend"
    """
    client = await get_client()
    update_fields = {}

    if summary:
        update_fields['summary'] = summary
    if priority:
        update_fields['priority'] = {'name': priority}
    if labels:
        update_fields['labels'] = [l.strip() for l in labels.split(',')]
    if assignee:
        if '@' in assignee:
            update_fields['assignee'] = {'emailAddress': assignee}
        else:
            update_fields['assignee'] = {'name': assignee}

    if not update_fields:
        return error_response("No fields specified to update", hint="Provide at least one field to update")

    try:
        client.update_issue_field(key, update_fields)
        return success_response({"key": key, "updated": list(update_fields.keys())})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
