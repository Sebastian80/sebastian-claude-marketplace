"""
Project operations.

Endpoints:
- GET /projects - List all projects
- GET /project/{key} - Get project details
- GET /project/{key}/components - Get project components
- GET /project/{key}/versions - Get project versions
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import (
    get_client,
    formatted_response,
)

router = APIRouter()


@router.get("/projects")
async def list_projects(
    include_archived: bool = Query(False, alias="includeArchived", description="Include archived projects"),
    expand: str | None = Query(None, description="Fields to expand (e.g., 'description,lead')"),
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List all Jira projects.

    Returns a list of all projects accessible to the authenticated user.
    By default, archived projects are excluded.

    Examples:
        jira projects
        jira projects --format human
        jira projects --includeArchived
        jira projects --expand "description,lead"
    """
    client = await get_client()
    try:
        kwargs = {}
        if include_archived:
            kwargs['included_archived'] = True
        if expand:
            kwargs['expand'] = expand

        projects = client.projects(**kwargs)
        return formatted_response(projects, format, "projects")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{key}")
async def get_project(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get project details by key.

    Returns comprehensive project information including name, lead,
    description, issue types, and other metadata.

    Examples:
        jira project PROJ
        jira project PROJ --format human
        jira project MYPROJECT --format ai
    """
    client = await get_client()
    try:
        project = client.project(key)
        return formatted_response(project, format, "project")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Project {key} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{key}/components")
async def get_project_components(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get project components.

    Returns all components (logical groupings of issues) defined
    in the specified project.

    Components are used to organize issues by area, module, or team.

    Examples:
        jira project PROJ components
        jira project PROJ components --format human
    """
    client = await get_client()
    try:
        components = client.project_components(key)
        return formatted_response(components, format, "components")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Project {key} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{key}/versions")
async def get_project_versions(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get project versions.

    Returns all versions (releases, sprints) defined in the specified project.
    Includes both released and unreleased versions.

    Versions are used to track which release an issue is targeting or fixed in.

    Examples:
        jira project PROJ versions
        jira project PROJ versions --format human
        jira project MYPROJECT versions --format ai
    """
    client = await get_client()
    try:
        versions = client.project_versions(key)
        return formatted_response(versions, format, "versions")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Project {key} not found")
        raise HTTPException(status_code=500, detail=str(e))
