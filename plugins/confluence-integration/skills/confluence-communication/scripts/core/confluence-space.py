#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Confluence space operations - list and get space details."""

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
@click.option('--quiet', '-q', is_flag=True, help='Minimal output (space keys only)')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json, quiet, env_file, debug):
    """Manage Confluence spaces."""
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
@click.option('--type', 'space_type', type=click.Choice(['global', 'personal', 'all']),
              default='all', help='Filter by space type')
@click.option('--limit', '-l', default=50, help='Maximum results (default: 50)')
@click.option('--start', default=0, help='Start index for pagination')
@click.pass_context
def list(ctx, space_type, limit, start):
    """List all spaces."""
    client = ctx.obj['client']

    try:
        spaces = client.get_all_spaces(start=start, limit=limit, expand='description.plain')

        results = spaces.get('results', [])

        # Filter by type if specified
        if space_type != 'all':
            results = [s for s in results if s.get('type', '').lower() == space_type]

        if ctx.obj['quiet']:
            for space in results:
                print(space.get('key', ''))
            return

        if ctx.obj['json']:
            format_output(spaces, as_json=True)
            return

        if not results:
            print("No spaces found.")
            return

        # Human-readable table
        table_data = []
        for space in results:
            desc = space.get('description', {})
            if isinstance(desc, dict):
                desc_text = desc.get('plain', {}).get('value', '')[:50]
            else:
                desc_text = ''
            table_data.append({
                'key': space.get('key', ''),
                'name': space.get('name', '')[:40],
                'type': space.get('type', ''),
            })

        print(format_table(table_data, ['key', 'name', 'type']))
        print(f"\nTotal: {len(results)} spaces")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to list spaces: {e}")
        sys.exit(1)


@cli.command()
@click.argument('space_key')
@click.option('--expand', '-e', multiple=True,
              help='Fields to expand (description, homepage, etc.)')
@click.pass_context
def get(ctx, space_key, expand):
    """Get space details by key."""
    client = ctx.obj['client']

    try:
        expand_str = ','.join(expand) if expand else 'description.plain,homepage'
        space = client.get_space(space_key, expand=expand_str)

        if ctx.obj['quiet']:
            print(space.get('key', ''))
            return

        if ctx.obj['json']:
            format_output(space, as_json=True)
            return

        # Human-readable output
        print(f"Key: {space.get('key')}")
        print(f"Name: {space.get('name')}")
        print(f"Type: {space.get('type')}")

        desc = space.get('description', {})
        if isinstance(desc, dict) and 'plain' in desc:
            desc_text = desc['plain'].get('value', '')
            if desc_text:
                print(f"Description: {desc_text}")

        homepage = space.get('homepage', {})
        if homepage:
            print(f"Homepage ID: {homepage.get('id')}")
            print(f"Homepage Title: {homepage.get('title')}")

        links = space.get('_links', {})
        if 'webui' in links:
            print(f"URL: {links['webui']}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get space: {e}")
        sys.exit(1)


@cli.command()
@click.argument('space_key')
@click.option('--limit', '-l', default=50, help='Maximum results (default: 50)')
@click.option('--start', default=0, help='Start index for pagination')
@click.pass_context
def pages(ctx, space_key, limit, start):
    """List all pages in a space."""
    client = ctx.obj['client']

    try:
        pages = client.get_all_pages_from_space(space_key, start=start, limit=limit)

        if ctx.obj['quiet']:
            for page in pages:
                print(page.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(pages, as_json=True)
            return

        if not pages:
            print(f"No pages found in space '{space_key}'.")
            return

        # Human-readable table
        table_data = []
        for page in pages:
            table_data.append({
                'id': page.get('id', ''),
                'title': page.get('title', '')[:50],
                'type': page.get('type', ''),
            })

        print(format_table(table_data, ['id', 'title', 'type']))
        print(f"\nTotal: {len(pages)} pages")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to list pages: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
