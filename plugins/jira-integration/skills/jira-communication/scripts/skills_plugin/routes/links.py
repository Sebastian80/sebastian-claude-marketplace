"""
Link operations (issue links and web links).

Manage relationships between issues and external resources.

Issue Links: Connect related issues (blocks, causes, relates to, etc.)
Web Links: Attach external URLs (PRs, docs, etc.) to issues

Endpoints:
- GET /links/{key} - List all links on an issue
- GET /linktypes - List available link types
- GET /link/types - List available link types (alias)
- POST /link - Create link between issues
- POST /weblink/{key} - Add web link to issue
- GET /weblinks/{key} - List web links on issue
- DELETE /weblink/{key}/{link_id} - Remove web link

Examples:
    jira links PROJ-123        # Show all links on issue
    jira linktypes             # Available link type names
    jira link --from PROJ-1 --to PROJ-2 --type Blocks
    jira weblinks PROJ-123     # Show web/remote links
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import get_client, success_response, formatted_response

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# Issue Links
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/links/{key}")
async def get_issue_links(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List all links on an issue.

    Shows both issue links (relationships to other issues) and remote/web links.
    Each link shows the relationship type and linked issue/URL.

    Link directions:
    - Outward: "this issue blocks PROJ-456"
    - Inward: "this issue is blocked by PROJ-123"

    Examples:
        jira links PROJ-123
        jira links PROJ-123 --format human
    """
    client = await get_client()
    try:
        issue = client.issue(key, fields="issuelinks")
        links = issue.get('fields', {}).get('issuelinks', [])
        return formatted_response(links, format, "links")
    except Exception as e:
        error_msg = str(e).lower()
        if "not exist" in error_msg or "not found" in error_msg:
            raise HTTPException(status_code=404, detail=f"Issue {key} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/linktypes")
async def list_link_types_alias(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List available issue link types.

    Shows all relationship types you can use when linking issues.
    Each type has an inward and outward name.

    Common types:
    - Blocks / is blocked by
    - Clones / is cloned by
    - Relates to
    - Causes / is caused by
    - Duplicates / is duplicated by

    Examples:
        jira linktypes
        jira linktypes --format human
    """
    client = await get_client()
    try:
        types = client.get_issue_link_types()
        return formatted_response(types, format, "linktypes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/link")
async def create_link(
    from_key: str = Query(..., alias="from", description="Source issue key"),
    to_key: str = Query(..., alias="to", description="Target issue key"),
    link_type: str = Query(..., alias="type", description="Link type name (use 'jira link/types' to list)"),
):
    """Create link between two issues.

    Links two issues with a relationship type.
    Use 'jira link/types' to see available link types in your Jira.

    Common link types:
    - "Blocks" / "is blocked by" - Dependency
    - "Clones" / "is cloned by" - Duplicate
    - "Relates" - Generic relationship
    - "Causes" / "is caused by" - Root cause

    The direction matters: --from is the outward issue, --to is the inward issue.
    E.g., "PROJ-1 Blocks PROJ-2" means PROJ-1 --from, PROJ-2 --to.

    Examples:
        jira link --from PROJ-123 --to PROJ-456 --type Blocks
        jira link --from PROJ-100 --to PROJ-101 --type Relates
        jira link --from PROJ-200 --to PROJ-201 --type "is cloned by"
    """
    client = await get_client()
    try:
        link_data = {
            "type": {"name": link_type},
            "inwardIssue": {"key": to_key},
            "outwardIssue": {"key": from_key},
        }
        client.create_issue_link(link_data)
        return success_response({"from": from_key, "to": to_key, "type": link_type})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/link/types")
async def list_link_types():
    """List available issue link types.

    Returns all link types configured in your Jira instance.
    Each type has inward and outward names (e.g., "blocks" / "is blocked by").

    Examples:
        jira link/types
    """
    client = await get_client()
    try:
        types = client.get_issue_link_types()
        return success_response(types)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Web Links (Remote Links)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/weblink/{key}")
async def add_weblink(
    key: str,
    url: str = Query(..., description="URL to link"),
    title: str | None = Query(None, description="Link title (defaults to URL)"),
):
    """Add web link (remote link) to issue.

    Attaches an external URL to the issue, visible in the Links section.
    Useful for linking to PRs, documentation, or external resources.

    Examples:
        jira weblink PROJ-123 --url "https://github.com/org/repo/pull/456"
        jira weblink PROJ-123 --url "https://docs.example.com/feature" --title "Feature Docs"
    """
    client = await get_client()
    link_title = title or url

    try:
        link_object = {"url": url, "title": link_title}
        endpoint = f"rest/api/2/issue/{key}/remotelink"
        response = client._session.post(
            f"{client.url}/{endpoint}",
            json={"object": link_object}
        )
        response.raise_for_status()
        result = response.json()
        return success_response({
            "key": key,
            "url": url,
            "title": link_title,
            "id": result.get('id'),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weblinks/{key}")
async def list_weblinks(key: str):
    """List web links on issue.

    Returns all remote/web links attached to the issue.

    Examples:
        jira weblinks PROJ-123
    """
    client = await get_client()
    try:
        endpoint = f"rest/api/2/issue/{key}/remotelink"
        response = client._session.get(f"{client.url}/{endpoint}")
        response.raise_for_status()
        links = response.json()
        return success_response(links)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/weblink/{key}/{link_id}")
async def remove_weblink(key: str, link_id: str):
    """Remove web link from issue.

    Deletes a remote link by its ID. Get IDs from 'jira weblinks ISSUE'.

    Examples:
        jira weblink PROJ-123 12345
    """
    client = await get_client()
    try:
        endpoint = f"rest/api/2/issue/{key}/remotelink/{link_id}"
        response = client._session.delete(f"{client.url}/{endpoint}")
        response.raise_for_status()
        return success_response({"key": key, "link_id": link_id, "removed": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
