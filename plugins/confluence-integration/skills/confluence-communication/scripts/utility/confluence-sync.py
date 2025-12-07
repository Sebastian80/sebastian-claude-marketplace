#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
#     "pyyaml>=6.0",
# ]
# ///
"""Confluence sync - sync markdown files to Confluence using mark CLI or native API."""

import sys
import subprocess
import shutil
import re
from pathlib import Path

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
import yaml
from lib.client import get_confluence_client
from lib.config import load_env
from lib.output import format_output, error, success, warning


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json, quiet, env_file, debug):
    """Sync markdown files to Confluence."""
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json
    ctx.obj['quiet'] = quiet
    ctx.obj['debug'] = debug
    ctx.obj['env_file'] = env_file

    # Check for mark CLI availability
    ctx.obj['mark_available'] = shutil.which('mark') is not None


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--space', '-s', required=True, help='Confluence space key')
@click.option('--parent', '-p', help='Parent page title or ID')
@click.option('--title', '-t', help='Page title (defaults to filename or frontmatter)')
@click.option('--use-mark', is_flag=True, help='Force use of mark CLI')
@click.option('--dry-run', is_flag=True, help='Preview without syncing')
@click.pass_context
def push(ctx, file_path, space, parent, title, use_mark, dry_run):
    """Push a markdown file to Confluence.

    If the page exists, it will be updated. Otherwise, a new page is created.

    Supports frontmatter for metadata:
    ---
    title: Page Title
    space: SPACE
    parent: Parent Page Title
    labels: [doc, api]
    ---
    """
    file_path = Path(file_path)

    # Read file and extract frontmatter
    content = file_path.read_text(encoding='utf-8')
    frontmatter, markdown_body = _parse_frontmatter(content)

    # Determine metadata (CLI args override frontmatter)
    page_title = title or frontmatter.get('title') or file_path.stem
    page_space = space or frontmatter.get('space')
    page_parent = parent or frontmatter.get('parent')
    labels = frontmatter.get('labels', [])

    if not page_space:
        error("Space is required. Use --space or add 'space:' to frontmatter")
        sys.exit(1)

    if dry_run:
        print("DRY RUN - Would sync:")
        print(f"  File: {file_path}")
        print(f"  Title: {page_title}")
        print(f"  Space: {page_space}")
        if page_parent:
            print(f"  Parent: {page_parent}")
        if labels:
            print(f"  Labels: {', '.join(labels)}")
        print(f"  Content length: {len(markdown_body)} chars")
        return

    # Use mark CLI if available and requested
    if use_mark and ctx.obj['mark_available']:
        _sync_with_mark(file_path, page_space, page_title, page_parent, ctx.obj['quiet'])
    else:
        if use_mark and not ctx.obj['mark_available']:
            warning("mark CLI not found, using native API")
        _sync_with_api(ctx, markdown_body, page_space, page_title, page_parent, labels)


@cli.command('push-dir')
@click.argument('directory', type=click.Path(exists=True))
@click.option('--space', '-s', required=True, help='Confluence space key')
@click.option('--parent', '-p', help='Parent page title or ID')
@click.option('--pattern', default='*.md', help='File pattern (default: *.md)')
@click.option('--recursive', '-r', is_flag=True, help='Include subdirectories')
@click.option('--use-mark', is_flag=True, help='Force use of mark CLI')
@click.option('--dry-run', is_flag=True, help='Preview without syncing')
@click.pass_context
def push_dir(ctx, directory, space, parent, pattern, recursive, use_mark, dry_run):
    """Push all markdown files in a directory to Confluence."""
    directory = Path(directory)

    if recursive:
        files = list(directory.rglob(pattern))
    else:
        files = list(directory.glob(pattern))

    if not files:
        warning(f"No files matching '{pattern}' found in {directory}")
        return

    if dry_run:
        print(f"DRY RUN - Would sync {len(files)} files:")
        for f in files:
            print(f"  {f}")
        return

    results = []
    for file_path in files:
        try:
            ctx.invoke(push, file_path=str(file_path), space=space, parent=parent,
                      title=None, use_mark=use_mark, dry_run=False)
            results.append({'file': str(file_path), 'status': 'success'})
        except Exception as e:
            results.append({'file': str(file_path), 'status': 'error', 'error': str(e)})

    if ctx.obj['json']:
        format_output(results, as_json=True)
        return

    succeeded = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - succeeded
    print(f"\nSynced {succeeded}/{len(results)} files")
    if failed > 0:
        warning(f"{failed} files failed")


