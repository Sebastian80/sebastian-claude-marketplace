#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Confluence user operations - get current user and search users."""

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
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json, quiet, env_file, debug):
    """User operations."""
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
@click.pass_context
def me(ctx):
    """Get current user information."""
    client = ctx.obj['client']

    try:
        # Confluence API doesn't have get_current_user - use direct REST call
        try:
            response = client._session.get(f"{client.url}/wiki/rest/api/user/current")
            user = response.json()
        except Exception:
            # Fallback for Server/DC
            response = client._session.get(f"{client.url}/rest/api/user/current")
            user = response.json()

        if ctx.obj['quiet']:
            print(user.get('accountId', user.get('username', user.get('name', ''))))
            return

        if ctx.obj['json']:
            format_output(user, as_json=True)
            return

        # Human-readable output
        print(f"Username: {user.get('username', user.get('name', 'N/A'))}")
        print(f"Display Name: {user.get('displayName', 'N/A')}")
        print(f"Email: {user.get('email', 'N/A')}")
        if 'accountId' in user:
            print(f"Account ID: {user.get('accountId')}")
        if 'userKey' in user:
            print(f"User Key: {user.get('userKey')}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to get current user: {e}")
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('--limit', '-l', default=25, help='Maximum results (default: 25)')
@click.pass_context
def search(ctx, query, limit):
    """Search for users by name or email."""
    client = ctx.obj['client']

    try:
        # Use CQL to search for users
        # Note: The exact method depends on the atlassian-python-api version
        # Try the user search method
        try:
            users = client.cql(f'user ~ "{query}"', limit=limit)
            results = users.get('results', [])
        except Exception:
            # Fallback: try to get user directly
            try:
                user = client.get_user_details_by_username(query)
                results = [user] if user else []
            except Exception:
                results = []

        if ctx.obj['quiet']:
            for user in results:
                print(user.get('accountId', user.get('username', '')))
            return

        if ctx.obj['json']:
            format_output(results, as_json=True)
            return

        if not results:
            print(f"No users found matching '{query}'.")
            return

        # Human-readable table
        table_data = []
        for user in results:
            table_data.append({
                'username': user.get('username', user.get('name', ''))[:20],
                'displayName': user.get('displayName', '')[:30],
                'email': user.get('email', 'N/A')[:30],
            })

        print(format_table(table_data, ['username', 'displayName', 'email']))

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to search users: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
