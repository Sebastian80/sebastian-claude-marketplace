"""
Workflow and transition operations.

Endpoints:
- GET /transitions/{key} - List available transitions
- POST /transition/{key} - Execute transition (smart multi-step, runtime path-finding)
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import jira
from ..response import success, error, formatted

router = APIRouter()


@router.get("/transitions/{key}")
async def list_transitions(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
    client=Depends(jira),
):
    """List available transitions for an issue."""
    try:
        transitions = client.get_issue_transitions(key)
        return formatted(transitions, format, "transitions")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transition/{key}")
async def do_transition(
    key: str,
    target: str = Query(..., description="Target state name (e.g., 'In Progress', 'Done')"),
    comment: bool = Query(False, description="Add transition trail as comment"),
    dry_run: bool = Query(False, alias="dryRun", description="Show path without executing"),
    max_steps: int = Query(5, alias="maxSteps", ge=1, le=10, description="Max intermediate transitions (1-10)"),
    client=Depends(jira),
):
    """Transition issue to target state (smart multi-step)."""
    try:
        from lib.workflow import smart_transition

        executed = smart_transition(
            client=client,
            issue_key=key,
            target_state=target,
            add_comment=comment,
            dry_run=dry_run,
            max_steps=max_steps,
        )

        issue = client.issue(key, fields="status")
        final_state = issue["fields"]["status"]["name"]

        return success({
            "key": key,
            "dry_run": dry_run,
            "transitions": [{"id": t.id, "name": t.name, "to": t.to} for t in executed],
            "steps": len(executed),
            "final_state": final_state,
        })
    except Exception as e:
        error_msg = str(e)
        if "path" in error_msg.lower() or "reachable" in error_msg.lower():
            return error(f"No path to '{target}'", hint="Use 'jira transitions ISSUE' to see available states")
        raise HTTPException(status_code=500, detail=error_msg)
