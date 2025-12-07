#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
#     "requests>=2.28.0",
# ]
# ///
"""Confluence environment validation - verify runtime, configuration, and connectivity."""

import shutil
import subprocess
import sys
from pathlib import Path

# Shared library import (PYTHONPATH approach)
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import json as json_module

import click
import requests
from lib.config import load_env, validate_config, get_auth_mode, DEFAULT_ENV_FILE
from lib.client import get_confluence_client
from lib.output import success, error, warning

# Exit Codes
EXIT_SUCCESS = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_CONNECTION_ERROR = 3


def check_runtime(verbose: bool = False) -> tuple[bool, dict]:
    """Check runtime dependencies."""
    checks_passed = True
    info = {}

    # Check uv/uvx
    uv_path = shutil.which('uv')
    if uv_path:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        uv_version = result.stdout.strip() if result.returncode == 0 else 'unknown'
        info['uv_path'] = uv_path
        info['uv_version'] = uv_version
        if verbose:
            success(f"uv found: {uv_path} ({uv_version})")
    else:
        error(
            "Runtime check failed: 'uv' command not found",
            "To install uv, run:\n"
            "    curl -LsSf https://astral.sh/uv/install.sh | sh\n\n"
            "  Or visit: https://docs.astral.sh/uv/getting-started/installation/"
        )
        checks_passed = False

    # Check Python version
    py_version = sys.version_info
    info['python_version'] = f"{py_version.major}.{py_version.minor}.{py_version.micro}"
    if py_version >= (3, 10):
        if verbose:
            success(f"Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        error(
            f"Python version {py_version.major}.{py_version.minor} < 3.10 required",
            "Please upgrade Python to 3.10 or later"
        )
        checks_passed = False

    return checks_passed, info


def check_environment(env_file: str | None, verbose: bool = False) -> dict | None:
    """Check environment configuration."""
    try:
        config = load_env(env_file)
        errors = validate_config(config)

        if errors:
            for err in errors:
                error(f"Configuration error: {err}")
            return None

        if verbose:
            path = Path(env_file) if env_file else DEFAULT_ENV_FILE
            success(f"Environment file: {path}")
            success(f"CONFLUENCE_URL: {config['CONFLUENCE_URL']}")

            # Show auth mode-specific credentials
            auth_mode = get_auth_mode(config)
            if auth_mode == 'pat':
                success("Auth mode: Personal Access Token (Server/DC)")
                success("CONFLUENCE_PERSONAL_TOKEN: ******* (hidden)")
            else:
                success("Auth mode: Username + API Token (Cloud)")
                success(f"CONFLUENCE_USERNAME: {config.get('CONFLUENCE_USERNAME', 'N/A')}")
                success("CONFLUENCE_API_TOKEN: ******* (hidden)")

            if 'CONFLUENCE_CLOUD' in config:
                success(f"CONFLUENCE_CLOUD: {config['CONFLUENCE_CLOUD']}")

        return config

    except FileNotFoundError as e:
        error(str(e))
        return None


def check_connectivity(config: dict, space: str | None, verbose: bool = False) -> tuple[bool, dict]:
    """Check connectivity and authentication."""
    url = config['CONFLUENCE_URL']
    info = {'url': url}

    # Test server reachability
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        info['server_reachable'] = True
        if verbose:
            success(f"Server reachable: {url} (status: {response.status_code})")
    except requests.exceptions.Timeout:
        error(
            f"Connection timeout: {url}",
            "The server did not respond within 10 seconds.\n"
            "  Check your network connection and CONFLUENCE_URL."
        )
        return False, info
    except requests.exceptions.ConnectionError as e:
        error(
            f"Connection failed: {url}",
            f"Could not connect to the server.\n  Error: {e}"
        )
        return False, info

    # Test authentication
    try:
        client = get_confluence_client()
        # Confluence API: test auth by getting spaces (no get_current_user method)
        spaces = client.get_all_spaces(limit=1)
        info['authenticated'] = True

        # Try to get user info from a simple API call
        try:
            # For Cloud, try the /wiki/rest/api/user/current endpoint
            user = client._session.get(f"{client.url}/wiki/rest/api/user/current").json()
            display_name = user.get('displayName', user.get('username', 'Unknown'))
            email = user.get('email', 'N/A')
            info['user'] = display_name
            info['email'] = email
        except Exception:
            display_name = config.get('CONFLUENCE_USERNAME', 'Unknown')
            email = display_name
            info['user'] = display_name

        if verbose:
            success(f"Authenticated as: {display_name}")

    except Exception as e:
        error(
            "Authentication failed",
            f"Could not authenticate with the provided credentials.\n  Error: {e}"
        )
        return False, info

    # Test space access (optional)
    if space:
        try:
            space_info = client.get_space(space)
            info['space_access'] = space
            if verbose:
                success(f"Space access: {space} ({space_info.get('name', 'Unknown')})")
            else:
                success(f"Space access verified: {space}")
        except Exception as e:
            warning(f"Could not access space {space}: {e}")

    return True, info


