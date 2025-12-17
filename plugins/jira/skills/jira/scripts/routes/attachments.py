"""
Attachment operations.

Endpoints:
- GET /attachments/{key} - List attachments on issue
- POST /attachment/{key} - Upload attachment
- DELETE /attachment/{attachment_id} - Delete attachment
"""

import base64

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import success, error, formatted, formatted_error

router = APIRouter()


@router.get("/attachments/{key}")
async def list_attachments(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List attachments on issue."""
    try:
        issue = client.issue(key, fields="attachment")
        attachments = issue.get("fields", {}).get("attachment", [])
        return formatted(attachments, format, "attachments")
    except Exception as e:
        if "does not exist" in str(e).lower() or "404" in str(e):
            return formatted_error(f"Issue {key} not found", fmt=format, status=404)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/attachment/{key}")
async def upload_attachment(
    key: str,
    filename: str = Query(..., description="Name of the file to attach"),
    content: str = Query(..., description="Base64-encoded file content"),
    client=Depends(jira),
):
    """Upload attachment to issue."""
    try:
        try:
            file_data = base64.b64decode(content)
        except Exception:
            return error("Failed to decode base64 content")

        result = client.add_attachment(issue_key=key, filename=filename, attachment=file_data)
        return success(result)
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            return error(f"Issue {key} not found")
        elif "permission" in error_msg.lower():
            return error("Permission denied")
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/attachment/{attachment_id}")
async def delete_attachment(attachment_id: str, client=Depends(jira)):
    """Delete attachment."""
    try:
        client.delete_attachment(attachment_id)
        return success({"attachment_id": attachment_id, "deleted": True})
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return error(f"Attachment {attachment_id} not found", status=404)
        elif "permission" in error_msg.lower():
            return error("Permission denied")
        raise HTTPException(status_code=500, detail=error_msg)
