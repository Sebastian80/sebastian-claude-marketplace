#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Jira issue transitions - list available transitions and change issue status."""

import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# Shared library import (TR1.1.1 - PYTHONPATH approach)
# ═══════════════════════════════════════════════════════════════════════════════
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
from lib.client import get_jira_client
from lib.output import format_output, format_table, success, error, warning
from lib.workflow import (
    WorkflowStore,
    smart_transition,
    PathNotFoundError,
    WorkflowNotFoundError,
    TransitionFailedError
)

# ═══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════


def _get_to_status(transition: dict) -> str:
    """Get target status name from transition, handling both Cloud and Server formats.

    Cloud returns: {'to': {'name': 'In Progress', ...}}
    Server/DC returns: {'to': 'In Progress'}
    """
    to_value = transition.get('to', '')
    if isinstance(to_value, dict):
        return to_value.get('name', '')
    return str(to_value)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Definition
# ═══════════════════════════════════════════════════════════════════════════════


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--env-file', type=click.Path(), help='Environment file path')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json: bool, quiet: bool, env_file: str | None, debug: bool):
    """Jira issue transitions.

    List available transitions and change issue status.
    """
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json
    ctx.obj['quiet'] = quiet
    ctx.obj['debug'] = debug
    try:
        ctx.obj['client'] = get_jira_client(env_file)
    except Exception as e:
        if debug:
            raise
        error(str(e))
        sys.exit(1)


@cli.command('list')
@click.argument('issue_key')
@click.pass_context
def list_transitions(ctx, issue_key: str):
    """List available transitions for an issue.

    ISSUE_KEY: The Jira issue key (e.g., PROJ-123)

    Shows all valid status transitions from the issue's current state.

    Example:

      jira-transition list PROJ-123
    """
    client = ctx.obj['client']

    try:
        transitions = client.get_issue_transitions(issue_key)

        if ctx.obj['json']:
            format_output(transitions, as_json=True)
        elif ctx.obj['quiet']:
            for t in transitions:
                print(t.get('name', ''))
        else:
            # Get current status
            issue = client.issue(issue_key, fields='status')
            current_status = issue['fields']['status']['name']

            print(f"Available transitions for {issue_key}")
            print(f"Current status: {current_status}\n")

            if not transitions:
                print("No transitions available from this status")
            else:
                rows = []
                for t in transitions:
                    rows.append({
                        'ID': t.get('id', ''),
                        'Name': t.get('name', ''),
                        'To Status': _get_to_status(t)
                    })
                print(format_table(rows, ['ID', 'Name', 'To Status']))

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get transitions for {issue_key}: {e}")
        sys.exit(1)


@cli.command('do')
@click.argument('issue_key')
@click.argument('target_state')
@click.option('--comment', '-c', is_flag=True, help='Add transition trail as comment')
@click.option('--resolution', '-r', help='Resolution name (for closing transitions)')
@click.option('--dry-run', is_flag=True, help='Show path without executing')
@click.pass_context
def do_transition(ctx, issue_key: str, target_state: str,
                  comment: bool, resolution: str | None, dry_run: bool):
    """Transition an issue to a new status (smart multi-step).

    ISSUE_KEY: The Jira issue key (e.g., PROJ-123)

    TARGET_STATE: Target status name (e.g., "In Progress", "Waiting for QA")

    Automatically finds and executes the shortest path to the target state.

    Examples:

      jira-transition do PROJ-123 "In Progress"

      jira-transition do PROJ-123 "Waiting for QA" --dry-run

      jira-transition do PROJ-123 "Done" --comment

      jira-transition do PROJ-123 "Geschlossen" -r Fixed
    """
    client = ctx.obj['client']
    debug = ctx.obj['debug']

    try:
        store = WorkflowStore()

        # Handle resolution for closing transitions
        # TODO: Add resolution support in v2
        if resolution:
            warning("Resolution support coming in v2, ignoring for now")

        executed = smart_transition(
            client=client,
            issue_key=issue_key,
            target_state=target_state,
            store=store,
            add_comment=comment,
            dry_run=dry_run,
            verbose=not ctx.obj['quiet']
        )

        if dry_run:
            if ctx.obj['json']:
                format_output({
                    'issue_key': issue_key,
                    'dry_run': True,
                    'path': [t.to_dict() for t in executed]
                }, as_json=True)
            return

        if ctx.obj['quiet']:
            print(issue_key)
        elif ctx.obj['json']:
            format_output({
                'issue_key': issue_key,
                'transitions': [t.to_dict() for t in executed],
                'final_state': executed[-1].to if executed else target_state
            }, as_json=True)
        else:
            if executed:
                success(f"Transitioned {issue_key} to '{executed[-1].to}'")
            else:
                success(f"{issue_key} already at '{target_state}'")

    except PathNotFoundError as e:
        error(f"No path to '{target_state}'")
        print(f"  Reachable states: {', '.join(sorted(e.reachable))}")
        sys.exit(1)

    except TransitionFailedError as e:
        error(f"Transition failed at '{e.current_state}'")
        print(f"  Failed: {e.transition.name} → {e.transition.to}")
        print(f"  Reason: {e.reason}")
        sys.exit(1)

    except Exception as e:
        if debug:
            raise
        error(f"Failed to transition {issue_key}: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
