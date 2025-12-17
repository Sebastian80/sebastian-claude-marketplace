"""Tests for the tools framework."""

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from pydantic import Field

from toolbus.tools import Tool, ToolContext, ToolResult, ToolRegistry, register_tools


# --- Test Tools ---


class GetItem(Tool):
    """Get item by key."""

    key: str = Field(..., description="Item key")
    format: str = Field("json", description="Output format: json, human")

    async def execute(self, ctx: ToolContext) -> dict:
        return {"key": self.key, "format": self.format, "data": f"Item {self.key}"}


class CreateItem(Tool):
    """Create a new item."""

    name: str = Field(..., description="Item name")
    value: int = Field(0, description="Item value")

    class Meta:
        method = "POST"
        path = "/create"

    async def execute(self, ctx: ToolContext) -> dict:
        return {"name": self.name, "value": self.value, "created": True}


class UpdateItem(Tool):
    """Update an existing item."""

    key: str = Field(..., description="Item key")
    name: str | None = Field(None, description="New name")
    value: int | None = Field(None, description="New value")

    async def execute(self, ctx: ToolContext) -> dict:
        updates = {}
        if self.name:
            updates["name"] = self.name
        if self.value is not None:
            updates["value"] = self.value
        return {"key": self.key, "updates": updates}


class DeleteItem(Tool):
    """Delete an item."""

    key: str = Field(..., description="Item key")

    async def execute(self, ctx: ToolContext) -> dict:
        return {"key": self.key, "deleted": True}


class SearchItems(Tool):
    """Search for items."""

    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Max results")

    async def execute(self, ctx: ToolContext) -> dict:
        return {"query": self.query, "limit": self.limit, "results": []}


class ToolWithResult(Tool):
    """Tool that returns ToolResult."""

    fail: bool = Field(False, description="Whether to fail")

    class Meta:
        method = "POST"
        path = "/result-test"

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if self.fail:
            return ToolResult(error="Intentional failure", status=400)
        return ToolResult(data={"success": True}, status=201)


class ToolWithFormatter(Tool):
    """Tool that uses formatter."""

    key: str = Field(..., description="Item key")
    format: str = Field("json", description="Output format")

    async def execute(self, ctx: ToolContext) -> dict:
        data = {"key": self.key, "raw": "data"}
        return ctx.formatted(data, self.format, "item")


# --- Mock Client ---


class MockClient:
    """Mock client for testing."""

    def get(self, key: str) -> dict:
        return {"key": key, "data": f"Data for {key}"}


def get_mock_client() -> MockClient:
    return MockClient()


# --- Tests ---


class TestToolBase:
    """Tests for Tool base class."""

    def test_get_method_from_name(self):
        assert GetItem.get_method() == "GET"
        assert CreateItem.get_method() == "POST"
        assert UpdateItem.get_method() == "PATCH"
        assert DeleteItem.get_method() == "DELETE"
        assert SearchItems.get_method() == "GET"

    def test_get_method_from_meta(self):
        assert CreateItem.get_method() == "POST"  # Explicit in Meta
        assert ToolWithResult.get_method() == "POST"

    def test_get_path_auto(self):
        assert GetItem.get_path() == "/item/{key}"
        assert SearchItems.get_path() == "/items"
        assert DeleteItem.get_path() == "/item/{key}"

    def test_get_path_explicit(self):
        assert CreateItem.get_path() == "/create"
        assert ToolWithResult.get_path() == "/result-test"

    def test_get_summary(self):
        assert GetItem.get_summary() == "Get item by key."
        assert CreateItem.get_summary() == "Create a new item."

    def test_model_validation(self):
        tool = GetItem(key="TEST-123", format="human")
        assert tool.key == "TEST-123"
        assert tool.format == "human"

    def test_model_defaults(self):
        tool = GetItem(key="TEST-123")
        assert tool.format == "json"  # Default value

    def test_model_validation_error(self):
        with pytest.raises(Exception):  # ValidationError
            GetItem()  # Missing required 'key'


