"""
Link operations (issue links and web links).

Endpoints:
- GET /links/{key} - List all links on an issue
- GET /linktypes - List available link types
- GET /link/types - List available link types (alias)
- POST /link - Create link between issues
- POST /weblink/{key} - Add web link to issue
- GET /weblinks/{key} - List web links on issue
- DELETE /weblink/{key}/{link_id} - Remove web link
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import success, formatted

router = APIRouter()


@router.get("/links/{key}")
async def get_issue_links(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List all links on an issue."""
    try:
        issue = client.issue(key, fields="issuelinks")
        links = issue.get("fields", {}).get("issuelinks", [])
        return formatted(links, format, "links")
    except Exception as e:
        error_msg = str(e).lower()
        if "not exist" in error_msg or "not found" in error_msg:
            raise HTTPException(status_code=404, detail=f"Issue {key} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/linktypes")
async def list_link_types_alias(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List available issue link types."""
    try:
        types = client.get_issue_link_types()
        return formatted(types, format, "linktypes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/link")
async def create_link(
    from_key: str = Query(..., alias="from", description="Source issue key"),
    to_key: str = Query(..., alias="to", description="Target issue key"),
    link_type: str = Query(..., alias="type", description="Link type name"),
    client=Depends(jira),
):
    """Create link between two issues."""
    try:
        link_data = {
            "type": {"name": link_type},
            "inwardIssue": {"key": to_key},
            "outwardIssue": {"key": from_key},
        }
        client.create_issue_link(link_data)
        return success({"from": from_key, "to": to_key, "type": link_type})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/link/types")
async def list_link_types(client=Depends(jira)):
    """List available issue link types."""
    try:
        types = client.get_issue_link_types()
        return success(types)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/weblink/{key}")
async def add_weblink(
    key: str,
    url: str = Query(..., description="URL to link"),
    title: str | None = Query(None, description="Link title (defaults to URL)"),
    client=Depends(jira),
):
    """Add web link to issue."""
    link_title = title or url
    try:
        link_object = {"url": url, "title": link_title}
        endpoint = f"rest/api/2/issue/{key}/remotelink"
        response = client._session.post(f"{client.url}/{endpoint}", json={"object": link_object})
        response.raise_for_status()
        result = response.json()
        return success({"key": key, "url": url, "title": link_title, "id": result.get("id")})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weblinks/{key}")
async def list_weblinks(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List web links on issue."""
    try:
        endpoint = f"rest/api/2/issue/{key}/remotelink"
        response = client._session.get(f"{client.url}/{endpoint}")
        response.raise_for_status()
        links = response.json()
        return formatted(links, format, "weblinks")
    except Exception as e:
        error_msg = str(e).lower()
        if "not exist" in error_msg or "not found" in error_msg or "404" in error_msg:
            raise HTTPException(status_code=404, detail=f"Issue {key} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/weblink/{key}/{link_id}")
async def remove_weblink(key: str, link_id: str, client=Depends(jira)):
    """Remove web link from issue."""
    try:
        endpoint = f"rest/api/2/issue/{key}/remotelink/{link_id}"
        response = client._session.delete(f"{client.url}/{endpoint}")
        response.raise_for_status()
        return success({"key": key, "link_id": link_id, "removed": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
