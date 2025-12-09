"""
Serena CLI - Command Line Interface.

Provides a typer-based CLI for interacting with Serena MCP server.
All commands use async/await internally for optimal performance.

Usage:
    serena find Customer --kind class
    serena refs "Customer/getName" src/Entity/Customer.php
    serena overview src/Entity/Customer.php
    serena status
"""

from __future__ import annotations

import asyncio
import sys
from typing import Annotated, Optional

import typer

from . import __version__
from .client import SerenaClient, SerenaError, SymbolKind
from .formatters import OutputFormatter

# Create typer app
app = typer.Typer(
    name="serena",
    help="Semantic code navigation via LSP.",
    no_args_is_help=True,
    add_completion=False,
)

# Memory subcommand group
memory_app = typer.Typer(help="Memory operations (list, read, write, delete, etc.)")
app.add_typer(memory_app, name="memory")

# Edit subcommand group
edit_app = typer.Typer(help="Symbol-based code editing")
app.add_typer(edit_app, name="edit")


def _run_async(coro):
    """Run async function synchronously."""
    return asyncio.run(coro)


def _get_formatter(json_mode: bool) -> OutputFormatter:
    """Create output formatter."""
    return OutputFormatter(json_mode=json_mode)


# =============================================================================
# Main Commands
# =============================================================================