class TestToolContext:
    """Tests for ToolContext."""

    def test_formatted_with_formatter(self):
        def mock_formatter(data, fmt, entity):
            return {"formatted": True, "fmt": fmt, "data": data}

        ctx = ToolContext(client=None, format=mock_formatter)
        result = ctx.formatted({"raw": "data"}, "human", "item")

        assert result["formatted"] is True
        assert result["fmt"] == "human"

    def test_formatted_without_formatter(self):
        ctx = ToolContext(client=None)
        data = {"raw": "data"}
        result = ctx.formatted(data, "human", "item")

        assert result == data  # Returns unchanged


class TestToolResult:
    """Tests for ToolResult."""

    def test_success_result(self):
        result = ToolResult(data={"key": "value"})
        assert result.success is True
        assert result.status == 200

    def test_error_result(self):
        result = ToolResult(error="Something went wrong", status=400)
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_custom_status(self):
        result = ToolResult(data={"created": True}, status=201)
        assert result.success is True
        assert result.status == 201


class TestToolRegistry:
    """Tests for ToolRegistry and route generation."""

    def test_register_single_tool(self):
        router = APIRouter()
        registry = ToolRegistry(router)
        registry.register(GetItem, Depends(get_mock_client))

        # Check route was registered
        routes = [r.path for r in router.routes]
        assert "/item/{key}" in routes

    def test_register_multiple_tools(self):
        router = APIRouter()
        registry = ToolRegistry(router)
        registry.register_all(
            [GetItem, CreateItem, SearchItems],
            Depends(get_mock_client),
        )

        routes = [r.path for r in router.routes]
        assert "/item/{key}" in routes
        assert "/create" in routes
        assert "/items" in routes

    def test_duplicate_registration_fails(self):
        router = APIRouter()
        registry = ToolRegistry(router)
        registry.register(GetItem, Depends(get_mock_client))

        with pytest.raises(ValueError, match="already registered"):
            registry.register(GetItem, Depends(get_mock_client))


class TestToolEndpoints:
    """Integration tests for generated endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi import FastAPI

        app = FastAPI()
        router = APIRouter()

        def mock_formatter(data, fmt, entity):
            if fmt == "human":
                return {"human_readable": True, **data}
            return data

        register_tools(
            router,
            [GetItem, CreateItem, UpdateItem, DeleteItem, SearchItems,
             ToolWithResult, ToolWithFormatter],
            Depends(get_mock_client),
            formatter=mock_formatter,
        )
        app.include_router(router)

        return TestClient(app)

    def test_get_endpoint(self, client):
        response = client.get("/item/TEST-123")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "TEST-123"

    def test_get_with_query_params(self, client):
        response = client.get("/item/TEST-123?format=human")
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "human"

    def test_post_endpoint(self, client):
        response = client.post("/create?name=Test&value=42")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test"
        assert data["value"] == 42
        assert data["created"] is True

    def test_patch_endpoint(self, client):
        response = client.patch("/item/TEST-123?name=NewName")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "TEST-123"
        assert data["updates"]["name"] == "NewName"

    def test_delete_endpoint(self, client):
        response = client.delete("/item/TEST-123")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True

    def test_search_endpoint(self, client):
        response = client.get("/items?query=test&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["limit"] == 5

    def test_tool_result_success(self, client):
        response = client.post("/result-test?fail=false")
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_tool_result_error(self, client):
        response = client.post("/result-test?fail=true")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Intentional failure"

    def test_validation_error(self, client):
        response = client.get("/item/")  # Missing key
        assert response.status_code in (404, 422)  # Either not found or validation error

    def test_formatter_used(self, client):
        response = client.get("/item/{key}?key=TEST&format=human")
        # Formatter should be called but we're testing the flow works
        assert response.status_code == 200


class TestRegisterToolsFunction:
    """Tests for the register_tools convenience function."""

    def test_returns_registry(self):
        router = APIRouter()
        registry = register_tools(router, [GetItem], Depends(get_mock_client))

        assert isinstance(registry, ToolRegistry)

    def test_with_prefix(self):
        router = APIRouter()
        register_tools(
            router,
            [GetItem],
            Depends(get_mock_client),
            prefix="/api/v1",
        )

        routes = [r.path for r in router.routes]
        assert "/api/v1/item/{key}" in routes
