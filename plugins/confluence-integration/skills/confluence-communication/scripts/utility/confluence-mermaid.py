#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
#     "requests>=2.28.0",
# ]
# ///
"""Confluence Mermaid diagram rendering - render and embed Mermaid diagrams."""

import sys
import base64
import subprocess
import tempfile
import shutil
from pathlib import Path

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
import requests
from lib.client import get_confluence_client
from lib.output import format_output, error, success, warning


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--env-file', type=click.Path(exists=False), help='Path to environment file')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json, quiet, env_file, debug):
    """Render and manage Mermaid diagrams."""
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json
    ctx.obj['quiet'] = quiet
    ctx.obj['debug'] = debug
    ctx.obj['env_file'] = env_file

    # Check for mermaid-cli availability
    ctx.obj['mmdc_available'] = shutil.which('mmdc') is not None


@cli.command()
@click.argument('input_file', type=click.Path(exists=True), required=False)
@click.option('--text', '-t', help='Mermaid diagram code')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'output_format', type=click.Choice(['svg', 'png', 'pdf']),
              default='svg', help='Output format (default: svg)')
@click.option('--theme', type=click.Choice(['default', 'dark', 'forest', 'neutral']),
              default='default', help='Mermaid theme')
@click.option('--background', '-b', default='white', help='Background color')
@click.option('--width', '-w', type=int, help='Output width in pixels')
@click.option('--height', '-h', type=int, help='Output height in pixels')
@click.pass_context
def render(ctx, input_file, text, output, output_format, theme, background, width, height):
    """Render a Mermaid diagram to image.

    Requires mermaid-cli (mmdc) to be installed:
      npm install -g @mermaid-js/mermaid-cli

    Or use the --api flag to render via Mermaid.ink API (no local install needed).
    """
    if not input_file and not text:
        error("Provide either INPUT_FILE or --text option")
        sys.exit(1)

    # Get mermaid code
    if input_file:
        with open(input_file, 'r', encoding='utf-8') as f:
            mermaid_code = f.read()
    else:
        mermaid_code = text

    # Determine output path
    if not output:
        output = f"diagram.{output_format}"

    try:
        if ctx.obj['mmdc_available']:
            # Use local mermaid-cli
            _render_with_mmdc(mermaid_code, output, output_format, theme, background, width, height)
        else:
            # Fallback to mermaid.ink API
            warning("mermaid-cli (mmdc) not found, using mermaid.ink API")
            _render_with_api(mermaid_code, output, output_format, theme, background)

        if ctx.obj['quiet']:
            print(output)
            return

        success(f"Diagram rendered: {output}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to render diagram: {e}")
        sys.exit(1)


@cli.command('to-storage')
@click.argument('input_file', type=click.Path(exists=True), required=False)
@click.option('--text', '-t', help='Mermaid diagram code')
@click.option('--format', 'output_format', type=click.Choice(['svg', 'png']),
              default='svg', help='Image format (default: svg)')
@click.option('--theme', type=click.Choice(['default', 'dark', 'forest', 'neutral']),
              default='default', help='Mermaid theme')
@click.pass_context
def to_storage(ctx, input_file, text, output_format, theme):
    """Convert Mermaid diagram to Confluence storage format (embedded image).

    Returns HTML that can be used in page body content.
    """
    if not input_file and not text:
        error("Provide either INPUT_FILE or --text option")
        sys.exit(1)

    # Get mermaid code
    if input_file:
        with open(input_file, 'r', encoding='utf-8') as f:
            mermaid_code = f.read()
    else:
        mermaid_code = text

    try:
        # Render to temporary file
        with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as tmp:
            tmp_path = tmp.name

        if ctx.obj['mmdc_available']:
            _render_with_mmdc(mermaid_code, tmp_path, output_format, theme, 'white', None, None)
        else:
            _render_with_api(mermaid_code, tmp_path, output_format, theme, 'white')

        # Read and encode
        with open(tmp_path, 'rb') as f:
            image_data = f.read()

        # Clean up
        Path(tmp_path).unlink()

        # Create data URL or storage format
        if output_format == 'svg':
            # SVG can be embedded directly
            mime_type = 'image/svg+xml'
        else:
            mime_type = 'image/png'

        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_data}"

        # Create HTML for Confluence
        html = f'<img src="{data_url}" alt="Mermaid Diagram" />'

        if ctx.obj['json']:
            format_output({
                'html': html,
                'format': output_format,
                'size': len(image_data),
            }, as_json=True)
            return

        print(html)

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to convert diagram: {e}")
        sys.exit(1)


