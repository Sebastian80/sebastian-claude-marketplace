"""
Tool Registry - Auto-generates FastAPI routes from Tool classes.

Converts Tool definitions into fully functional FastAPI endpoints with:
- Proper HTTP methods (GET/POST/PUT/PATCH/DELETE)
- Query/Path parameters from Pydantic fields
- OpenAPI documentation from docstrings and field descriptions
- Validation via Pydantic
- Error handling

Example:
    router = APIRouter()
    registry = ToolRegistry(router)

    registry.register(GetIssue, client_dependency=Depends(jira))
    registry.register(CreateIssue, client_dependency=Depends(jira))

    # Or register multiple at once:
    registry.register_all([GetIssue, CreateIssue, UpdateIssue], Depends(jira))
"""

import inspect
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pydantic.fields import FieldInfo

from .base import Tool, ToolContext, ToolResult

__all__ = [
    "ToolRegistry",
    "register_tools",
]


class ToolRegistry:
    """Registry for auto-generating routes from Tool classes.

    Handles the conversion of Tool definitions to FastAPI endpoints,
    preserving all parameter metadata for OpenAPI generation.
    """

    def __init__(
        self,
        router: APIRouter,
        formatter: Callable[[Any, str, str], Any] | None = None,
    ) -> None:
        """Initialize the registry.

        Args:
            router: FastAPI router to register endpoints on
            formatter: Optional formatter function for output formatting
        """
        self._router = router
        self._formatter = formatter
        self._tools: dict[str, type[Tool]] = {}
        self._fallback_paths: set[str] = set()  # Track registered fallback routes

    def register(
        self,
        tool_cls: type[Tool],
        client_dependency: Any = None,
        prefix: str = "",
    ) -> None:
        """Register a single tool and create its route.

        Args:
            tool_cls: Tool class to register
            client_dependency: FastAPI Depends() for client injection
            prefix: Optional path prefix
        """
        if not issubclass(tool_cls, Tool):
            raise TypeError(f"{tool_cls} must be a Tool subclass")

        name = tool_cls.__name__
        if name in self._tools:
            raise ValueError(f"Tool '{name}' already registered")

        self._tools[name] = tool_cls
        self._create_route(tool_cls, client_dependency, prefix)

    def register_all(
        self,
        tools: list[type[Tool]],
        client_dependency: Any = None,
        prefix: str = "",
    ) -> None:
        """Register multiple tools at once.

        Args:
            tools: List of Tool classes to register
            client_dependency: FastAPI Depends() for client injection
            prefix: Optional path prefix
        """
        for tool_cls in tools:
            self.register(tool_cls, client_dependency, prefix)

    def _create_route(
        self,
        tool_cls: type[Tool],
        client_dependency: Any,
        prefix: str,
    ) -> None:
        """Create FastAPI route for a tool.

        Dynamically builds an endpoint function with proper signature
        for FastAPI to generate correct OpenAPI documentation.
        """
        method = tool_cls.get_method()
        path = prefix + tool_cls.get_path()
        summary = tool_cls.get_summary()
        description = tool_cls.get_description()
        meta = tool_cls.get_meta()

        # Build endpoint function dynamically
        endpoint = self._build_endpoint(tool_cls, client_dependency)

        # Register with appropriate HTTP method
        route_kwargs = {
            "summary": summary,
            "description": description,
            "tags": meta.tags,
            "deprecated": meta.deprecated,
            "response_model": None,  # We handle responses manually
        }

        if method == "GET":
            self._router.get(path, **route_kwargs)(endpoint)
        elif method == "POST":
            self._router.post(path, **route_kwargs)(endpoint)
        elif method == "PUT":
            self._router.put(path, **route_kwargs)(endpoint)
        elif method == "PATCH":
            self._router.patch(path, **route_kwargs)(endpoint)
        elif method == "DELETE":
            self._router.delete(path, **route_kwargs)(endpoint)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        # Register fallback error route for missing path parameters
        self._register_fallback_route(path, method, tool_cls)

    def _register_fallback_route(
        self,
        path: str,
        method: str,
        tool_cls: type[Tool],
    ) -> None:
        """Register fallback route that returns helpful error for missing path params.

        When a tool has path parameters (e.g., /issue/{key}), this registers
        a route for the base path (e.g., /issue) that returns a usage hint
        instead of a generic 404 "Not Found" error.

        Args:
            path: Full route path including parameter placeholders (e.g., "/issue/{key}")
            method: HTTP method (GET, POST, etc.)
            tool_cls: Tool class (used for future extension, currently unused)

        Example:
            Tool with path="/issue/{key}" registers fallback at "/issue"
            that returns: "Error: key required\\n\\nUsage: issue <KEY>"
        """
        import re
        from fastapi.responses import PlainTextResponse

        # Find path parameters
        param_matches = list(re.finditer(r"/\{(\w+)\}", path))
        if not param_matches:
            return  # No path parameters, no fallback needed

        # Get the first path parameter (most common case)
        first_match = param_matches[0]
        param_name = first_match.group(1)
        base_path = path[:first_match.start()]

        # Skip if base path is empty or already registered
        if not base_path or base_path in self._fallback_paths:
            return

        self._fallback_paths.add(base_path)

        # Build usage hint from path
        # /issue/{key} -> "issue <KEY>"
        command = base_path.lstrip("/").replace("/", " ")

        async def fallback_endpoint():
            return PlainTextResponse(
                f"Error: {param_name} required\n\n"
                f"Usage: {command} <{param_name.upper()}>\n",
                status_code=400,
            )

        # Register with same method as the main route
        if method == "GET":
            self._router.get(base_path, include_in_schema=False)(fallback_endpoint)
        elif method == "POST":
            self._router.post(base_path, include_in_schema=False)(fallback_endpoint)

    def _build_endpoint(
        self,
        tool_cls: type[Tool],
        client_dependency: Any,
    ) -> Callable:
        """Build endpoint function with proper FastAPI signature.

        Creates a function that:
        1. Has parameters matching Tool fields (for OpenAPI)
        2. Validates input via Pydantic
        3. Executes the tool
        4. Handles errors
        """
        # Get field info for parameter generation
        fields = tool_cls.model_fields
        path = tool_cls.get_path()
        formatter = self._formatter

        # Determine which fields are path params (appear in {})
        path_params = set()
        import re
        for match in re.finditer(r"\{(\w+)\}", path):
            path_params.add(match.group(1))

        # Build parameter specifications for FastAPI
        param_specs = {}
        for field_name, field_info in fields.items():
            param_specs[field_name] = self._field_to_param(
                field_name, field_info, is_path=field_name in path_params
            )

        async def endpoint(
            request: Request,
            client: Any = client_dependency,
            **kwargs: Any,
        ) -> Any:
            """Auto-generated endpoint for tool execution."""
            try:
                # Validate and create tool instance
                tool = tool_cls.model_validate(kwargs)

                # Create context
                ctx = ToolContext(
                    client=client,
                    format=formatter,
                    request=request,
                )

                # Execute tool
                result = await tool.execute(ctx)

                # Handle ToolResult wrapper
                if isinstance(result, ToolResult):
                    if result.error:
                        return JSONResponse(
                            status_code=result.status,
                            content={"error": result.error},
                            headers=result.headers,
                        )
                    return JSONResponse(
                        status_code=result.status,
                        content=result.data,
                        headers=result.headers,
                    )

                return result

            except ValidationError as e:
                raise HTTPException(status_code=422, detail=e.errors())
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Dynamically set function signature for FastAPI
        endpoint = self._set_signature(endpoint, param_specs, client_dependency)
        endpoint.__name__ = f"{tool_cls.__name__}_endpoint"
        endpoint.__doc__ = tool_cls.__doc__

        return endpoint

    def _field_to_param(
        self,
        name: str,
        field: FieldInfo,
        is_path: bool,
    ) -> tuple[type, Any]:
        """Convert Pydantic field to FastAPI parameter.

        Args:
            name: Field name
            field: Pydantic FieldInfo
            is_path: Whether this is a path parameter

        Returns:
            Tuple of (type, FastAPI parameter)
        """
        # Get type annotation
        annotation = field.annotation
        if annotation is None:
            annotation = str

        # Get description and other metadata
        description = field.description or ""
        default = field.default if field.default is not None else ...
        alias = field.alias

        # Handle optional fields
        if hasattr(field, "is_required") and not field.is_required():
            if default is ...:
                default = None

        # Create FastAPI parameter
        if is_path:
            # Path parameters are always required, cannot have defaults
            param = Path(
                description=description,
                alias=alias,
            )
        else:
            param = Query(
                default=default,
                description=description,
                alias=alias,
            )

        return (annotation, param)

    def _set_signature(
        self,
        func: Callable,
        param_specs: dict[str, tuple[type, Any]],
        client_dependency: Any,
    ) -> Callable:
        """Set function signature for FastAPI introspection.

        FastAPI uses function signature to generate OpenAPI schema.
        We dynamically create a signature matching our Tool fields.
        """
        import typing

        from fastapi import Request

        # Build parameters list
        params = [
            inspect.Parameter(
                "request",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Request,
            ),
            inspect.Parameter(
                "client",
                inspect.Parameter.KEYWORD_ONLY,
                default=client_dependency,
                annotation=typing.Any,
            ),
        ]

        # Add tool parameters
        for name, (annotation, default) in param_specs.items():
            params.append(
                inspect.Parameter(
                    name,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=annotation,
                )
            )

        # Create and set new signature
        sig = inspect.Signature(parameters=params)
        func.__signature__ = sig

        # Set annotations for FastAPI
        annotations = {"request": Request, "client": typing.Any, "return": typing.Any}
        for name, (annotation, _) in param_specs.items():
            annotations[name] = annotation
        func.__annotations__ = annotations

        return func


def register_tools(
    router: APIRouter,
    tools: list[type[Tool]],
    client_dependency: Any = None,
    formatter: Callable[[Any, str, str], Any] | None = None,
    prefix: str = "",
) -> ToolRegistry:
    """Convenience function to register multiple tools.

    Args:
        router: FastAPI router
        tools: List of Tool classes
        client_dependency: FastAPI Depends() for client injection
        formatter: Optional output formatter
        prefix: Optional path prefix

    Returns:
        ToolRegistry instance for further registration

    Example:
        router = APIRouter()
        register_tools(router, [GetIssue, CreateIssue], Depends(jira))
    """
    registry = ToolRegistry(router, formatter)
    registry.register_all(tools, client_dependency, prefix)
    return registry
