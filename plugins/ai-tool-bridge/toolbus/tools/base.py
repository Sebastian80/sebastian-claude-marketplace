"""
Tool Base Class - Pydantic-based tool definitions.

Tools are the core abstraction for plugin functionality. Each tool:
- Defines its parameters via Pydantic Fields
- Implements execute() for business logic
- Gets auto-generated routes, CLI, and OpenAPI docs

Example:
    class GetIssue(Tool):
        '''Get Jira issue by key.'''
        key: str = Field(..., description="Issue key like PROJ-123")
        format: str = Field("json", description="Output: json, human, ai")

        class Meta:
            method = "GET"
            path = "/issue/{key}"

        async def execute(self, ctx: ToolContext) -> Any:
            issue = ctx.client.issue(self.key)
            return ctx.format(issue, self.format, "issue")
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict

__all__ = [
    "Tool",
    "ToolContext",
    "ToolMeta",
    "ToolResult",
]


@dataclass
class ToolContext:
    """Context passed to tool execution.

    Provides access to:
    - client: The connector client (e.g., Jira API client)
    - format: Formatter function for output formatting
    - request: Optional FastAPI request for advanced use cases
    """
    client: Any
    format: Callable[[Any, str, str], Any] | None = None
    request: Any | None = None

    def formatted(self, data: Any, fmt: str, entity: str) -> Any:
        """Format data using the registered formatter.

        Args:
            data: Raw data to format
            fmt: Format type (json, human, ai, markdown)
            entity: Entity type for format selection

        Returns:
            Formatted data
        """
        if self.format:
            return self.format(data, fmt, entity)
        return data


class ToolMeta:
    """Metadata for tool routing and behavior.

    Define as inner class 'Meta' on Tool subclasses:
        class GetIssue(Tool):
            class Meta:
                method = "GET"
                path = "/issue/{key}"
                tags = ["issues"]
    """
    method: str = "POST"  # HTTP method: GET, POST, PUT, PATCH, DELETE
    path: str | None = None  # URL path, auto-generated if None
    tags: list[str] | None = None  # OpenAPI tags
    summary: str | None = None  # Override docstring for OpenAPI summary
    deprecated: bool = False  # Mark as deprecated in OpenAPI


@dataclass
class ToolResult:
    """Structured result from tool execution.

    Tools can return raw data or ToolResult for more control:
        return ToolResult(data=issue, status=200)
        return ToolResult(error="Not found", status=404)
    """
    data: Any = None
    error: str | None = None
    status: int = 200
    headers: dict[str, str] | None = None

    @property
    def success(self) -> bool:
        return self.error is None and 200 <= self.status < 300


class Tool(BaseModel, ABC):
    """Base class for all tools.

    Subclass and implement execute() to create a tool:

        class CreateIssue(Tool):
            '''Create new Jira issue.'''
            project: str = Field(..., description="Project key")
            summary: str = Field(..., description="Issue title")
            issue_type: str = Field(..., alias="type", description="Issue type")

            class Meta:
                method = "POST"
                path = "/create"

            async def execute(self, ctx: ToolContext) -> dict:
                return ctx.client.create_issue(fields={
                    "project": {"key": self.project},
                    "summary": self.summary,
                    "issuetype": {"name": self.issue_type},
                })

    Features:
    - Parameters defined as Pydantic fields with descriptions
    - Type validation automatic via Pydantic
    - OpenAPI schema auto-generated
    - HTTP method and path configurable via Meta class
    - Async execution with client access via ToolContext
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        populate_by_name=True,  # Allow alias usage
        str_strip_whitespace=True,  # Clean string inputs
    )

    # Default Meta - subclasses override with inner class
    class Meta(ToolMeta):
        pass

    @abstractmethod
    async def execute(self, ctx: ToolContext) -> Any:
        """Execute the tool logic.

        Args:
            ctx: Tool context with client and utilities

        Returns:
            Result data (dict, ToolResult, or any JSON-serializable)

        Raises:
            Any exception - will be caught and returned as error
        """
        ...

    @classmethod
    def get_meta(cls) -> ToolMeta:
        """Get tool metadata, merging with defaults."""
        meta = ToolMeta()
        if hasattr(cls, "Meta"):
            for attr in ("method", "path", "tags", "summary", "deprecated"):
                if hasattr(cls.Meta, attr):
                    setattr(meta, attr, getattr(cls.Meta, attr))
        return meta

    @classmethod
    def get_path(cls) -> str:
        """Get URL path for this tool.

        Uses Meta.path if defined, otherwise generates from class name:
        - GetIssue -> /issue/{key} (if 'key' field exists)
        - CreateIssue -> /create
        - SearchIssues -> /search
        """
        meta = cls.get_meta()
        if meta.path:
            return meta.path

        # Auto-generate from class name
        name = cls.__name__

        # Remove common prefixes
        for prefix in ("Get", "Create", "Update", "Delete", "List", "Search"):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break

        # Convert to snake_case path
        path = ""
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                path += "-"
            path += char.lower()

        # Add path parameter if tool has 'key' or 'id' field
        fields = cls.model_fields
        if "key" in fields:
            path = f"/{path}/{{key}}"
        elif "id" in fields:
            path = f"/{path}/{{id}}"
        else:
            path = f"/{path}"

        return path

    @classmethod
    def get_method(cls) -> str:
        """Get HTTP method for this tool.

        Uses Meta.method if defined, otherwise infers from class name:
        - Get*, List*, Search* -> GET
        - Create* -> POST
        - Update* -> PATCH
        - Delete* -> DELETE
        - Others -> POST
        """
        # Check if subclass explicitly defines Meta with method
        # (not inherited from Tool base class)
        if "Meta" in cls.__dict__ and hasattr(cls.Meta, "method"):
            return cls.Meta.method

        name = cls.__name__
        if name.startswith(("Get", "List", "Search", "Find")):
            return "GET"
        elif name.startswith("Create"):
            return "POST"
        elif name.startswith("Update"):
            return "PATCH"
        elif name.startswith("Delete"):
            return "DELETE"
        else:
            return "POST"

    @classmethod
    def get_summary(cls) -> str:
        """Get OpenAPI summary from docstring or Meta."""
        meta = cls.get_meta()
        if meta.summary:
            return meta.summary

        doc = cls.__doc__ or ""
        # First line of docstring
        return doc.split("\n")[0].strip()

    @classmethod
    def get_description(cls) -> str:
        """Get full description from docstring."""
        return (cls.__doc__ or "").strip()
