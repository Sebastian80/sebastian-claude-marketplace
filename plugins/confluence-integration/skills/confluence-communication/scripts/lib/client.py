"""Confluence client initialization for CLI scripts."""

from typing import Optional
from atlassian import Confluence

from .config import load_env, validate_config, get_auth_mode

# === INLINE_START: client ===

def get_confluence_client(env_file: Optional[str] = None) -> Confluence:
    """Initialize and return a Confluence client.

    Supports two authentication modes:
    - Cloud: CONFLUENCE_USERNAME + CONFLUENCE_API_TOKEN
    - Server/DC: CONFLUENCE_PERSONAL_TOKEN (Personal Access Token)

    Args:
        env_file: Optional path to environment file

    Returns:
        Configured Confluence client instance

    Raises:
        FileNotFoundError: If env file doesn't exist
        ValueError: If configuration is invalid
        ConnectionError: If cannot connect to Confluence
    """
    config = load_env(env_file)

    errors = validate_config(config)
    if errors:
        raise ValueError("Configuration errors:\n  " + "\n  ".join(errors))

    url = config['CONFLUENCE_URL']
    auth_mode = get_auth_mode(config)

    # Determine if Cloud or Server/DC
    is_cloud = config.get('CONFLUENCE_CLOUD', '').lower() == 'true'

    # Auto-detect if not specified
    if 'CONFLUENCE_CLOUD' not in config:
        is_cloud = '.atlassian.net' in url.lower()

    try:
        if auth_mode == 'pat':
            # Server/DC with Personal Access Token
            client = Confluence(
                url=url,
                token=config['CONFLUENCE_PERSONAL_TOKEN'],
                cloud=is_cloud
            )
        else:
            # Cloud with username + API token
            client = Confluence(
                url=url,
                username=config['CONFLUENCE_USERNAME'],
                password=config['CONFLUENCE_API_TOKEN'],
                cloud=is_cloud
            )
        return client
    except Exception as e:
        if auth_mode == 'pat':
            raise ConnectionError(
                f"Failed to connect to Confluence at {url}\n\n"
                f"  Error: {e}\n\n"
                f"  Please verify:\n"
                f"    - CONFLUENCE_URL is correct\n"
                f"    - CONFLUENCE_PERSONAL_TOKEN is a valid Personal Access Token\n"
            )
        else:
            raise ConnectionError(
                f"Failed to connect to Confluence at {url}\n\n"
                f"  Error: {e}\n\n"
                f"  Please verify:\n"
                f"    - CONFLUENCE_URL is correct\n"
                f"    - CONFLUENCE_USERNAME is your email (Cloud) or username (Server/DC)\n"
                f"    - CONFLUENCE_API_TOKEN is valid\n"
            )

# === INLINE_END: client ===
