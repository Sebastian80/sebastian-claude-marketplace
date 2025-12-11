"""
Attachment operations.

Endpoints:
- GET /attachments/{key} - List attachments on issue
- POST /attachment/{key} - Upload attachment
- DELETE /attachment/{attachment_id} - Delete attachment
"""

import base64
from fastapi import APIRouter, HTTPException, Query

from ..client import (
    get_client,
    success_response,
    error_response,
    formatted_response,
    formatted_error,
)

router = APIRouter()


@router.get("/attachments/{key}")
async def list_attachments(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List attachments on issue.

    Returns all files attached to the specified issue.
    Each attachment includes id, filename, size, mimeType, and download URL.

    Examples:
        jira attachments PROJ-123
        jira attachments PROJ-123 --format human
        jira attachments PROJ-123 --format markdown
    """
    client = await get_client()
    try:
        issue = client.issue(key, fields='attachment')
        attachments = issue.get('fields', {}).get('attachment', [])
        return formatted_response(attachments, format, "attachments")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            return formatted_error(f"Issue {key} not found", fmt=format, status=404)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/attachment/{key}")
async def upload_attachment(
    key: str,
    filename: str = Query(..., description="Name of the file to attach"),
    content: str = Query(..., description="Base64-encoded file content"),
):
    """Upload or delete an attachment.

    This command supports two operations:
    - POST: Upload attachment (with --filename and --content)
    - DELETE: Delete attachment (jira attachment/delete ATTACHMENT_ID)

    Upload attachment examples:
        jira attachment PROJ-123 --filename "screenshot.png" --content "$(base64 -w0 screenshot.png)"
        jira attachment PROJ-123 --filename "logs.txt" --content "$(base64 -w0 logs.txt)"

    Delete attachment examples:
        jira attachment/delete 12345
        jira attachments PROJ-123  # list attachments first to get IDs
    """
    client = await get_client()
    try:
        # Decode base64 content
        try:
            file_data = base64.b64decode(content)
        except Exception:
            return error_response(
                "Failed to decode base64 content",
                hint="Ensure content is valid base64-encoded data"
            )

        # Upload attachment
        result = client.add_attachment(issue_key=key, filename=filename, attachment=file_data)
        return success_response(result)
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            return error_response(f"Issue {key} not found", hint="Verify issue key is correct")
        elif "permission" in error_msg.lower():
            return error_response(
                "Permission denied",
                hint="You may not have permission to attach files to this issue"
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/attachment/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
):
    """Delete attachment.

    Removes an attachment from Jira by its attachment ID.
    Use 'jira attachments ISSUE-KEY' to get attachment IDs.

    Examples:
        jira attachment/delete 12345
        jira attachments PROJ-123  # to see attachment IDs first
    """
    client = await get_client()
    try:
        client.delete_attachment(attachment_id)
        return success_response({"attachment_id": attachment_id, "deleted": True})
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error_response(
                f"Attachment {attachment_id} not found",
                hint="Verify attachment ID is correct"
            )
        elif "permission" in error_msg.lower():
            return error_response(
                "Permission denied",
                hint="You may not have permission to delete this attachment"
            )
        raise HTTPException(status_code=500, detail=error_msg)
