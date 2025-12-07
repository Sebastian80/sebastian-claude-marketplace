#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click>=8.1.0",
#     "markdownify>=0.11.0",
#     "markdown>=3.5.0",
# ]
# ///
"""Confluence format conversion - convert between markdown and wiki markup."""

import sys
import re
from pathlib import Path

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
import markdown
from markdownify import markdownify as md
from lib.output import error, success


@click.group()
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, debug):
    """Convert between Confluence and markdown formats."""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug


@cli.command('to-wiki')
@click.argument('input_file', type=click.Path(exists=True), required=False)
@click.option('--text', '-t', help='Markdown text to convert')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.pass_context
def to_wiki(ctx, input_file, text, output):
    """Convert markdown to Confluence wiki markup.

    Reads from file or --text option. Output to stdout or --output file.
    """
    if not input_file and not text:
        error("Provide either INPUT_FILE or --text option")
        sys.exit(1)

    try:
        # Get input
        if input_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
        else:
            md_content = text

        # Convert markdown -> HTML -> wiki markup
        html = markdown.markdown(
            md_content,
            extensions=['fenced_code', 'tables', 'nl2br']
        )

        # Convert HTML to Confluence wiki markup
        wiki = _html_to_wiki(html)

        # Output
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(wiki)
            success(f"Converted to: {output}")
        else:
            print(wiki)

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Conversion failed: {e}")
        sys.exit(1)


@cli.command('to-markdown')
@click.argument('input_file', type=click.Path(exists=True), required=False)
@click.option('--text', '-t', help='Wiki markup or HTML to convert')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'input_format', type=click.Choice(['wiki', 'html', 'storage']),
              default='storage', help='Input format (default: storage/HTML)')
@click.pass_context
def to_markdown(ctx, input_file, text, output, input_format):
    """Convert Confluence content to markdown.

    Supports wiki markup, HTML, and Confluence storage format.
    """
    if not input_file and not text:
        error("Provide either INPUT_FILE or --text option")
        sys.exit(1)

    try:
        # Get input
        if input_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = text

        # Convert based on input format
        if input_format == 'wiki':
            # Wiki markup -> HTML -> Markdown
            html = _wiki_to_html(content)
            markdown_out = md(html, heading_style='atx')
        else:
            # HTML/storage -> Markdown
            # Pre-process Confluence macros
            content = _convert_confluence_macros(content)
            markdown_out = md(content, heading_style='atx')

        # Clean up
        markdown_out = re.sub(r'\n{3,}', '\n\n', markdown_out)
        markdown_out = markdown_out.strip()

        # Output
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(markdown_out)
            success(f"Converted to: {output}")
        else:
            print(markdown_out)

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Conversion failed: {e}")
        sys.exit(1)


