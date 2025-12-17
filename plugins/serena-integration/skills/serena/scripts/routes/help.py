"""
Help endpoint for Serena CLI.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

HELP_TEXT = """Serena CLI - Semantic Code Navigation
========================================

serena status                     Get project status
serena activate [--project PATH]  Activate a project

serena find PATTERN               Find symbols by pattern
  --kind CLASS|METHOD|...         Filter by symbol kind
  --path PATH                     Filter by path
  --body                          Include symbol body
  --depth N                       Include nested symbols
  --exact                         Exact match only

serena refs SYMBOL FILE           Find references to symbol
  --all                           Include all references

serena overview FILE              Get file structure overview
serena search PATTERN             Regex search in code
  --path PATH                     Filter by path
  --glob GLOB                     Filter by glob pattern

serena recipe NAME                Run pre-built search recipes
  list                            List available recipes

serena tools                      List available Serena MCP tools

Memory commands:
  serena memory list [--folder F] List memories
  serena memory read NAME         Read a memory
  serena memory write NAME        Write a memory (--content via stdin)
  serena memory delete NAME       Delete a memory
  serena memory tree              Show memory folder structure
  serena memory search PATTERN    Search memories
  serena memory archive NAME      Archive a memory
  serena memory move SRC DEST     Move/rename a memory
  serena memory stats             Show memory statistics

Edit commands:
  serena edit replace SYMBOL FILE Replace symbol body
  serena edit after SYMBOL FILE   Insert after symbol
  serena edit before SYMBOL FILE  Insert before symbol
  serena edit rename SYMBOL FILE  Rename symbol
"""


@router.get("/help")
async def help():
    """Show available Serena commands."""
    return PlainTextResponse(HELP_TEXT)
