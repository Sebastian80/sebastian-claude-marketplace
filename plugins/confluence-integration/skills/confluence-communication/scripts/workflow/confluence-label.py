#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Confluence label operations - add, remove, list labels on pages."""

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
    """Manage page labels."""
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
@click.pass_context
def list(ctx, page_id):
    """List labels on a page."""
    client = ctx.obj['client']

    try:
        labels = client.get_page_labels(page_id)
        results = labels.get('results', [])

        if ctx.obj['quiet']:
            for label in results:
                print(label.get('name', ''))
            return

        if ctx.obj['json']:
            format_output(labels, as_json=True)
            return

        if not results:
            print(f"No labels on page {page_id}.")
            return

        # Human-readable output
        label_names = [l.get('name', '') for l in results]
        print(f"Labels ({len(label_names)}): {', '.join(label_names)}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get labels: {e}")
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.argument('labels', nargs=-1, required=True)
@click.option('--dry-run', is_flag=True, help='Preview without adding')
@click.pass_context
def add(ctx, page_id, labels, dry_run):
    """Add labels to a page.

    Multiple labels can be specified:
      confluence-label.py add 12345 label1 label2 label3
    """
    client = ctx.obj['client']

    if dry_run:
        print("DRY RUN - Would add labels:")
        print(f"  Page ID: {page_id}")
        print(f"  Labels: {', '.join(labels)}")
        return

    try:
        for label in labels:
            client.set_page_label(page_id, label)

        if ctx.obj['quiet']:
            print(page_id)
            return

        success(f"Added {len(labels)} label(s) to page {page_id}")
        print(f"Labels: {', '.join(labels)}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to add labels: {e}")
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.argument('label')
@click.option('--dry-run', is_flag=True, help='Preview without removing')
@click.pass_context
def remove(ctx, page_id, label, dry_run):
    """Remove a label from a page."""
    client = ctx.obj['client']

    if dry_run:
        print("DRY RUN - Would remove label:")
        print(f"  Page ID: {page_id}")
        print(f"  Label: {label}")
        return

    try:
        client.remove_page_label(page_id, label)

        if ctx.obj['quiet']:
            print(page_id)
            return

        success(f"Removed label '{label}' from page {page_id}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to remove label: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
