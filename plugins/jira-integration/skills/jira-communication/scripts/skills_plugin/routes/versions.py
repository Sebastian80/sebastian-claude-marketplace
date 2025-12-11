"""
Version/Release operations.

Endpoints:
- GET /versions/{project} - List versions in project
- POST /version - Create version
- GET /version/{version_id} - Get version details
- PATCH /version/{version_id} - Update version (release, rename, describe)
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, success_response, formatted_response, error_response

router = APIRouter()


@router.get("/versions/{project}")
async def list_versions(
    project: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List versions in a project.

    Returns all versions/releases defined for the specified project.
    Versions are used to track release cycles and group issues by target release.

    Examples:
        jira versions PROJ
        jira versions PROJ --format human
        jira versions HMKG --format markdown
    """
    client = await get_client()
    try:
        versions = client.get_project_versions(project)
        return formatted_response(versions, format, "versions")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error_response(
                f"Project '{project}' not found",
                hint="Check project key is correct (case-sensitive)",
                status=404,
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/version")
async def create_version(
    project: str = Query(..., description="Project key (e.g., 'PROJ')"),
    name: str = Query(..., description="Version name (e.g., 'v1.2.0', 'Sprint 23')"),
    description: str = Query(None, description="Version description"),
    released: bool = Query(False, description="Mark version as released"),
):
    """Create, get, or update a version.

    This command supports multiple operations:
    - POST: Create new version (with --project and --name)
    - GET: Get version details by ID (jira version VERSION_ID)
    - PATCH: Update version (jira version/update VERSION_ID --name/--released)

    Create version examples:
        jira version --project PROJ --name "v1.2.0"
        jira version --project PROJ --name "Sprint 23" --description "Q4 Sprint"
        jira version --project HMKG --name "v2.0.0" --released true

    Get version examples:
        jira version 10345
        jira version 10345 --format human

    Update version examples:
        jira version/update 10345 --name "v1.2.1"
        jira version/update 10345 --released true
    """
    client = await get_client()
    try:
        result = client.create_version(
            name=name,
            project=project,
            description=description,
            released=released,
        )
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
                f"Version '{name}' already exists in {project}",
                hint="Use a different version name or update the existing version",
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/version/{version_id}")
async def get_version(
    version_id: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """Get version details.

    Returns full details for a specific version including name, description,
    release status, and associated project information.

    Examples:
        jira version 10345
        jira version 10345 --format human
    """
    client = await get_client()
    try:
        version = client.get_version(version_id)
        return formatted_response(version, format, "version")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=f"Version '{version_id}' not found. Use 'jira versions PROJECT' to list available versions."
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.patch("/version/{version_id}")
async def update_version(
    version_id: str,
    name: str = Query(None, description="New version name"),
    description: str = Query(None, description="New description"),
    released: bool = Query(None, description="Release status (true/false)"),
):
    """Update a version.

    Updates version properties such as name, description, or release status.
    At least one field must be provided to update.

    Use this to:
    - Rename a version
    - Update the description
    - Mark a version as released or unreleased

    Examples:
        jira version/update 10345 --name "v1.2.1"
        jira version/update 10345 --description "Bug fix release"
        jira version/update 10345 --released true
        jira version/update 10345 --name "v1.3.0" --released false
    """
    client = await get_client()

    # Ensure at least one field is provided
    if name is None and description is None and released is None:
        return error_response(
            "At least one field must be provided",
            hint="Provide --name, --description, or --released",
        )

    try:
        result = client.update_version(
            version_id=version_id,
            name=name,
            description=description,
            released=released,
        )
        return success_response(result)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error_response(
                f"Version '{version_id}' not found",
                hint="Use 'jira versions PROJECT' to list available versions",
                status=404,
            )
        if "already exists" in error_msg.lower():
            return error_response(
                f"Version name '{name}' already exists",
                hint="Use a different version name",
            )
        raise HTTPException(status_code=500, detail=error_msg)
