#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Confluence page operations - get, create, update, delete pages."""

import sys
from pathlib import Path

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
from lib.client import get_confluence_client
from lib.output import format_output, error, success, warning


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output (page ID only)')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json, quiet, env_file, debug):
    """Manage Confluence pages."""
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
@click.option('--expand', '-e', multiple=True,
              help='Fields to expand (body.storage, body.view, version, ancestors, children)')
@click.option('--body-format', type=click.Choice(['storage', 'view', 'editor']),
              default='storage', help='Body format to retrieve')
@click.pass_context
def get(ctx, page_id, expand, body_format):
    """Get page by ID.

    Returns page details including title, space, and optionally body content.
    """
    client = ctx.obj['client']

    try:
        # Build expand string
        expand_list = list(expand) if expand else []
        if not any(e.startswith('body') for e in expand_list):
            expand_list.append(f'body.{body_format}')
        expand_str = ','.join(expand_list)

        page = client.get_page_by_id(page_id, expand=expand_str)

        if ctx.obj['quiet']:
            print(page.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(page, as_json=True)
            return

        # Human-readable output
        print(f"ID: {page.get('id')}")
        print(f"Title: {page.get('title')}")
        print(f"Space: {page.get('space', {}).get('key', 'N/A')}")
        print(f"Type: {page.get('type')}")
        print(f"Version: {page.get('version', {}).get('number', 'N/A')}")
        print(f"URL: {page.get('_links', {}).get('webui', 'N/A')}")

        if 'body' in page and body_format in page['body']:
            content = page['body'][body_format].get('value', '')
            print(f"\nBody ({body_format}):")
            print("-" * 40)
            # Truncate long content
            if len(content) > 2000:
                print(content[:2000])
                print(f"\n... (truncated, {len(content)} total chars)")
            else:
                print(content)

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get page: {e}")
        sys.exit(1)


@cli.command()
@click.argument('space_key')
@click.argument('title')
@click.option('--body', '-b', help='Page body content (storage format/HTML)')
@click.option('--body-file', type=click.Path(exists=True), help='Read body from file')
@click.option('--parent-id', '-p', help='Parent page ID')
@click.option('--type', 'page_type', default='page', type=click.Choice(['page', 'blogpost']),
              help='Content type (default: page)')
@click.option('--dry-run', is_flag=True, help='Preview without creating')
@click.pass_context
def create(ctx, space_key, title, body, body_file, parent_id, page_type, dry_run):
    """Create a new page.

    Body content should be in Confluence storage format (XHTML-based).
    """
    client = ctx.obj['client']

    # Get body content
    if body_file:
        with open(body_file) as f:
            body_content = f.read()
    elif body:
        body_content = body
    else:
        body_content = ""

    if dry_run:
        print("DRY RUN - Would create page:")
        print(f"  Space: {space_key}")
        print(f"  Title: {title}")
        print(f"  Type: {page_type}")
        if parent_id:
            print(f"  Parent ID: {parent_id}")
        print(f"  Body length: {len(body_content)} chars")
        return

    try:
        page = client.create_page(
            space=space_key,
            title=title,
            body=body_content,
            parent_id=parent_id,
            type=page_type
        )

        if ctx.obj['quiet']:
            print(page.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(page, as_json=True)
            return

        success(f"Page created: {page.get('id')}")
        print(f"Title: {page.get('title')}")
        print(f"URL: {page.get('_links', {}).get('webui', 'N/A')}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to create page: {e}")
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.option('--title', '-t', help='New title')
@click.option('--body', '-b', help='New body content (storage format/HTML)')
@click.option('--body-file', type=click.Path(exists=True), help='Read body from file')
@click.option('--minor-edit', is_flag=True, help='Mark as minor edit')
@click.option('--version-comment', help='Version comment')
@click.option('--dry-run', is_flag=True, help='Preview without updating')
@click.pass_context
def update(ctx, page_id, title, body, body_file, minor_edit, version_comment, dry_run):
    """Update an existing page.

    At least one of --title, --body, or --body-file must be provided.
    """
    client = ctx.obj['client']

    if not title and not body and not body_file:
        error("At least one of --title, --body, or --body-file must be provided")
        sys.exit(1)

    try:
        # Get current page to preserve unchanged fields
        current = client.get_page_by_id(page_id, expand='body.storage,version')
        current_title = current.get('title')
        current_body = current.get('body', {}).get('storage', {}).get('value', '')
        current_version = current.get('version', {}).get('number', 1)

        new_title = title if title else current_title
        if body_file:
            with open(body_file) as f:
                new_body = f.read()
        elif body:
            new_body = body
        else:
            new_body = current_body

        if dry_run:
            print("DRY RUN - Would update page:")
            print(f"  Page ID: {page_id}")
            print(f"  Title: {current_title} -> {new_title}")
            print(f"  Body changed: {new_body != current_body}")
            print(f"  Version: {current_version} -> {current_version + 1}")
            if minor_edit:
                print("  Minor edit: Yes")
            if version_comment:
                print(f"  Comment: {version_comment}")
            return

        page = client.update_page(
            page_id=page_id,
            title=new_title,
            body=new_body,
            minor_edit=minor_edit,
            version_comment=version_comment
        )

        if ctx.obj['quiet']:
            print(page.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(page, as_json=True)
            return

        success(f"Page updated: {page.get('id')}")
        print(f"Version: {page.get('version', {}).get('number', 'N/A')}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to update page: {e}")
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.option('--dry-run', is_flag=True, help='Preview without deleting')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.pass_context
def delete(ctx, page_id, dry_run, force):
    """Delete a page.

    This moves the page to trash (can be restored within retention period).
    """
    client = ctx.obj['client']

    try:
        # Get page info first
        page = client.get_page_by_id(page_id)
        title = page.get('title', 'Unknown')

        if dry_run:
            print("DRY RUN - Would delete page:")
            print(f"  Page ID: {page_id}")
            print(f"  Title: {title}")
            return

        if not force:
            warning(f"About to delete page: {title} (ID: {page_id})")
            if not click.confirm("Are you sure?"):
                print("Cancelled.")
                return

        client.remove_page(page_id)

        if ctx.obj['quiet']:
            print(page_id)
            return

        success(f"Page deleted: {page_id} ({title})")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to delete page: {e}")
        sys.exit(1)


@cli.command('get-by-title')
@click.argument('space_key')
@click.argument('title')
@click.option('--expand', '-e', multiple=True, help='Fields to expand')
@click.pass_context
def get_by_title(ctx, space_key, title, expand):
    """Get page by space key and title."""
    client = ctx.obj['client']

    try:
        expand_str = ','.join(expand) if expand else 'body.storage'
        page = client.get_page_by_title(space_key, title, expand=expand_str)

        if not page:
            error(f"Page not found: '{title}' in space '{space_key}'")
            sys.exit(1)

        if ctx.obj['quiet']:
            print(page.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(page, as_json=True)
            return

        # Human-readable output
        print(f"ID: {page.get('id')}")
        print(f"Title: {page.get('title')}")
        print(f"Space: {page.get('space', {}).get('key', 'N/A')}")
        print(f"Version: {page.get('version', {}).get('number', 'N/A')}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get page: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