@app.command()
def find(
    pattern: Annotated[str, typer.Argument(help="Symbol name or pattern (supports wildcards like 'get*')")],
    kind: Annotated[Optional[str], typer.Option("--kind", "-k", help="Filter: class, method, interface, function")] = None,
    path: Annotated[Optional[str], typer.Option("--path", "-p", help="Restrict to path (e.g., 'src/Meyer/')")] = None,
    body: Annotated[bool, typer.Option("--body", "-b", help="Include symbol body/implementation")] = False,
    depth: Annotated[int, typer.Option("--depth", "-d", help="Traversal depth (0=symbol, 1=children)")] = 0,
    exact: Annotated[bool, typer.Option("--exact", "-e", help="Exact match only")] = False,
    json_mode: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = False,
):
    """
    Find symbols by name pattern.

    Examples:
        serena find Customer --kind class
        serena find "get*" --kind method --path src/
        serena find Payment --body --path src/Meyer/
    """
    fmt = _get_formatter(json_mode)

    async def _find():
        async with SerenaClient() as client:
            symbols = await client.find_symbol(
                pattern,
                kind=kind,
                path=path,
                body=body,
                depth=depth,
                exact=exact,
            )
            print(fmt.format_symbols(symbols, show_body=body))

    try:
        _run_async(_find())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def refs(
    symbol: Annotated[str, typer.Argument(help="Symbol path (e.g., 'Customer/getName')")],
    file: Annotated[str, typer.Argument(help="File where symbol is defined")],
    all_refs: Annotated[bool, typer.Option("--all", "-a", help="Show all references")] = False,
    json_mode: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = False,
):
    """
    Find all references to a symbol.

    Examples:
        serena refs "Customer/getName" src/Entity/Customer.php
        serena refs Order/save src/Entity/Order.php --all
    """
    fmt = _get_formatter(json_mode)

    async def _refs():
        async with SerenaClient() as client:
            references = await client.find_refs(symbol, file, all_refs=all_refs)
            print(fmt.format_refs(references, symbol, show_all=all_refs))

    try:
        _run_async(_refs())
    except SerenaError as e:
        print(fmt.format_error(str(e), hint="Verify symbol exists with 'serena find'"), file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def overview(
    file: Annotated[str, typer.Argument(help="File to analyze")],
    json_mode: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = False,
):
    """
    Get overview of symbols in a file.

    Example:
        serena overview src/Entity/Customer.php
    """
    fmt = _get_formatter(json_mode)

    async def _overview():
        async with SerenaClient() as client:
            symbols = await client.get_overview(file)
            print(fmt.format_overview(symbols, file))

    try:
        _run_async(_overview())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def search(
    pattern: Annotated[str, typer.Argument(help="Regex pattern to search for")],
    glob: Annotated[Optional[str], typer.Option("--glob", "-g", help="File glob filter (e.g., '*.php')")] = None,
    path: Annotated[Optional[str], typer.Option("--path", "-p", help="Restrict to path")] = None,
    json_mode: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = False,
):
    """
    Search for regex pattern in code.

    Examples:
        serena search "implements.*Interface" --glob "*.php"
        serena search "#\\[ORM\\\\Entity" --path src/
    """
    fmt = _get_formatter(json_mode)

    async def _search():
        async with SerenaClient() as client:
            results = await client.search(pattern, glob=glob, path=path)
            print(fmt.format_search(results, pattern))

    try:
        _run_async(_search())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def status(
    json_mode: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = False,
):
    """Check Serena connection and configuration."""
    fmt = _get_formatter(json_mode)

    async def _status():
        async with SerenaClient() as client:
            config = await client.get_status()
            print(fmt.format_status(config))

    try:
        _run_async(_status())
    except SerenaError as e:
        print(fmt.format_error(str(e), hint="Is Serena server running?"), file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def activate(
    project: Annotated[Optional[str], typer.Argument(help="Project path or name")] = None,
):
    """
    Activate a project.

    Defaults to current directory if no project specified.
    """
    fmt = _get_formatter(False)

    async def _activate():
        async with SerenaClient() as client:
            result = await client.activate_project(project)
            print(fmt.format_success(result))

    try:
        _run_async(_activate())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    print(f"serena-cli {__version__}")


# =============================================================================
# Memory Commands
# =============================================================================


@memory_app.command("list")
def memory_list(
    folder: Annotated[Optional[str], typer.Argument(help="Folder to filter (e.g., 'active/tasks')")] = None,
    json_mode: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = False,
):
    """List memories, optionally filtered by folder."""
    fmt = _get_formatter(json_mode)

    async def _list():
        async with SerenaClient() as client:
            memories = await client.memory_list(folder)
            print(fmt.format_memory_list(memories))

    try:
        _run_async(_list())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@memory_app.command("read")
def memory_read(
    name: Annotated[str, typer.Argument(help="Memory name/path")],
):
    """Read a memory by name."""
    async def _read():
        async with SerenaClient() as client:
            content = await client.memory_read(name)
            print(content)

    try:
        _run_async(_read())
    except SerenaError as e:
        print(e, file=sys.stderr)
        raise typer.Exit(1)


@memory_app.command("write")
def memory_write(
    name: Annotated[str, typer.Argument(help="Memory name/path")],
    content: Annotated[str, typer.Argument(help="Content (use '-' for stdin)")] = "-",
):
    """Write a memory (folders auto-created)."""
    fmt = _get_formatter(False)

    if content == "-":
        content = sys.stdin.read()

    async def _write():
        async with SerenaClient() as client:
            result = await client.memory_write(name, content)
            print(fmt.format_success(result))

    try:
        _run_async(_write())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@memory_app.command("delete")
def memory_delete(
    name: Annotated[str, typer.Argument(help="Memory name/path")],
):
    """Delete a memory."""
    fmt = _get_formatter(False)

    async def _delete():
        async with SerenaClient() as client:
            result = await client.memory_delete(name)
            print(fmt.format_success(result))

    try:
        _run_async(_delete())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@memory_app.command("tree")
def memory_tree(
    folder: Annotated[Optional[str], typer.Argument(help="Start from subfolder")] = None,
):
    """Show memory folder structure."""
    async def _tree():
        async with SerenaClient() as client:
            tree = await client.memory_tree(folder)
            print(tree)

    try:
        _run_async(_tree())
    except SerenaError as e:
        print(e, file=sys.stderr)
        raise typer.Exit(1)


@memory_app.command("search")
def memory_search(
    pattern: Annotated[str, typer.Argument(help="Regex pattern to search")],
    folder: Annotated[Optional[str], typer.Option("--folder", "-f", help="Limit to folder")] = None,
    json_mode: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = False,
):
    """Search memory contents."""
    import json as json_lib
    fmt = _get_formatter(json_mode)

    async def _search():
        async with SerenaClient() as client:
            results = await client.memory_search(pattern, folder)
            if json_mode:
                print(json_lib.dumps(results, indent=2))
            elif not results:
                print("No matches found.")
            else:
                print(f"Found matches in {len(results)} memories:\n")
                for match in results:
                    count = match.get("match_count", 0)
                    print(f"  {match['memory']} ({count} matches)")
                    for snippet in match.get("snippets", [])[:2]:
                        print(f"    ...{snippet.strip()[:60]}...")
                    print()

    try:
        _run_async(_search())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@memory_app.command("archive")
def memory_archive(
    name: Annotated[str, typer.Argument(help="Memory to archive")],
    category: Annotated[Optional[str], typer.Option("--category", "-c", help="Category subfolder")] = None,
):
    """Archive memory (moves to archive/YYYY-MM/)."""
    fmt = _get_formatter(False)

    async def _archive():
        async with SerenaClient() as client:
            result = await client.memory_archive(name, category)
            print(fmt.format_success(result))

    try:
        _run_async(_archive())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


# =============================================================================
# Edit Commands
# =============================================================================


@edit_app.command("replace")
def edit_replace(
    symbol: Annotated[str, typer.Argument(help="Symbol path (e.g., 'Customer/getName')")],
    file: Annotated[str, typer.Argument(help="File path")],
    body: Annotated[str, typer.Argument(help="New body (use '-' for stdin)")] = "-",
):
    """Replace a symbol's body."""
    fmt = _get_formatter(False)

    if body == "-":
        body = sys.stdin.read()

    async def _replace():
        async with SerenaClient() as client:
            result = await client.edit_replace(symbol, file, body)
            print(fmt.format_success(result))

    try:
        _run_async(_replace())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@edit_app.command("after")
def edit_after(
    symbol: Annotated[str, typer.Argument(help="Symbol path")],
    file: Annotated[str, typer.Argument(help="File path")],
    code: Annotated[str, typer.Argument(help="Code to insert (use '-' for stdin)")] = "-",
):
    """Insert code after a symbol."""
    fmt = _get_formatter(False)

    if code == "-":
        code = sys.stdin.read()

    async def _after():
        async with SerenaClient() as client:
            result = await client.edit_after(symbol, file, code)
            print(fmt.format_success(result))

    try:
        _run_async(_after())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@edit_app.command("before")
def edit_before(
    symbol: Annotated[str, typer.Argument(help="Symbol path")],
    file: Annotated[str, typer.Argument(help="File path")],
    code: Annotated[str, typer.Argument(help="Code to insert (use '-' for stdin)")] = "-",
):
    """Insert code before a symbol."""
    fmt = _get_formatter(False)

    if code == "-":
        code = sys.stdin.read()

    async def _before():
        async with SerenaClient() as client:
            result = await client.edit_before(symbol, file, code)
            print(fmt.format_success(result))

    try:
        _run_async(_before())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


@edit_app.command("rename")
def edit_rename(
    symbol: Annotated[str, typer.Argument(help="Symbol path")],
    file: Annotated[str, typer.Argument(help="File path")],
    new_name: Annotated[str, typer.Argument(help="New name")],
):
    """Rename a symbol."""
    fmt = _get_formatter(False)

    async def _rename():
        async with SerenaClient() as client:
            result = await client.edit_rename(symbol, file, new_name)
            print(fmt.format_success(result))

    try:
        _run_async(_rename())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


# =============================================================================
# Recipe Commands
# =============================================================================


@app.command()
def recipe(
    name: Annotated[str, typer.Argument(help="Recipe: entities, controllers, services, interfaces, tests")] = "list",
    json_mode: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = False,
):
    """
    Run pre-built operations.

    Available recipes:
        entities     - Find all Doctrine entities
        controllers  - Find all *Controller classes
        services     - Find all *Service classes
        interfaces   - Find all interfaces
        tests        - Find all *Test classes
    """
    fmt = _get_formatter(json_mode)

    recipes = {
        "entities": ("ORM\\\\Entity", "*.php", "src/"),
        "controllers": ("Controller", "class"),
        "services": ("Service", "class"),
        "interfaces": ("Interface", "interface"),
        "tests": ("Test", "class"),
    }

    if name == "list":
        print("Available recipes:")
        for recipe_name in recipes:
            print(f"  {recipe_name}")
        return

    if name not in recipes:
        print(fmt.format_error(f"Unknown recipe: {name}", hint=f"Available: {', '.join(recipes.keys())}"))
        raise typer.Exit(1)

    async def _recipe():
        async with SerenaClient() as client:
            if name == "entities":
                # Search for ORM\Entity attribute
                results = await client.search(r"#\[ORM\\Entity", glob="src/**/*.php")
                print(fmt.format_search(results, "Doctrine entities"))
            else:
                pattern, kind = recipes[name]
                symbols = await client.find_symbol(pattern, kind=kind)
                # Filter to only matching names
                if name in ["controllers", "tests"]:
                    suffix = "Controller" if name == "controllers" else "Test"
                    symbols = [s for s in symbols if s.get("name_path", "").endswith(suffix)]
                print(fmt.format_symbols(symbols))

    try:
        _run_async(_recipe())
    except SerenaError as e:
        print(fmt.format_error(str(e)), file=sys.stderr)
        raise typer.Exit(1)


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
