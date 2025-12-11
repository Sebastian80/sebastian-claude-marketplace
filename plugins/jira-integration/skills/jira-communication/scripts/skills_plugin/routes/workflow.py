"""
Workflow and transition operations.

Endpoints:
- GET /transitions/{key} - List available transitions
- POST /transition/{key} - Execute transition (smart multi-step)
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
):
    """Transition issue to target state (smart multi-step).

    Automatically finds the shortest path through workflow states.
    If direct transition isn't available, executes intermediate transitions.

    Use --dryRun to preview the transition path without making changes.

    Examples:
        jira transition PROJ-123 --target "In Progress"
        jira transition PROJ-123 --target Done --comment
        jira transition PROJ-123 --target "Code Review" --dryRun
    """
    client = await get_client()
    store = get_workflow_store_sync()

    try:
        from lib.workflow import smart_transition
        executed = smart_transition(
            client=client,
            issue_key=key,
            target_state=target,
            store=store,
            add_comment=comment,
            dry_run=dry_run,
        )

        return success_response({
            "key": key,
            "dry_run": dry_run,
            "transitions": [{"id": t.id, "name": t.name, "to": t.to} for t in executed],
            "final_state": executed[-1].to if executed else target,
        })
    except Exception as e:
        error_msg = str(e)
        if "path" in error_msg.lower():
            return error_response(
                f"No path to '{target}'",
                hint="Use 'jira transitions ISSUE' to see available states"
            )
        raise HTTPException(status_code=500, detail=error_msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow Cache Management
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/workflows")
async def list_workflows():
    """List cached workflows.

    Shows all issue types with cached workflow graphs.
    Workflows are cached to enable smart multi-step transitions.

    Examples:
        jira workflows
    """
    store = get_workflow_store_sync()
    types = store.list_types()
    return success_response(types)


@router.get("/workflow/{issue_type:path}")
async def get_workflow(issue_type: str):
    """Get cached workflow for issue type.

    Returns the workflow graph showing states and transitions.
    Use this to understand the workflow before transitioning.

    Examples:
        jira workflow Story
        jira workflow "Technical task"
        jira workflow Bug
    """
    store = get_workflow_store_sync()
    graph = store.get(issue_type)
    if graph is None:
        return error_response(
            f"Workflow for '{issue_type}' not cached",
            hint="Use 'jira workflow/discover ISSUE-KEY' to cache",
            status=404,
        )
    return success_response(graph.to_dict())


@router.post("/workflow/discover/{key}")
async def discover_workflow(key: str):
    """Discover and cache workflow from an issue.

    Explores all possible states and transitions for the issue type.
    The cached workflow enables smart multi-step transitions.

    Examples:
        jira workflow/discover PROJ-123
    """
    client = await get_client()
    store = get_workflow_store_sync()

    try:
        from lib.workflow import discover_workflow
        graph = discover_workflow(client, key, verbose=False)
        store.save(graph)
        return success_response({
            "issue_type": graph.issue_type,
            "states": len(graph.all_states()),
            "cached": True,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