@cli.command()
@click.argument('page_id')
@click.argument('input_file', type=click.Path(exists=True), required=False)
@click.option('--text', '-t', help='Mermaid diagram code')
@click.option('--name', '-n', default='diagram', help='Attachment name (without extension)')
@click.option('--format', 'output_format', type=click.Choice(['svg', 'png']),
              default='svg', help='Image format (default: svg)')
@click.option('--theme', type=click.Choice(['default', 'dark', 'forest', 'neutral']),
              default='default', help='Mermaid theme')
@click.option('--dry-run', is_flag=True, help='Preview without uploading')
@click.pass_context
def upload(ctx, page_id, input_file, text, name, output_format, theme, dry_run):
    """Render Mermaid diagram and upload as attachment to a page."""
    if not input_file and not text:
        error("Provide either INPUT_FILE or --text option")
        sys.exit(1)

    # Get mermaid code
    if input_file:
        with open(input_file, 'r', encoding='utf-8') as f:
            mermaid_code = f.read()
    else:
        mermaid_code = text

    attachment_name = f"{name}.{output_format}"

    if dry_run:
        print("DRY RUN - Would upload diagram:")
        print(f"  Page ID: {page_id}")
        print(f"  Attachment: {attachment_name}")
        print(f"  Format: {output_format}")
        print(f"  Theme: {theme}")
        return

    try:
        # Render to temporary file
        with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as tmp:
            tmp_path = tmp.name

        if ctx.obj['mmdc_available']:
            _render_with_mmdc(mermaid_code, tmp_path, output_format, theme, 'white', None, None)
        else:
            _render_with_api(mermaid_code, tmp_path, output_format, theme, 'white')

        # Upload to Confluence
        client = get_confluence_client(ctx.obj.get('env_file'))
        result = client.attach_file(
            filename=tmp_path,
            name=attachment_name,
            page_id=page_id,
            comment=f"Mermaid diagram: {name}"
        )

        # Clean up
        Path(tmp_path).unlink()

        if ctx.obj['quiet']:
            print(attachment_name)
            return

        if ctx.obj['json']:
            format_output(result, as_json=True)
            return

        success(f"Diagram uploaded: {attachment_name}")
        print(f"Page ID: {page_id}")
        print(f"Use in page: !{attachment_name}!")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Failed to upload diagram: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def check(ctx):
    """Check if mermaid-cli is installed."""
    mmdc_path = shutil.which('mmdc')

    if mmdc_path:
        # Get version
        try:
            result = subprocess.run(['mmdc', '--version'], capture_output=True, text=True)
            version = result.stdout.strip() or result.stderr.strip()
        except Exception:
            version = 'unknown'

        if ctx.obj['json']:
            format_output({
                'installed': True,
                'path': mmdc_path,
                'version': version,
            }, as_json=True)
            return

        success(f"mermaid-cli installed: {mmdc_path}")
        print(f"Version: {version}")
    else:
        if ctx.obj['json']:
            format_output({
                'installed': False,
                'fallback': 'mermaid.ink API',
            }, as_json=True)
            return

        warning("mermaid-cli (mmdc) not installed")
        print("\nTo install:")
        print("  npm install -g @mermaid-js/mermaid-cli")
        print("\nFallback: mermaid.ink API will be used for rendering")


def _render_with_mmdc(code: str, output: str, fmt: str, theme: str,
                       background: str, width: int | None, height: int | None):
    """Render using local mermaid-cli."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as tmp:
        tmp.write(code)
        tmp_input = tmp.name

    try:
        cmd = ['mmdc', '-i', tmp_input, '-o', output, '-t', theme, '-b', background]

        # Auto-detect puppeteer config for Linux sandbox workaround
        puppeteer_config = Path.home() / '.config' / 'mermaid' / 'puppeteer-config.json'
        if puppeteer_config.exists():
            cmd.extend(['-p', str(puppeteer_config)])

        if width:
            cmd.extend(['-w', str(width)])
        if height:
            cmd.extend(['-H', str(height)])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"mmdc failed: {result.stderr}")

    finally:
        Path(tmp_input).unlink()


def _render_with_api(code: str, output: str, fmt: str, theme: str, background: str):
    """Render using mermaid.ink API."""
    # Encode the mermaid code for URL
    encoded = base64.urlsafe_b64encode(code.encode()).decode()

    # Build URL
    url = f"https://mermaid.ink/img/{encoded}"

    if fmt == 'svg':
        url = f"https://mermaid.ink/svg/{encoded}"

    # Add theme parameter
    if theme != 'default':
        url += f"?theme={theme}"

    # Download the image
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with open(output, 'wb') as f:
        f.write(response.content)


if __name__ == '__main__':
    cli()
