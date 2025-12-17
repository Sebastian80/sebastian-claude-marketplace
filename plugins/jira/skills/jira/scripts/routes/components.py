"""
Component operations.

Endpoints:
- GET /components/{project} - List components in project
- POST /component - Create component
- GET /component/{component_id} - Get component details
- DELETE /component/{component_id} - Delete component
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import success, error, formatted

router = APIRouter()


@router.get("/components/{project}")
async def list_components(
    project: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List components in a project."""
    try:
        components = client.get_project_components(project)
        return formatted(components, format, "components")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error(f"Project '{project}' not found", status=404)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/component")
async def create_component(
    project: str = Query(..., description="Project key"),
    name: str = Query(..., description="Component name"),
    description: str = Query(None, description="Component description"),
    lead: str = Query(None, description="Component lead username"),
    client=Depends(jira),
):
    """Create a component."""
    try:
        component = {"name": name, "project": project}
        if description:
            component["description"] = description
        if lead:
            component["leadUserName"] = lead

        result = client.create_component(component)
        return success(result)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error(f"Project '{project}' not found")
        if "already exists" in error_msg.lower():
            return error(f"Component '{name}' already exists in {project}")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/component/{component_id}")
async def get_component(
    component_id: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get component details."""
    try:
        component = client.component(component_id)
        return formatted(component, format, "component")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error(f"Component '{component_id}' not found", status=404)
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/component/{component_id}")
async def delete_component(component_id: str, client=Depends(jira)):
    """Delete a component."""
    try:
        client.delete_component(component_id)
        return success({"deleted": True, "component_id": component_id})
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error(f"Component '{component_id}' not found", status=404)
        raise HTTPException(status_code=500, detail=error_msg)
