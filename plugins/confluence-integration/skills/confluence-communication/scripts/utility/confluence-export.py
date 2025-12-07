#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
#     "markdownify>=0.11.0",
# ]
# ///
"""Confluence export - export pages to markdown files."""

import sys
import re
from pathlib import Path
from datetime import datetime

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
from markdownify import markdownify as md
from lib.client import get_confluence_client
from lib.output import format_output, error, success


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json, quiet, env_file, debug):
    """Export Confluence pages to markdown."""
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
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--include-frontmatter', '-f', is_flag=True, help='Include YAML frontmatter')
@click.option('--include-children', '-c', is_flag=True, help='Export child pages too')
@click.option('--output-dir', '-d', type=click.Path(), help='Output directory for multiple pages')
@click.pass_context
def page(ctx, page_id, output, include_frontmatter, include_children, output_dir):
    """Export a single page to markdown.

    If --include-children is set, all child pages will also be exported.
    """
    client = ctx.obj['client']

    try:
        # Get page with body
        page_data = client.get_page_by_id(
            page_id,
            expand='body.storage,version,space,ancestors'
        )

        pages_to_export = [page_data]

        # Get children if requested
        if include_children:
            children = client.get_page_child_by_type(page_id, type='page', limit=100)
            if isinstance(children, list):
                for child in children:
                    child_data = client.get_page_by_id(
                        child['id'],
                        expand='body.storage,version,space,ancestors'
                    )
                    pages_to_export.append(child_data)

        exported = []
        for p in pages_to_export:
            result = _export_page(p, output, output_dir, include_frontmatter, ctx.obj['quiet'])
            exported.append(result)

        if ctx.obj['json']:
            format_output(exported, as_json=True)
            return

        if not ctx.obj['quiet']:
            success(f"Exported {len(exported)} page(s)")
            for exp in exported:
                print(f"  {exp['file']}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to export page: {e}")
        sys.exit(1)


@cli.command()
@click.argument('space_key')
@click.option('--output-dir', '-d', type=click.Path(), required=True,
              help='Output directory')
@click.option('--include-frontmatter', '-f', is_flag=True, help='Include YAML frontmatter')
@click.option('--limit', '-l', default=100, help='Maximum pages to export')
@click.pass_context
def space(ctx, space_key, output_dir, include_frontmatter, limit):
    """Export all pages from a space to markdown files."""
    client = ctx.obj['client']

    try:
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get all pages in space
        pages = client.get_all_pages_from_space(space_key, limit=limit)

        exported = []
        for p in pages:
            # Get full page data
            page_data = client.get_page_by_id(
                p['id'],
                expand='body.storage,version,space,ancestors'
            )
            result = _export_page(page_data, None, str(output_path), include_frontmatter, ctx.obj['quiet'])
            exported.append(result)

        if ctx.obj['json']:
            format_output(exported, as_json=True)
            return

        if not ctx.obj['quiet']:
            success(f"Exported {len(exported)} page(s) from space '{space_key}'")
            print(f"Output directory: {output_path}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to export space: {e}")
        sys.exit(1)


def _export_page(page_data: dict, output: str | None, output_dir: str | None,
                 include_frontmatter: bool, quiet: bool) -> dict:
    """Export a single page to markdown."""
    title = page_data.get('title', 'Untitled')
    page_id = page_data.get('id', '')
    space_key = page_data.get('space', {}).get('key', '')
    version = page_data.get('version', {}).get('number', 1)

    # Get HTML body
    body_html = page_data.get('body', {}).get('storage', {}).get('value', '')

    # Convert to markdown
    markdown_content = _html_to_markdown(body_html)

    # Build frontmatter if requested
    if include_frontmatter:
        frontmatter = f"""---
title: "{title}"
page_id: {page_id}
space: {space_key}
version: {version}
exported: {datetime.now().isoformat()}
---

"""
        markdown_content = frontmatter + markdown_content

    # Determine output path
    if output:
        file_path = Path(output)
    elif output_dir:
        # Create safe filename from title
        safe_title = _safe_filename(title)
        file_path = Path(output_dir) / f"{safe_title}.md"
    else:
        safe_title = _safe_filename(title)
        file_path = Path(f"{safe_title}.md")

    # Write file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    if quiet:
        print(str(file_path))

    return {
        'id': page_id,
        'title': title,
        'file': str(file_path),
    }


def _html_to_markdown(html: str) -> str:
    """Convert Confluence storage format (HTML) to markdown."""
    # Pre-process Confluence-specific macros
    html = _convert_confluence_macros(html)

    # Convert HTML to markdown
    markdown = md(
        html,
        heading_style='atx',
        code_language_callback=_get_code_language,
        strip=['script', 'style'],
    )

    # Clean up extra whitespace
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)

    return markdown.strip()


def _convert_confluence_macros(html: str) -> str:
    """Convert Confluence-specific macros to HTML equivalents."""
    # Code blocks: <ac:structured-macro ac:name="code">
    html = re.sub(
        r'<ac:structured-macro[^>]*ac:name="code"[^>]*>.*?'
        r'<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>.*?'
        r'</ac:structured-macro>',
        r'<pre><code>\1</code></pre>',
        html,
        flags=re.DOTALL
    )

    # Info/note/warning panels
    for panel_type in ['info', 'note', 'warning', 'tip']:
        html = re.sub(
            rf'<ac:structured-macro[^>]*ac:name="{panel_type}"[^>]*>.*?'
            r'<ac:rich-text-body>(.*?)</ac:rich-text-body>.*?'
            r'</ac:structured-macro>',
            rf'<blockquote><strong>{panel_type.upper()}:</strong> \1</blockquote>',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )

    # Expand macros
    html = re.sub(
        r'<ac:structured-macro[^>]*ac:name="expand"[^>]*>.*?'
        r'<ac:rich-text-body>(.*?)</ac:rich-text-body>.*?'
        r'</ac:structured-macro>',
        r'<details><summary>Details</summary>\1</details>',
        html,
        flags=re.DOTALL
    )

    # Remove remaining unhandled macros
    html = re.sub(r'<ac:[^>]*>.*?</ac:[^>]*>', '', html, flags=re.DOTALL)
    html = re.sub(r'<ac:[^/]*/?>', '', html)

    # Convert Confluence images
    html = re.sub(
        r'<ri:attachment ri:filename="([^"]+)"[^/]*/?>',
        r'<img src="\1" alt="\1">',
        html
    )

    return html


def _get_code_language(el) -> str | None:
    """Extract code language from element."""
    # Try to get language from class or data attribute
    if el.get('class'):
        classes = el.get('class', [])
        for cls in classes:
            if cls.startswith('language-'):
                return cls.replace('language-', '')
    return None


def _safe_filename(title: str) -> str:
    """Convert title to safe filename."""
    # Remove/replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = re.sub(r'\s+', '-', safe)
    safe = safe.strip('-')
    return safe[:100]  # Limit length


if __name__ == '__main__':
    cli()
