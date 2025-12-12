"""
Version/Release operations.

Endpoints:
- GET /versions/{project} - List versions in project
- POST /version - Create version
- GET /version/{version_id} - Get version details
- PATCH /version/{version_id} - Update version
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import success, error, formatted

router = APIRouter()


@router.get("/versions/{project}")
async def list_versions(
    project: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List versions in a project."""
    try:
        versions = client.get_project_versions(project)
        return formatted(versions, format, "versions")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error(f"Project '{project}' not found", status=404)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/version")
async def create_version(
    project: str = Query(..., description="Project key"),
    name: str = Query(..., description="Version name"),
    description: str = Query(None, description="Version description"),
    released: bool = Query(False, description="Mark as released"),
    client=Depends(jira),
):
    """Create a version."""
    try:
        result = client.create_version(
            name=name, project=project, description=description, released=released
        )
        return success(result)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error(f"Project '{project}' not found")
        if "already exists" in error_msg.lower():
            return error(f"Version '{name}' already exists in {project}")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/version/{version_id}")
async def get_version(
    version_id: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get version details."""
    try:
        version = client.get_version(version_id)
        return formatted(version, format, "version")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=f"Version '{version_id}' not found")
        raise HTTPException(status_code=500, detail=error_msg)


@router.patch("/version/{version_id}")
async def update_version(
    version_id: str,
    name: str = Query(None, description="New version name"),
    description: str = Query(None, description="New description"),
    released: bool = Query(None, description="Release status"),
    client=Depends(jira),
):
    """Update a version."""
    if name is None and description is None and released is None:
        return error("At least one field must be provided")

    try:
        result = client.update_version(
            version_id=version_id, name=name, description=description, released=released
        )
        return success(result)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error(f"Version '{version_id}' not found", status=404)
        if "already exists" in error_msg.lower():
            return error(f"Version name '{name}' already exists")
        raise HTTPException(status_code=500, detail=error_msg)
