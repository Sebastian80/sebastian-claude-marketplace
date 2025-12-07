#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Confluence children operations - list child pages."""

import sys
from pathlib import Path

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
from lib.client import get_confluence_client
from lib.output import format_output, format_table, error


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output (page IDs only)')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json, quiet, env_file, debug):
    """Manage page hierarchy."""
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json
    ctx.obj['quiet'] = quiet
    ctx.obj['debug'] = debug

    try:
        ctx.obj['client'] = get_confluence_client(env_file)
    except Exception as e:
        if debug:
            raise
        error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.option('--limit', '-l', default=50, help='Maximum results (default: 50)')
@click.option('--start', default=0, help='Start index for pagination')
@click.option('--recursive', '-r', is_flag=True, help='Include all descendants')
@click.option('--expand', '-e', multiple=True, help='Fields to expand')
@click.pass_context
def list(ctx, page_id, limit, start, recursive, expand):
    """List child pages of a parent page."""
    client = ctx.obj['client']

    try:
        expand_str = ','.join(expand) if expand else None

        if recursive:
            # Get all descendants
            children = client.get_page_child_by_type(page_id, type='page', start=start, limit=limit,
                                                      expand=expand_str)
        else:
            # Get direct children only
            children = client.get_page_child_by_type(page_id, type='page', start=start, limit=limit,
                                                      expand=expand_str)

        # Note: can't use isinstance(children, list) because 'list' is shadowed by the command name
        results = children if type(children).__name__ == 'list' else children.get('results', [])

        if ctx.obj['quiet']:
            for child in results:
                print(child.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(children, as_json=True)
            return

        if not results:
            print(f"No child pages found for page {page_id}.")
            return

        # Human-readable table
        table_data = []
        for child in results:
            table_data.append({
                'id': child.get('id', ''),
                'title': child.get('title', '')[:50],
                'type': child.get('type', ''),
            })

        print(format_table(table_data, ['id', 'title', 'type']))
        print(f"\nTotal: {len(results)} child pages")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get children: {e}")
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.option('--expand', '-e', multiple=True, help='Fields to expand')
@click.pass_context
def ancestors(ctx, page_id, expand):
    """List ancestor pages (parent chain to root)."""
    client = ctx.obj['client']

    try:
        expand_str = 'ancestors' + (',' + ','.join(expand) if expand else '')
        page = client.get_page_by_id(page_id, expand=expand_str)

        ancestors = page.get('ancestors', [])

        if ctx.obj['quiet']:
            for ancestor in ancestors:
                print(ancestor.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(ancestors, as_json=True)
            return

        if not ancestors:
            print(f"Page {page_id} has no ancestors (it's a root page).")
            return

        # Human-readable output
        print(f"Ancestors of page {page_id}:")
        for i, ancestor in enumerate(ancestors):
            indent = "  " * i
            print(f"{indent}-> {ancestor.get('title', 'Unknown')} (ID: {ancestor.get('id')})")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get ancestors: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
