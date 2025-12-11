"""
Workflow and transition operations.

Endpoints:
- GET /transitions/{key} - List available transitions
- POST /transition/{key} - Execute transition (smart multi-step, runtime path-finding)

Deprecated (caching removed in favor of runtime discovery):
- GET /workflows - List cached workflows
- GET /workflow/{issue_type} - Get cached workflow graph
- POST /workflow/discover/{key} - Discover and cache workflow
"""

from fastapi import APIRouter, HTTPException, Query

from ..client import (
    get_client,
    get_workflow_store_sync,
    success_response,
    error_response,
    formatted_response,
)

router = APIRouter()


@router.get("/transitions/{key}")
async def list_transitions(
    key: str,
    format: str = Query("json", description="Output format: json, human, ai, markdown"),
):
    """List available transitions for an issue.

    Shows all transitions currently available from the issue's current state.
    Use this before 'jira transition' to see valid target states.

    Examples:
        jira transitions PROJ-123
        jira transitions PROJ-123 --format human
    """
    client = await get_client()
    try:
        transitions = client.get_issue_transitions(key)
        return formatted_response(transitions, format, "transitions")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transition/{key}")
async def do_transition(
    key: str,
    target: str = Query(..., description="Target state name (e.g., 'In Progress', 'Done')"),
    comment: bool = Query(False, description="Add transition trail as comment"),
    dry_run: bool = Query(False, alias="dryRun", description="Show path without executing"),
    max_steps: int = Query(5, alias="maxSteps", ge=1, le=10, description="Max intermediate transitions (1-10)"),
):
    """Transition issue to target state (smart multi-step).

    Uses runtime path-finding - NO caching, works with any workflow.
    If direct transition isn't available, automatically navigates through
    intermediate states to reach the target.

    Use --dryRun to preview the transition path without making changes.
    Use --maxSteps to limit how many intermediate transitions are allowed.

    Examples:
        jira transition PROJ-123 --target "In Progress"
        jira transition PROJ-123 --target Done --comment
        jira transition PROJ-123 --target "Code Review" --dryRun
        jira transition PROJ-123 --target Done --maxSteps 3
    """
    client = await get_client()

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

        # Get final state
        issue = client.issue(key, fields="status")
        final_state = issue["fields"]["status"]["name"]

        return success_response({
            "key": key,
            "dry_run": dry_run,
            "transitions": [{"id": t.id, "name": t.name, "to": t.to} for t in executed],
            "steps": len(executed),
            "final_state": final_state,
        })
    except Exception as e:
        error_msg = str(e)
        if "path" in error_msg.lower() or "reachable" in error_msg.lower():
            return error_response(
                f"No path to '{target}'",
                hint="Use 'jira transitions ISSUE' to see available states"
            )
        raise HTTPException(status_code=500, detail=error_msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow Cache Management (DEPRECATED - kept for backward compatibility)
# The transition endpoint now uses runtime path-finding, no caching needed.
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/workflows")
async def list_workflows():
    """[DEPRECATED] List cached workflows.

    NOTE: Workflow caching is deprecated. The transition endpoint now uses
    runtime path-finding that works with any workflow without pre-caching.

    Examples:
        jira workflows
    """
    store = get_workflow_store_sync()
    types = store.list_types()
    return success_response({
        "deprecated": True,
        "message": "Workflow caching is deprecated. Use 'jira transition' directly.",
        "cached_types": types,
    })


@router.get("/workflow/{issue_type:path}")
async def get_workflow(issue_type: str):
    """[DEPRECATED] Get cached workflow for issue type.

    NOTE: Workflow caching is deprecated. The transition endpoint now uses
    runtime path-finding that works with any workflow without pre-caching.

    Examples:
        jira workflow Story
    """
    store = get_workflow_store_sync()
    graph = store.get(issue_type)
    if graph is None:
        return error_response(
            f"Workflow for '{issue_type}' not cached (caching is deprecated)",
            hint="Use 'jira transition ISSUE --target STATE' directly - it finds the path at runtime",
            status=404,
        )
    result = graph.to_dict()
    result["deprecated"] = True
    result["message"] = "Workflow caching is deprecated. Use 'jira transition' directly."
    return success_response(result)


@router.post("/workflow/discover/{key}")
async def discover_workflow_endpoint(key: str):
    """[DEPRECATED] Discover and cache workflow from an issue.

    NOTE: This endpoint is deprecated. The transition endpoint now uses
    runtime path-finding that works with any workflow without pre-caching.

    The old discovery method actually MOVED the issue through states,
    which was risky. Runtime path-finding is safer and more reliable.

    Examples:
        jira workflow/discover PROJ-123
    """
    return error_response(
        "Workflow discovery is deprecated",
        hint="Use 'jira transition ISSUE --target STATE' directly - it finds the path at runtime",
        status=410,  # Gone
    )
