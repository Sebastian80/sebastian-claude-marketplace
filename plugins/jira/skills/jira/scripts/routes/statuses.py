"""
Status reference data.

Endpoints:
- GET /statuses - List all statuses
- GET /status/{name} - Get status by name (accepts English or localized names)
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import formatted

router = APIRouter()

# English to common localized name mappings (for JQL compatibility)
# These are standard Jira status names that JQL accepts in English
STATUS_ALIASES = {
    "open": ["offen"],
    "closed": ["geschlossen"],
    "resolved": ["erledigt"],
    "in progress": ["in arbeit"],
    "to do": ["zu erledigen"],
    "done": ["fertig"],
    "new": ["neu"],
    "reopened": ["neueröffnet", "wieder geöffnet"],
}


def normalize_status_name(name: str) -> list[str]:
    """Return list of possible status names to search for."""
    name_lower = name.lower()
    candidates = [name_lower]

    # If English name given, add German aliases
    if name_lower in STATUS_ALIASES:
        candidates.extend(STATUS_ALIASES[name_lower])

    # If German name given, add English equivalent
    for english, aliases in STATUS_ALIASES.items():
        if name_lower in aliases:
            candidates.append(english)
            break

    return candidates


@router.get("/statuses")
async def list_statuses(
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List all statuses."""
    try:
        statuses = client.get_all_statuses()
        return formatted(statuses, format, "statuses")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{name}")
async def get_status(
    name: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """Get status by name (accepts English or localized names)."""
    try:
        all_statuses = client.get_all_statuses()
        candidates = normalize_status_name(name)

        for status in all_statuses:
            status_name_lower = status.get("name", "").lower()
            if status_name_lower in candidates:
                return formatted(status, format, "status")

        raise HTTPException(status_code=404, detail=f"Status '{name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