@cli.command()
@click.pass_context
def check(ctx):
    """Check if mark CLI is installed and configured."""
    mark_path = shutil.which('mark')

    if mark_path:
        # Get version
        try:
            result = subprocess.run(['mark', '--version'], capture_output=True, text=True)
            version = result.stdout.strip() or 'unknown'
        except Exception:
            version = 'unknown'

        if ctx.obj['json']:
            format_output({
                'installed': True,
                'path': mark_path,
                'version': version,
            }, as_json=True)
            return

        success(f"mark CLI installed: {mark_path}")
        print(f"Version: {version}")

        # Check for config
        config_path = Path.home() / '.config' / 'mark'
        if config_path.exists():
            success(f"Config found: {config_path}")
        else:
            warning("No mark config found at ~/.config/mark")
            print("\nCreate config with:")
            print("  mkdir -p ~/.config && cat > ~/.config/mark << EOF")
            print("  username = your-email@example.com")
            print("  password = your-api-token")
            print("  base_url = https://company.atlassian.net/wiki")
            print("  EOF")
    else:
        if ctx.obj['json']:
            format_output({
                'installed': False,
                'fallback': 'native API',
            }, as_json=True)
            return

        warning("mark CLI not installed")
        print("\nTo install:")
        print("  # macOS")
        print("  brew install kovetskiy/mark/mark")
        print("")
        print("  # Go")
        print("  go install github.com/kovetskiy/mark@latest")
        print("")
        print("Fallback: Native API will be used for syncing")


@cli.command('init-frontmatter')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--space', '-s', help='Confluence space key')
@click.option('--parent', '-p', help='Parent page title')
@click.option('--title', '-t', help='Page title')
@click.pass_context
def init_frontmatter(ctx, file_path, space, parent, title):
    """Add Confluence frontmatter to a markdown file."""
    file_path = Path(file_path)
    content = file_path.read_text(encoding='utf-8')

    # Check if frontmatter exists
    if content.startswith('---'):
        warning("File already has frontmatter")
        return

    # Create frontmatter
    frontmatter = {
        'title': title or file_path.stem,
    }
    if space:
        frontmatter['space'] = space
    if parent:
        frontmatter['parent'] = parent

    yaml_str = yaml.dump(frontmatter, default_flow_style=False)
    new_content = f"---\n{yaml_str}---\n\n{content}"

    file_path.write_text(new_content, encoding='utf-8')

    if ctx.obj['quiet']:
        print(str(file_path))
        return

    success(f"Added frontmatter to {file_path}")


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}, content

    # Find end of frontmatter
    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return {}, content

    frontmatter_str = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3 + 1:]

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, body


def _sync_with_mark(file_path: Path, space: str, title: str, parent: str | None, quiet: bool):
    """Sync using mark CLI."""
    cmd = ['mark', '-f', str(file_path), '--space', space]

    if parent:
        cmd.extend(['--parents', parent])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"mark failed: {result.stderr}")

    if not quiet:
        success(f"Synced with mark: {file_path}")
        if result.stdout:
            print(result.stdout)


def _sync_with_api(ctx, markdown_body: str, space: str, title: str,
                   parent: str | None, labels: list):
    """Sync using native Confluence API."""
    import markdown
    from lib.client import get_confluence_client

    client = get_confluence_client(ctx.obj.get('env_file'))

    # Convert markdown to HTML
    html_body = markdown.markdown(
        markdown_body,
        extensions=['fenced_code', 'tables', 'nl2br']
    )

    # Wrap in storage format
    storage_body = html_body

    # Check if page exists
    existing = client.get_page_by_title(space, title)

    if existing:
        # Update existing page
        page = client.update_page(
            page_id=existing['id'],
            title=title,
            body=storage_body,
        )
        action = "Updated"
    else:
        # Create new page
        parent_id = None
        if parent:
            # Try to find parent page
            parent_page = client.get_page_by_title(space, parent)
            if parent_page:
                parent_id = parent_page['id']

        page = client.create_page(
            space=space,
            title=title,
            body=storage_body,
            parent_id=parent_id,
        )
        action = "Created"

    # Add labels if specified
    if labels and page:
        for label in labels:
            try:
                client.set_page_label(page['id'], label)
            except Exception:
                pass  # Ignore label errors

    if ctx.obj['quiet']:
        print(page.get('id', ''))
        return

    if ctx.obj['json']:
        format_output(page, as_json=True)
        return

    success(f"{action} page: {title}")
    print(f"ID: {page.get('id')}")
    print(f"URL: {page.get('_links', {}).get('webui', 'N/A')}")


if __name__ == '__main__':
    cli()
