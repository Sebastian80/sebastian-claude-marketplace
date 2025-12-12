"""
Project operations.

Endpoints:
- GET /projects - List all projects
- GET /project/{key} - Get project details
- GET /project/{key}/components - Get project components
- GET /project/{key}/versions - Get project versions
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import formatted

router = APIRouter()


@router.get("/projects")
async def list_projects(
    include_archived: bool = Query(False, alias="includeArchived", description="Include archived projects"),
    expand: str | None = Query(None, description="Fields to expand"),
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List all Jira projects."""
    try:
        kwargs = {}
        if include_archived:
            kwargs["included_archived"] = True
        if expand:
            kwargs["expand"] = expand

        projects = client.projects(**kwargs)
        return formatted(projects, format, "projects")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{key}")
async def get_project(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get project details by key."""
    try:
        project = client.project(key)
        return formatted(project, format, "project")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Project {key} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{key}/components")
async def get_project_components(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get project components."""
    try:
        components = client.project_components(key)
        return formatted(components, format, "components")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Project {key} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{key}/versions")
async def get_project_versions(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get project versions."""
    try:
        versions = client.project_versions(key)
        return formatted(versions, format, "versions")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Project {key} not found")
        raise HTTPException(status_code=500, detail=str(e))
