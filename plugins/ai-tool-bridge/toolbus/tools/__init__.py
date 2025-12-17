"""
Tools Framework - Pydantic-based tool definitions with auto-routing.

This module provides a clean abstraction for defining plugin tools:

1. Define tools as Pydantic models with Field descriptions
2. Implement execute() for business logic
3. Register with a router - routes auto-generated

Example:
    from pydantic import Field
    from toolbus.tools import Tool, ToolContext, register_tools

    class GetIssue(Tool):
        '''Get Jira issue by key.'''
        key: str = Field(..., description="Issue key like PROJ-123")
        format: str = Field("json", description="Output: json, human, ai")

        async def execute(self, ctx: ToolContext) -> dict:
            issue = ctx.client.issue(self.key)
            return ctx.formatted(issue, self.format, "issue")

    class CreateIssue(Tool):
        '''Create new Jira issue.'''
        project: str = Field(..., description="Project key")
        summary: str = Field(..., description="Issue title")
        issue_type: str = Field(..., alias="type", description="Issue type")

        class Meta:
            method = "POST"
            path = "/create"

        async def execute(self, ctx: ToolContext) -> dict:
            return ctx.client.create_issue(fields={...})

    # In plugin:
    router = APIRouter()
    register_tools(router, [GetIssue, CreateIssue], Depends(jira), formatter=formatted)

Benefits:
- ~8 lines per tool instead of ~40
- Same OpenAPI output as manual routes
- Same CLI behavior via bridge
- Type validation via Pydantic
- Descriptions in one place (Field)
"""

from .base import Tool, ToolContext, ToolMeta, ToolResult
from .registry import ToolRegistry, register_tools

__all__ = [
    # Base classes
    "Tool",
    "ToolContext",
    "ToolMeta",
    "ToolResult",
    # Registration
    "ToolRegistry",
    "register_tools",
]
