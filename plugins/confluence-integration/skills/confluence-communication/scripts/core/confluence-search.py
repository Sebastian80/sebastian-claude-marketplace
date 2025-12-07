#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Confluence search - search pages using CQL (Confluence Query Language)."""

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
    """Search Confluence pages using CQL."""
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
@click.argument('cql')
@click.option('--limit', '-l', default=25, help='Maximum results (default: 25)')
@click.option('--start', default=0, help='Start index for pagination')
@click.option('--expand', '-e', multiple=True, help='Fields to expand (e.g., body.storage, version)')
@click.pass_context
def query(ctx, cql, limit, start, expand):
    """Search pages using CQL query.

    CQL (Confluence Query Language) examples:

    \b
      # Find pages in a space
      space = "DEV"

    \b
      # Find pages by title
      title ~ "Architecture"

    \b
      # Find recently modified pages
      lastModified > now("-7d")

    \b
      # Combine conditions
      space = "DEV" AND type = "page" AND text ~ "API"
    """
    client = ctx.obj['client']

    try:
        expand_str = ','.join(expand) if expand else None
        results = client.cql(cql, limit=limit, start=start, expand=expand_str)

        pages = results.get('results', [])

        if ctx.obj['quiet']:
            for page in pages:
                print(page.get('content', {}).get('id', page.get('id', '')))
            return

        if ctx.obj['json']:
            format_output(results, as_json=True)
            return

        # Human-readable table
        if not pages:
            print("No pages found matching the query.")
            return

        # Extract relevant fields for display
        table_data = []
        for item in pages:
            content = item.get('content', item)
            table_data.append({
                'id': content.get('id', ''),
                'title': content.get('title', ''),
                'space': content.get('space', {}).get('key', '') if isinstance(content.get('space'), dict) else '',
                'type': content.get('type', ''),
            })

        print(format_table(table_data, ['id', 'title', 'space', 'type']))
        print(f"\nTotal: {results.get('totalSize', len(pages))} results")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Search failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument('text')
@click.option('--space', '-s', help='Limit search to specific space')
@click.option('--limit', '-l', default=25, help='Maximum results (default: 25)')
@click.pass_context
def text(ctx, text, space, limit):
    """Simple text search across pages.

    This is a convenience wrapper that builds a CQL query for you.
    """
    # Build CQL query
    cql_parts = [f'text ~ "{text}"']
    if space:
        cql_parts.append(f'space = "{space}"')
    cql = ' AND '.join(cql_parts)

    # Reuse query command
    ctx.invoke(query, cql=cql, limit=limit, start=0, expand=())


if __name__ == '__main__':
    cli()
