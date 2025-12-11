"""
Component operations.

Endpoints:
- GET /components/{project} - List components in project
- POST /component - Create component
- GET /component/{component_id} - Get component details
- DELETE /component/{component_id} - Delete component
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, success_response, formatted_response, error_response

router = APIRouter()


@router.get("/components/{project}")
async def list_components(
    project: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List components in a project.

    Returns all components defined for the specified project.
    Components are used to categorize issues within a project
    (e.g., Backend, Frontend, Database, API).

    Examples:
        jira components PROJ
        jira components PROJ --format human
        jira components HMKG --format markdown
    """
    client = await get_client()
    try:
        components = client.get_project_components(project)
        return formatted_response(components, format, "components")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error_response(
                f"Project '{project}' not found",
                hint="Check project key is correct (case-sensitive)",
                status=404,
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/component")
async def create_component(
    project: str = Query(..., description="Project key (e.g., 'PROJ')"),
    name: str = Query(..., description="Component name"),
    description: str = Query(None, description="Component description"),
    lead: str = Query(None, description="Component lead username"),
):
    """Create a new component.

    Creates a component in the specified project for categorizing issues.
    Components help organize issues by area (e.g., Backend, Frontend, Infrastructure).

    Examples:
        jira component --project PROJ --name "Backend"
        jira component --project PROJ --name "Frontend" --description "UI components"
        jira component --project HMKG --name "API" --lead john.doe
    """
    client = await get_client()
    try:
        component = {
            "name": name,
            "project": project,
        }
        if description:
            component["description"] = description
        if lead:
            component["leadUserName"] = lead

        result = client.create_component(component)
        return success_response(result)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error_response(
                f"Project '{project}' not found",
                hint="Check project key is correct",
            )
        if "already exists" in error_msg.lower():
            return error_response(
                f"Component '{name}' already exists in {project}",
                hint="Use a different component name",
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/component/{component_id}")
async def get_component(
    component_id: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get component details.

    Returns full details for a specific component including name, description,
    lead, and associated project information.

    Examples:
        jira component 10234
        jira component 10234 --format human
    """
    client = await get_client()
    try:
        component = client.component(component_id)
        return formatted_response(component, format, "component")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error_response(
                f"Component '{component_id}' not found",
                hint="Use 'jira components PROJECT' to list available components",
                status=404,
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/component/{component_id}")
async def delete_component(
    component_id: str,
):
    """Delete a component.

    Permanently removes a component from the project.
    Issues assigned to this component will not be deleted,
    but the component assignment will be cleared.

    Examples:
        jira component/delete 10234
    """
    client = await get_client()
    try:
        client.delete_component(component_id)
        return success_response({
            "deleted": True,
            "component_id": component_id,
        })
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error_response(
                f"Component '{component_id}' not found",
                hint="Component may have already been deleted",
                status=404,
            )
        raise HTTPException(status_code=500, detail=error_msg)
