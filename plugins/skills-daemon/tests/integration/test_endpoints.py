"""Integration tests for core daemon endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_returns_ok(self, client: TestClient):
        """Health endpoint returns running status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "version" in data
        assert "plugins" in data

    def test_health_includes_plugin_health(self, client: TestClient, isolated_registry, simple_plugin):
        """Health endpoint includes plugin health."""
        isolated_registry.register(simple_plugin)

        response = client.get("/health")
        data = response.json()

        assert "plugin_health" in data


class TestPluginsEndpoint:
    """Test /plugins endpoint."""

    def test_plugins_returns_list(self, client: TestClient):
        """Plugins endpoint returns plugin list."""
        response = client.get("/plugins")

        assert response.status_code == 200
        data = response.json()
        assert "plugins" in data
        assert isinstance(data["plugins"], list)


class TestShutdownEndpoint:
    """Test /shutdown endpoint."""

    def test_shutdown_returns_success(self, client: TestClient):
        """Shutdown endpoint initiates shutdown."""
        response = client.post("/shutdown")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestErrorHandling:
    """Test global error handling."""

    def test_404_for_unknown_route(self, client: TestClient):
        """Returns 404 for unknown routes."""
        response = client.get("/nonexistent/route")

        assert response.status_code == 404
