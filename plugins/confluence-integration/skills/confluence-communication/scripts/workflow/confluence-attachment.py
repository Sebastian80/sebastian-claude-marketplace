#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
#     "requests>=2.28.0",
# ]
# ///
"""Confluence attachment operations - upload, list, download attachments."""

import sys
from pathlib import Path

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
import requests
from lib.client import get_confluence_client
from lib.config import load_env, get_auth_mode
from lib.output import format_output, format_table, error, success


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json, quiet, env_file, debug):
    """Manage page attachments."""
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json
    ctx.obj['quiet'] = quiet
    ctx.obj['debug'] = debug
    ctx.obj['env_file'] = env_file

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
@click.pass_context
def list(ctx, page_id, limit, start):
    """List attachments on a page."""
    client = ctx.obj['client']

    try:
        attachments = client.get_attachments_from_content(page_id, start=start, limit=limit)

        results = attachments.get('results', [])

        if ctx.obj['quiet']:
            for att in results:
                print(att.get('id', ''))
            return

        if ctx.obj['json']:
            format_output(attachments, as_json=True)
            return

        if not results:
            print(f"No attachments on page {page_id}.")
            return

        # Human-readable table
        table_data = []
        for att in results:
            extensions = att.get('extensions', {})
            table_data.append({
                'id': att.get('id', ''),
                'title': att.get('title', '')[:40],
                'size': _format_size(extensions.get('fileSize', 0)),
                'type': extensions.get('mediaType', 'unknown')[:20],
            })

        print(format_table(table_data, ['id', 'title', 'size', 'type']))
        print(f"\nTotal: {len(results)} attachments")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to list attachments: {e}")
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--name', '-n', help='Attachment name (defaults to filename)')
@click.option('--comment', '-c', help='Attachment comment')
@click.option('--dry-run', is_flag=True, help='Preview without uploading')
@click.pass_context
def upload(ctx, page_id, file_path, name, comment, dry_run):
    """Upload a file as attachment to a page."""
    client = ctx.obj['client']

    file_path = Path(file_path)
    attachment_name = name if name else file_path.name

    if dry_run:
        print("DRY RUN - Would upload attachment:")
        print(f"  Page ID: {page_id}")
        print(f"  File: {file_path}")
        print(f"  Name: {attachment_name}")
        print(f"  Size: {_format_size(file_path.stat().st_size)}")
        if comment:
            print(f"  Comment: {comment}")
        return

    try:
        result = client.attach_file(
            filename=str(file_path),
            name=attachment_name,
            page_id=page_id,
            comment=comment
        )

        if ctx.obj['quiet']:
            # Try to get the attachment ID from result
            if isinstance(result, dict):
                print(result.get('id', page_id))
            else:
                print(page_id)
            return

        if ctx.obj['json']:
            format_output(result, as_json=True)
            return

        success(f"Attachment uploaded to page {page_id}")
        print(f"File: {attachment_name}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to upload attachment: {e}")
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.argument('attachment_name')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.pass_context
def download(ctx, page_id, attachment_name, output):
    """Download an attachment from a page."""
    client = ctx.obj['client']

    try:
        # Get attachment info first
        attachments = client.get_attachments_from_content(page_id)
        results = attachments.get('results', [])

        target = None
        for att in results:
            if att.get('title') == attachment_name:
                target = att
                break

        if not target:
            error(f"Attachment '{attachment_name}' not found on page {page_id}")
            sys.exit(1)

        # Download the file
        download_link = target.get('_links', {}).get('download', '')
        if not download_link:
            error("Could not find download link for attachment")
            sys.exit(1)

        # Build full URL
        config = load_env(ctx.obj.get('env_file'))
        base_url = config['CONFLUENCE_URL'].rstrip('/')

        # The download link is usually relative
        if download_link.startswith('/'):
            full_url = base_url + download_link
        else:
            full_url = download_link

        # Setup auth for download
        auth_mode = get_auth_mode(config)
        if auth_mode == 'pat':
            headers = {'Authorization': f"Bearer {config['CONFLUENCE_PERSONAL_TOKEN']}"}
            auth = None
        else:
            headers = {}
            auth = (config['CONFLUENCE_USERNAME'], config['CONFLUENCE_API_TOKEN'])

        response = requests.get(full_url, headers=headers, auth=auth, stream=True)
        response.raise_for_status()

        # Determine output path
        output_path = Path(output) if output else Path(attachment_name)

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        if ctx.obj['quiet']:
            print(str(output_path))
            return

        success(f"Downloaded: {output_path}")
        print(f"Size: {_format_size(output_path.stat().st_size)}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to download attachment: {e}")
        sys.exit(1)


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


if __name__ == '__main__':
    cli()