def _html_to_wiki(html: str) -> str:
    """Convert HTML to Confluence wiki markup."""
    wiki = html

    # Headings
    for i in range(6, 0, -1):
        wiki = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', rf'h{i}. \1\n', wiki, flags=re.DOTALL)

    # Bold
    wiki = re.sub(r'<strong[^>]*>(.*?)</strong>', r'*\1*', wiki, flags=re.DOTALL)
    wiki = re.sub(r'<b[^>]*>(.*?)</b>', r'*\1*', wiki, flags=re.DOTALL)

    # Italic
    wiki = re.sub(r'<em[^>]*>(.*?)</em>', r'_\1_', wiki, flags=re.DOTALL)
    wiki = re.sub(r'<i[^>]*>(.*?)</i>', r'_\1_', wiki, flags=re.DOTALL)

    # Inline code
    wiki = re.sub(r'<code[^>]*>(.*?)</code>', r'{{\1}}', wiki, flags=re.DOTALL)

    # Code blocks
    wiki = re.sub(
        r'<pre[^>]*><code[^>]*class="language-(\w+)"[^>]*>(.*?)</code></pre>',
        r'{code:\1}\n\2\n{code}',
        wiki,
        flags=re.DOTALL
    )
    wiki = re.sub(
        r'<pre[^>]*>(.*?)</pre>',
        r'{code}\n\1\n{code}',
        wiki,
        flags=re.DOTALL
    )

    # Links
    wiki = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2|\1]', wiki, flags=re.DOTALL)

    # Images
    wiki = re.sub(r'<img[^>]*src="([^"]*)"[^>]*/?>',r'!\1!', wiki)

    # Unordered lists
    wiki = re.sub(r'<ul[^>]*>', '', wiki)
    wiki = re.sub(r'</ul>', '', wiki)
    wiki = re.sub(r'<li[^>]*>(.*?)</li>', r'* \1\n', wiki, flags=re.DOTALL)

    # Ordered lists
    wiki = re.sub(r'<ol[^>]*>', '', wiki)
    wiki = re.sub(r'</ol>', '', wiki)

    # Paragraphs
    wiki = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', wiki, flags=re.DOTALL)

    # Line breaks
    wiki = re.sub(r'<br\s*/?>', '\n', wiki)

    # Blockquotes
    wiki = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'{quote}\1{quote}', wiki, flags=re.DOTALL)

    # Tables (basic support)
    wiki = re.sub(r'<table[^>]*>', '', wiki)
    wiki = re.sub(r'</table>', '', wiki)
    wiki = re.sub(r'<thead[^>]*>', '', wiki)
    wiki = re.sub(r'</thead>', '', wiki)
    wiki = re.sub(r'<tbody[^>]*>', '', wiki)
    wiki = re.sub(r'</tbody>', '', wiki)
    wiki = re.sub(r'<tr[^>]*>', '', wiki)
    wiki = re.sub(r'</tr>', '|\n', wiki)
    wiki = re.sub(r'<th[^>]*>(.*?)</th>', r'||\1', wiki, flags=re.DOTALL)
    wiki = re.sub(r'<td[^>]*>(.*?)</td>', r'|\1', wiki, flags=re.DOTALL)

    # Clean up remaining HTML
    wiki = re.sub(r'<[^>]+>', '', wiki)

    # Clean up whitespace
    wiki = re.sub(r'\n{3,}', '\n\n', wiki)
    wiki = wiki.strip()

    return wiki


def _wiki_to_html(wiki: str) -> str:
    """Convert Confluence wiki markup to HTML."""
    html = wiki

    # Headings
    for i in range(1, 7):
        html = re.sub(rf'^h{i}\.\s+(.*)$', rf'<h{i}>\1</h{i}>', html, flags=re.MULTILINE)

    # Bold
    html = re.sub(r'\*([^*]+)\*', r'<strong>\1</strong>', html)

    # Italic
    html = re.sub(r'_([^_]+)_', r'<em>\1</em>', html)

    # Inline code
    html = re.sub(r'\{\{([^}]+)\}\}', r'<code>\1</code>', html)

    # Code blocks
    html = re.sub(
        r'\{code:(\w+)\}(.*?)\{code\}',
        r'<pre><code class="language-\1">\2</code></pre>',
        html,
        flags=re.DOTALL
    )
    html = re.sub(
        r'\{code\}(.*?)\{code\}',
        r'<pre><code>\1</code></pre>',
        html,
        flags=re.DOTALL
    )

    # Links
    html = re.sub(r'\[([^|]+)\|([^\]]+)\]', r'<a href="\2">\1</a>', html)

    # Images
    html = re.sub(r'!([^!]+)!', r'<img src="\1">', html)

    # Unordered lists
    html = re.sub(r'^\*\s+(.*)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # Ordered lists
    html = re.sub(r'^#\s+(.*)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # Quotes
    html = re.sub(r'\{quote\}(.*?)\{quote\}', r'<blockquote>\1</blockquote>', html, flags=re.DOTALL)

    # Panels
    for panel_type in ['info', 'note', 'warning', 'tip']:
        html = re.sub(
            rf'\{{{panel_type}\}}(.*?)\{{{panel_type}\}}',
            rf'<div class="{panel_type}">\1</div>',
            html,
            flags=re.DOTALL
        )

    # Tables (basic)
    html = re.sub(r'\|\|([^|]+)', r'<th>\1</th>', html)
    html = re.sub(r'\|([^|]+)', r'<td>\1</td>', html)

    return html


def _convert_confluence_macros(html: str) -> str:
    """Convert Confluence-specific macros to standard HTML."""
    # Code blocks
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

    # Remove remaining macros
    html = re.sub(r'<ac:[^>]*>.*?</ac:[^>]*>', '', html, flags=re.DOTALL)
    html = re.sub(r'<ac:[^/]*/?>', '', html)

    return html


if __name__ == '__main__':
    cli()