@click.command()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
@click.option('--space', '-s', help='Verify access to specific space')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
def main(output_json: bool, quiet: bool, verbose: bool, space: str | None,
         env_file: str | None, debug: bool):
    """Validate Confluence environment configuration.

    Checks runtime dependencies, environment configuration, and connectivity
    to ensure the Confluence CLI scripts will work correctly.

    Exit codes:
      0 - All checks passed
      1 - Runtime dependency missing
      2 - Environment configuration error
      3 - Connectivity/authentication failure
    """
    result = {'status': 'ok'}

    # Suppress verbose output if JSON or quiet mode
    show_verbose = verbose and not output_json and not quiet

    if show_verbose:
        click.echo("=" * 60)
        click.echo("Confluence Environment Validation")
        click.echo("=" * 60)
        click.echo()

    # Check 1: Runtime
    if show_verbose:
        click.echo("Runtime Checks:")
    runtime_ok, runtime_info = check_runtime(show_verbose)
    result['runtime'] = runtime_info
    if not runtime_ok:
        result['status'] = 'error'
        result['error'] = 'runtime_check_failed'
        if output_json:
            print(json_module.dumps(result, indent=2))
        elif quiet:
            print('error')
        sys.exit(EXIT_RUNTIME_ERROR)
    if show_verbose:
        click.echo()

    # Check 2: Environment
    if show_verbose:
        click.echo("Environment Checks:")
    config = check_environment(env_file, show_verbose)
    if config is None:
        result['status'] = 'error'
        result['error'] = 'config_error'
        if output_json:
            print(json_module.dumps(result, indent=2))
        elif quiet:
            print('error')
        sys.exit(EXIT_CONFIG_ERROR)

    result['url'] = config['CONFLUENCE_URL']
    result['server_type'] = 'cloud' if 'atlassian.net' in config['CONFLUENCE_URL'] else 'server'
    auth_mode = get_auth_mode(config)
    result['auth_mode'] = auth_mode
    if auth_mode == 'cloud':
        result['username'] = config.get('CONFLUENCE_USERNAME', 'N/A')
    if show_verbose:
        click.echo()

    # Check 3: Connectivity
    if show_verbose:
        click.echo("Connectivity Checks:")
    conn_ok, conn_info = check_connectivity(config, space, show_verbose)
    result['user'] = conn_info.get('user', 'Unknown')
    if 'space_access' in conn_info:
        result['space_access'] = conn_info['space_access']
    if not conn_ok:
        result['status'] = 'error'
        result['error'] = 'connectivity_error'
        if output_json:
            print(json_module.dumps(result, indent=2))
        elif quiet:
            print('error')
        sys.exit(EXIT_CONNECTION_ERROR)
    if show_verbose:
        click.echo()

    # All passed
    if output_json:
        print(json_module.dumps(result, indent=2))
    elif quiet:
        print('ok')
    else:
        if show_verbose:
            click.echo("=" * 60)
        success("All validation checks passed!")
    sys.exit(EXIT_SUCCESS)


if __name__ == '__main__':
    main()
