#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Jira workflow discovery and visualization."""

import sys
from pathlib import Path

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
from lib.client import get_jira_client
from lib.output import format_output, success, error, warning
from lib.workflow import (
    WorkflowStore,
    WorkflowGraph,
    discover_workflow,
    PathNotFoundError
)


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--env-file', type=click.Path(), help='Environment file path')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json: bool, quiet: bool, env_file: str | None, debug: bool):
    """Jira workflow discovery and visualization.

    Discover, view, and analyze Jira workflows for different issue types.
    """
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json
    ctx.obj['quiet'] = quiet
    ctx.obj['debug'] = debug
    ctx.obj['env_file'] = env_file


@cli.command('discover')
@click.argument('issue_key')
@click.pass_context
def discover(ctx, issue_key: str):
    """Discover workflow from a sample issue.

    ISSUE_KEY: Issue to use for discovery (e.g., PROJ-123)

    Walks the issue through all reachable states to map the complete workflow.
    Saves the result to the workflow store.

    Example:

      jira-workflow discover PROJ-123
    """
    try:
        client = get_jira_client(ctx.obj['env_file'])
    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(str(e))
        sys.exit(1)

    try:
        store = WorkflowStore()
        graph = discover_workflow(
            client,
            issue_key,
            verbose=not ctx.obj['quiet']
        )
        store.save(graph)

        if ctx.obj['json']:
            format_output(graph.to_dict(), as_json=True)
        elif not ctx.obj['quiet']:
            success(f"Workflow saved for '{graph.issue_type}'")
            print(f"  States: {len(graph.states)}")
            print(f"  Transitions: {sum(len(t) for t in graph.states.values())}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Discovery failed: {e}")
        sys.exit(1)


@cli.command('show')
@click.argument('issue_type')
@click.option('--format', '-f', 'fmt',
              type=click.Choice(['ascii', 'table', 'json']),
              default='table', help='Output format')
@click.pass_context
def show(ctx, issue_type: str, fmt: str):
    """Show workflow for an issue type.

    ISSUE_TYPE: Issue type name (e.g., "Sub: Task")

    Example:

      jira-workflow show "Sub: Task"

      jira-workflow show "Sub: Task" --format ascii
    """
    store = WorkflowStore()
    graph = store.get(issue_type)

    if graph is None:
        error(f"Workflow for '{issue_type}' not found")
        print(f"\nKnown types: {', '.join(store.list_types()) or 'none'}")
        print("\nRun 'jira-workflow discover ISSUE-KEY' to map a workflow")
        sys.exit(1)

    if fmt == 'json' or ctx.obj['json']:
        format_output(graph.to_dict(), as_json=True)
    elif fmt == 'ascii':
        print(graph.to_ascii())
    else:
        print(f"Workflow: {graph.issue_type}")
        if graph.discovered_from:
            print(f"Discovered from: {graph.discovered_from}")
        print()
        print(graph.to_table())


@cli.command('list')
@click.pass_context
def list_workflows(ctx):
    """List all known workflows.

    Example:

      jira-workflow list
    """
    store = WorkflowStore()
    types = store.list_types()

    if ctx.obj['json']:
        format_output({'issue_types': types}, as_json=True)
        return

    if not types:
        print("No workflows discovered yet")
        print("\nRun 'jira-workflow discover ISSUE-KEY' to map a workflow")
        return

    print("Known workflows:")
    for t in sorted(types):
        graph = store.get(t)
        states = len(graph.states) if graph else 0
        source = f" (from {graph.discovered_from})" if graph and graph.discovered_from else ""
        print(f"  {t}: {states} states{source}")


@cli.command('path')
@click.argument('issue_type')
@click.option('--from', '-f', 'from_state', required=True, help='Starting state')
@click.option('--to', '-t', 'to_state', required=True, help='Target state')
@click.pass_context
def show_path(ctx, issue_type: str, from_state: str, to_state: str):
    """Show path between two states.

    ISSUE_TYPE: Issue type name (e.g., "Sub: Task")

    Example:

      jira-workflow path "Sub: Task" --from "Offen" --to "Waiting for QA"
    """
    store = WorkflowStore()
    graph = store.get(issue_type)

    if graph is None:
        error(f"Workflow for '{issue_type}' not found")
        sys.exit(1)

    try:
        path = graph.path_to(from_state, to_state)

        if ctx.obj['json']:
            format_output({
                'from': from_state,
                'to': to_state,
                'path': [t.to_dict() for t in path]
            }, as_json=True)
            return

        if not path:
            print(f"Already at '{to_state}'")
            return

        print(f"Path from '{from_state}' to '{to_state}':")
        current = from_state
        for i, t in enumerate(path, 1):
            print(f"  {i}. {t.name} → {t.to}")
            current = t.to

    except PathNotFoundError as e:
        error(f"No path from '{from_state}' to '{to_state}'")
        print(f"  Reachable: {', '.join(sorted(e.reachable))}")
        sys.exit(1)


@cli.command('validate')
@click.argument('issue_type')
@click.pass_context
def validate(ctx, issue_type: str):
    """Validate workflow for dead ends.

    ISSUE_TYPE: Issue type name (e.g., "Sub: Task")

    Example:

      jira-workflow validate "Sub: Task"
    """
    store = WorkflowStore()
    graph = store.get(issue_type)

    if graph is None:
        error(f"Workflow for '{issue_type}' not found")
        sys.exit(1)

    # Find states with no exit (dead ends)
    dead_ends = []
    done_states = {'Fertig', 'Done', 'Geschlossen', 'Closed'}

    for state in graph.all_states():
        if state in done_states:
            continue

        reachable = graph.reachable_from(state)
        if not reachable.intersection(done_states):
            dead_ends.append(state)

    if ctx.obj['json']:
        format_output({
            'issue_type': issue_type,
            'valid': len(dead_ends) == 0,
            'dead_ends': dead_ends
        }, as_json=True)
        return

    print(f"Validating '{issue_type}' workflow...")

    if dead_ends:
        warning(f"Found {len(dead_ends)} dead-end states:")
        for state in dead_ends:
            print(f"  - {state} (no path to done)")
    else:
        success("All states have exit path to done")


@cli.command('refresh')
@click.argument('issue_type')
@click.option('--issue', '-i', required=True, help='Issue to use for re-discovery')
@click.pass_context
def refresh(ctx, issue_type: str, issue: str):
    """Re-discover workflow for an issue type.

    ISSUE_TYPE: Issue type name to refresh

    Example:

      jira-workflow refresh "Sub: Task" --issue PROJ-123
    """
    try:
        client = get_jira_client(ctx.obj['env_file'])
    except Exception as e:
        error(str(e))
        sys.exit(1)

    store = WorkflowStore()

    # Verify issue is correct type
    issue_data = client.issue(issue, fields="issuetype")
    actual_type = issue_data["fields"]["issuetype"]["name"]

    if actual_type != issue_type:
        error(f"Issue {issue} is '{actual_type}', not '{issue_type}'")
        sys.exit(1)

    if not ctx.obj['quiet']:
        print(f"Re-discovering '{issue_type}' from {issue}...")

    graph = discover_workflow(client, issue, verbose=not ctx.obj['quiet'])
    store.save(graph)

    success(f"Workflow refreshed for '{issue_type}'")


if __name__ == '__main__':
    cli()
