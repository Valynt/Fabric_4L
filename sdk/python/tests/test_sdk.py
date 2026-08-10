"""SDK smoke tests for CI validation.

These tests verify the SDK can be imported and basic functionality works
without requiring a running backend.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from valuefabric import ValueFabricClient
from valuefabric.cli.main import app
from valuefabric.models import HealthResponse

runner = CliRunner()


class TestSDKImports:
    """Verify SDK modules can be imported."""

    def test_import_client(self):
        """Main client can be imported."""
        from valuefabric import ValueFabricClient
        assert ValueFabricClient is not None

    def test_import_models(self):
        """Models can be imported."""
        from valuefabric.models import HealthResponse, Tenant, User
        assert HealthResponse is not None
        assert Tenant is not None
        assert User is not None

    def test_import_cli(self):
        """CLI can be imported."""
        from valuefabric.cli.main import app
        assert app is not None

    def test_import_generated_clients(self):
        """Generated clients can be imported."""
        from valuefabric.generated.l3_client import L3Client
        from valuefabric.generated.l4_client import L4Client
        assert L3Client is not None
        assert L4Client is not None


class TestCLIBasic:
    """Verify CLI basic commands work."""

    def test_version_flag(self):
        """CLI shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "vf" in result.output
        assert "version" in result.output

    def test_help_command(self):
        """CLI shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Value Fabric SDK CLI" in result.output

    def test_health_help(self):
        """Health command has help."""
        result = runner.invoke(app, ["health", "--help"])
        assert result.exit_code == 0
        assert "Check API health" in result.output


class TestClientInitialization:
    """Verify client can be initialized."""

    def test_client_init_with_url(self):
        """Client initializes with base URL and API key."""
        client = ValueFabricClient(base_url="http://localhost:8004", api_key="test-key")
        assert client is not None
        assert client.base_url == "http://localhost:8004"

    def test_client_init_with_api_key(self):
        """Client initializes with API key."""
        client = ValueFabricClient(
            base_url="http://localhost:8004",
            api_key="test-api-key"
        )
        assert client is not None
        # Verify auth handler is set (adds X-API-Key header at request time)
        assert client._sync_client._auth is not None


class TestModels:
    """Verify Pydantic models work."""

    def test_health_response_model(self):
        """HealthResponse model can be created."""
        health = HealthResponse(
            status="healthy",
            service="layer4-agents",
            version="1.0.0",
            timestamp="2024-01-01T00:00:00Z",
            executor_ready=True,
            uptime_seconds=3600.0
        )
        assert health.status == "healthy"
        assert health.version == "1.0.0"

    def test_model_serialization(self):
        """Models can be serialized to dict."""
        health = HealthResponse(
            status="healthy",
            service="layer4-agents",
            version="1.0.0",
            timestamp="2024-01-01T00:00:00Z",
            executor_ready=True,
            uptime_seconds=3600.0
        )
        data = health.model_dump(mode="json")
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"


class TestGeneratedClients:
    """Verify generated clients can be instantiated."""

    def test_l3_client_init(self):
        """L3 client can be initialized."""
        from valuefabric.generated.l3_client import L3Client
        client = L3Client(base_url="http://localhost:8003")
        assert client is not None

    def test_l4_client_init(self):
        """L4 client can be initialized."""
        from valuefabric.generated.l4_client import L4Client
        client = L4Client(base_url="http://localhost:8004")
        assert client is not None


@pytest.mark.skip(reason="Requires running backend")
class TestSDKIntegration:
    """Integration tests requiring backend (skipped in CI smoke tests)."""

    def test_health_command_live(self):
        """Health command against real API."""
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0

    def test_client_health_live(self):
        """Client health check against real API."""
        client = ValueFabricClient(base_url="http://localhost:8004")
        health = client.health()
        assert health.status in ["healthy", "degraded"]
