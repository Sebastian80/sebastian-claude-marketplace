"""
Field reference data.

Endpoints:
- GET /fields - List all fields
- GET /fields/custom - List only custom fields
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, formatted_response

router = APIRouter()


@router.get("/fields")
async def list_fields(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List all fields.

    Returns all fields available in Jira, including both system fields
    (summary, description, status, etc.) and custom fields.

    Custom fields have IDs like "customfield_10001".

    Examples:
        jira fields
        jira fields --format human
    """
    client = await get_client()
    try:
        fields = client.get_all_fields()
        return formatted_response(fields, format, "fields")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fields/custom")
async def list_custom_fields(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List only custom fields.

    Returns only custom fields, filtering out system fields.
    Custom fields have IDs starting with "customfield_".

    Use this to discover available custom fields for your instance
    without the noise of system fields.

    Examples:
        jira fields custom
        jira fields custom --format human
    """
    client = await get_client()
    try:
        all_fields = client.get_all_fields()
        custom_fields = [f for f in all_fields if f.get('id', '').startswith('customfield_')]
        return formatted_response(custom_fields, format, "custom_fields")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
