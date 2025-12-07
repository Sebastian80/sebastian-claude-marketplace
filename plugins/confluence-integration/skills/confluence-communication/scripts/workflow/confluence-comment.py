#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Confluence comment operations - add and list comments on pages."""

import sys
from pathlib import Path

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
from lib.client import get_confluence_client
from lib.output import format_output, format_table, error, success


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json, quiet, env_file, debug):
    """Manage page comments."""
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
@click.option('--limit', '-l', default=25, help='Maximum results (default: 25)')
@click.option('--expand', '-e', multiple=True, help='Fields to expand')
@click.pass_context
def list(ctx, page_id, limit, expand):
    """List comments on a page."""
    client = ctx.obj['client']

    try:
        expand_str = ','.join(expand) if expand else 'body.storage'
        comments = client.get_page_comments(page_id, expand=expand_str, depth='all')

        results = comments.get('results', [])

        if ctx.obj['quiet']:
            for comment in results:
                print(comment.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(comments, as_json=True)
            return

        if not results:
            print(f"No comments on page {page_id}.")
            return

        # Human-readable output
        table_data = []
        for comment in results[:limit]:
            body = comment.get('body', {}).get('storage', {}).get('value', '')
            # Strip HTML and truncate
            import re
            body_text = re.sub(r'<[^>]+>', '', body)[:50]

            table_data.append({
                'id': comment.get('id', ''),
                'author': comment.get('version', {}).get('by', {}).get('displayName', 'Unknown')[:20],
                'content': body_text,
            })

        print(format_table(table_data, ['id', 'author', 'content']))
        print(f"\nTotal: {len(results)} comments")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get comments: {e}")
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.argument('body')
@click.option('--parent-id', '-p', help='Parent comment ID (for replies)')
@click.option('--dry-run', is_flag=True, help='Preview without adding')
@click.pass_context
def add(ctx, page_id, body, parent_id, dry_run):
    """Add a comment to a page.

    Body should be in storage format (HTML). Simple text is also accepted.
    """
    client = ctx.obj['client']

    # Wrap plain text in paragraph if needed
    if not body.strip().startswith('<'):
        body = f"<p>{body}</p>"

    if dry_run:
        print("DRY RUN - Would add comment:")
        print(f"  Page ID: {page_id}")
        if parent_id:
            print(f"  Parent comment: {parent_id}")
        print(f"  Body: {body[:100]}...")
        return

    try:
        comment = client.add_comment(page_id, body)

        if ctx.obj['quiet']:
            print(comment.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(comment, as_json=True)
            return

        success(f"Comment added: {comment.get('id')}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to add comment: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
