#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Jira issue link operations - create links and list link types."""

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
    """Jira issue link operations.

    Create links between issues and list available link types.
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


@cli.command()
@click.argument('from_key')
@click.argument('to_key')
@click.option('--type', '-t', 'link_type', required=True,
              help='Link type name (e.g., "Blocks", "Relates")')
@click.option('--dry-run', is_flag=True, help='Show what would be created')
@click.pass_context
def create(ctx, from_key: str, to_key: str, link_type: str, dry_run: bool):
    """Create a link between two issues.

    FROM_KEY: Source issue key

    TO_KEY: Target issue key

    Examples:

      jira-link create PROJ-123 PROJ-456 --type "Blocks"

      jira-link create PROJ-123 PROJ-456 --type "Relates" --dry-run
    """
    client = ctx.obj['client']

    if dry_run:
        warning("DRY RUN - No link will be created")
        print(f"\nWould create link:")
        print(f"  {from_key} --[{link_type}]--> {to_key}")
        return

    try:
        client.create_issue_link(
            type=link_type,
            inwardIssue=to_key,
            outwardIssue=from_key
        )

        if ctx.obj['json']:
            format_output({
                'from': from_key,
                'to': to_key,
                'type': link_type,
                'created': True
            }, as_json=True)
        elif ctx.obj['quiet']:
            print('ok')
        else:
            success(f"Created link: {from_key} --[{link_type}]--> {to_key}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to create link: {e}")
        sys.exit(1)


@cli.command('weblink')
@click.argument('issue_key')
@click.argument('url')
@click.option('--title', '-t', help='Link title (defaults to URL)')
@click.option('--icon', help='Icon URL for the link')
@click.option('--dry-run', is_flag=True, help='Show what would be created')
@click.pass_context
def weblink(ctx, issue_key: str, url: str, title: str | None, icon: str | None, dry_run: bool):
    """Add a web link (remote link) to an issue.

    ISSUE_KEY: The issue to add the link to

    URL: The URL to link to

    Examples:

      jira-link weblink PROJ-123 https://github.com/org/repo/issues/42

      jira-link weblink PROJ-123 https://github.com/org/repo/issues/42 --title "GitHub Issue #42"

      jira-link weblink PROJ-123 https://example.com --title "Documentation" --icon "https://example.com/favicon.ico"
    """
    client = ctx.obj['client']
    link_title = title or url

    if dry_run:
        warning("DRY RUN - No link will be created")
        print(f"\nWould create web link:")
        print(f"  Issue: {issue_key}")
        print(f"  URL: {url}")
        print(f"  Title: {link_title}")
        if icon:
            print(f"  Icon: {icon}")
        return

    try:
        # Build the remote link payload
        link_object = {
            "url": url,
            "title": link_title
        }
        if icon:
            link_object["icon"] = {"url16x16": icon}

        # Use the underlying session to call the remote link API
        endpoint = f"rest/api/2/issue/{issue_key}/remotelink"
        response = client._session.post(
            f"{client.url}/{endpoint}",
            json={"object": link_object}
        )
        response.raise_for_status()
        result = response.json()

        if ctx.obj['json']:
            format_output({
                'issue': issue_key,
                'url': url,
                'title': link_title,
                'id': result.get('id'),
                'created': True
            }, as_json=True)
        elif ctx.obj['quiet']:
            print(result.get('id', 'ok'))
        else:
            success(f"Added web link to {issue_key}: {link_title}")
            print(f"  URL: {url}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to add web link: {e}")
        sys.exit(1)


@cli.command('weblinks')
@click.argument('issue_key')
@click.pass_context
def weblinks(ctx, issue_key: str):
    """List all web links (remote links) on an issue.

    ISSUE_KEY: The issue to list links for

    Example:

      jira-link weblinks PROJ-123
    """
    client = ctx.obj['client']

    try:
        endpoint = f"rest/api/2/issue/{issue_key}/remotelink"
        response = client._session.get(f"{client.url}/{endpoint}")
        response.raise_for_status()
        links = response.json()

        if ctx.obj['json']:
            format_output(links, as_json=True)
        elif ctx.obj['quiet']:
            for link in links:
                print(link.get('id', ''))
        else:
            if not links:
                print(f"No web links on {issue_key}")
                return

            print(f"Web links on {issue_key}:\n")
            rows = []
            for link in links:
                obj = link.get('object', {})
                rows.append({
                    'ID': str(link.get('id', '')),
                    'Title': obj.get('title', ''),
                    'URL': obj.get('url', '')
                })
            print(format_table(rows, ['ID', 'Title', 'URL']))

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get web links: {e}")
        sys.exit(1)


@cli.command('weblink-remove')
@click.argument('issue_key')
@click.argument('link_id')
@click.option('--dry-run', is_flag=True, help='Show what would be removed')
@click.pass_context
def weblink_remove(ctx, issue_key: str, link_id: str, dry_run: bool):
    """Remove a web link from an issue.

    ISSUE_KEY: The issue containing the link

    LINK_ID: The ID of the link to remove (use 'weblinks' command to find IDs)

    Example:

      jira-link weblink-remove PROJ-123 12345
    """
    client = ctx.obj['client']

    if dry_run:
        warning("DRY RUN - No link will be removed")
        print(f"\nWould remove web link {link_id} from {issue_key}")
        return

    try:
        endpoint = f"rest/api/2/issue/{issue_key}/remotelink/{link_id}"
        response = client._session.delete(f"{client.url}/{endpoint}")
        response.raise_for_status()

        if ctx.obj['json']:
            format_output({
                'issue': issue_key,
                'id': link_id,
                'removed': True
            }, as_json=True)
        elif ctx.obj['quiet']:
            print('ok')
        else:
            success(f"Removed web link {link_id} from {issue_key}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to remove web link: {e}")
        sys.exit(1)


@cli.command('weblink-update')
@click.argument('issue_key')
@click.argument('link_id')
@click.option('--url', help='New URL')
@click.option('--title', '-t', help='New title')
@click.option('--icon', help='New icon URL')
@click.option('--dry-run', is_flag=True, help='Show what would be updated')
@click.pass_context
def weblink_update(ctx, issue_key: str, link_id: str, url: str | None, title: str | None, icon: str | None, dry_run: bool):
    """Update a web link on an issue.

    ISSUE_KEY: The issue containing the link

    LINK_ID: The ID of the link to update (use 'weblinks' command to find IDs)

    Examples:

      jira-link weblink-update PROJ-123 12345 --title "New Title"

      jira-link weblink-update PROJ-123 12345 --url "https://new-url.com" --title "Updated"
    """
    client = ctx.obj['client']

    if not any([url, title, icon]):
        error("At least one of --url, --title, or --icon must be specified")
        sys.exit(1)

    try:
        # First get the existing link
        endpoint = f"rest/api/2/issue/{issue_key}/remotelink/{link_id}"
        response = client._session.get(f"{client.url}/{endpoint}")
        response.raise_for_status()
        existing = response.json()

        # Build updated object
        link_object = existing.get('object', {})
        if url:
            link_object['url'] = url
        if title:
            link_object['title'] = title
        if icon:
            link_object['icon'] = {'url16x16': icon}

        if dry_run:
            warning("DRY RUN - No link will be updated")
            print(f"\nWould update web link {link_id} on {issue_key}:")
            print(f"  URL: {link_object.get('url', '')}")
            print(f"  Title: {link_object.get('title', '')}")
            return

        # Update the link
        response = client._session.put(
            f"{client.url}/{endpoint}",
            json={"object": link_object}
        )
        response.raise_for_status()

        if ctx.obj['json']:
            format_output({
                'issue': issue_key,
                'id': link_id,
                'url': link_object.get('url'),
                'title': link_object.get('title'),
                'updated': True
            }, as_json=True)
        elif ctx.obj['quiet']:
            print('ok')
        else:
            success(f"Updated web link {link_id} on {issue_key}")
            print(f"  Title: {link_object.get('title', '')}")
            print(f"  URL: {link_object.get('url', '')}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to update web link: {e}")
        sys.exit(1)


@cli.command('list-types')
@click.pass_context
def list_types(ctx):
    """List available link types.

    Shows all issue link types configured in your Jira instance.

    Example:

      jira-link list-types
    """
    client = ctx.obj['client']

    try:
        link_types = client.get_issue_link_types()

        if ctx.obj['json']:
            format_output(link_types, as_json=True)
        elif ctx.obj['quiet']:
            for lt in link_types:
                print(lt.get('name', ''))
        else:
            print("Available link types:\n")
            rows = []
            for lt in link_types:
                rows.append({
                    'Name': lt.get('name', ''),
                    'Inward': lt.get('inward', ''),
                    'Outward': lt.get('outward', '')
                })
            print(format_table(rows, ['Name', 'Inward', 'Outward']))

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get link types: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
