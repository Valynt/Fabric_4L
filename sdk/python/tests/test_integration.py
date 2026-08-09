"""Integration tests for the Value Fabric SDK.

Tests verify the SDK works against real (or mocked) API endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
import respx
from httpx import Response

from valuefabric import ValueFabricClient
from valuefabric.__version__ import __version__


def now() -> str:
    """Return current ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


class TestSDKVersion:
    """Test version information is accessible."""

    def test_version_is_string(self):
        """Version should be a string in semver format."""
        assert isinstance(__version__, str)
        parts = __version__.split(".")
        assert len(parts) == 3, f"Expected semver (x.y.z), got: {__version__}"
        assert all(p.isdigit() for p in parts), f"Version parts should be numeric: {__version__}"

    def test_version_matches_package(self):
        """Version should be importable from package root."""
        from valuefabric import __version__ as package_version

        assert package_version == __version__


class TestClientAuthentication:
    """Test client authentication methods."""

    @respx.mock
    def test_api_key_auth_header(self):
        """API key should be sent in X-API-Key header."""
        route = respx.get("https://api.example.com/health").mock(
            return_value=Response(
                200,
                json={
                    "status": "ok",
                    "service": "layer4-agents",
                    "version": "1.0.0",
                    "timestamp": now(),
                    "executor_ready": True,
                    "uptime_seconds": 3600,
                    "dependencies": [],
                    "metrics": {},
                }
            )
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-api-key-123",
        )

        response = client.health()

        assert route.called
        request = route.calls[0].request
        # httpx normalizes headers to lowercase internally
        assert request.headers.get("x-api-key") == "test-api-key-123"
        assert response.status == "ok"

    @respx.mock
    def test_jwt_auth_header(self):
        """JWT token should be sent in Authorization header."""
        route = respx.get("https://api.example.com/health").mock(
            return_value=Response(
                200,
                json={
                    "status": "ok",
                    "service": "layer4-agents",
                    "version": "1.0.0",
                    "timestamp": now(),
                    "executor_ready": True,
                    "uptime_seconds": 3600,
                    "dependencies": [],
                    "metrics": {},
                }
            )
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            jwt_token="test-jwt-token",
        )

        client.health()

        assert route.called
        request = route.calls[0].request
        # httpx normalizes headers to lowercase internally
        assert request.headers.get("authorization") == "Bearer test-jwt-token"


class TestClientEndpoints:
    """Test client endpoint methods."""

    @respx.mock
    def test_list_tenants(self):
        """Should fetch and parse tenant list."""
        ts = now()
        tenants_data = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "Tenant One",
                "slug": "tenant-one",
                "status": "active",
                "settings": {},
                "created_at": ts,
                "updated_at": ts,
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "name": "Tenant Two",
                "slug": "tenant-two",
                "status": "active",
                "settings": {},
                "created_at": ts,
                "updated_at": ts,
            },
        ]
        route = respx.get("https://api.example.com/v1/tenants").mock(
            return_value=Response(200, json=tenants_data)
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        tenants = list(client.list_tenants())

        assert route.called
        assert len(tenants) == 2
        assert str(tenants[0].id) == "550e8400-e29b-41d4-a716-446655440001"
        assert tenants[0].name == "Tenant One"

    @respx.mock
    def test_health(self):
        """Should fetch health status."""
        route = respx.get("https://api.example.com/health").mock(
            return_value=Response(
                200,
                json={
                    "status": "healthy",
                    "service": "layer4-agents",
                    "version": "2.1.0",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "executor_ready": True,
                    "uptime_seconds": 3600,
                    "dependencies": [],
                    "metrics": {},
                },
            )
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        health = client.health()

        assert route.called
        assert health.status == "healthy"
        assert health.version == "2.1.0"


class TestClientAsync:
    """Test async client methods."""

    @respx.mock
    async def test_async_list_tenants(self):
        """Should support async tenant listing."""
        ts = now()
        tenants_data = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "Tenant One",
                "slug": "tenant-one",
                "status": "active",
                "settings": {},
                "created_at": ts,
                "updated_at": ts,
            },
        ]
        route = respx.get("https://api.example.com/v1/tenants").mock(
            return_value=Response(200, json=tenants_data)
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        tenants = await client.alist_tenants()

        assert route.called
        assert len(tenants) == 1
        assert str(tenants[0].id) == "550e8400-e29b-41d4-a716-446655440001"

    @respx.mock
    async def test_async_health(self):
        """Should support async health check."""
        route = respx.get("https://api.example.com/health").mock(
            return_value=Response(
                200,
                json={
                    "status": "ok",
                    "service": "layer4-agents",
                    "version": "1.0.0",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "executor_ready": True,
                    "uptime_seconds": 3600,
                    "dependencies": [],
                    "metrics": {},
                }
            )
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        health = await client.ahealth()

        assert route.called
        assert health.status == "ok"


class TestErrorHandling:
    """Test SDK error handling."""

    @respx.mock
    def test_http_error_raises_exception(self):
        """HTTP errors should raise exceptions."""
        respx.get("https://api.example.com/health").mock(
            return_value=Response(500, json={"error": "Internal Server Error"})
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )

        # HTTP errors raise HTTPStatusError
        with pytest.raises(Exception):
            client.health()

    @respx.mock
    def test_401_error_raises_exception(self):
        """401 errors should raise exceptions."""
        respx.get("https://api.example.com/health").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )

        # 401 raises HTTPStatusError
        with pytest.raises(Exception):
            client.health()


class TestClientContextManager:
    """Test async context manager support."""

    @respx.mock
    async def test_async_context_manager(self):
        """Should support async context manager pattern."""
        route = respx.get("https://api.example.com/health").mock(
            return_value=Response(
                200,
                json={
                    "status": "ok",
                    "service": "layer4-agents",
                    "version": "1.0.0",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "executor_ready": True,
                    "uptime_seconds": 3600,
                    "dependencies": [],
                    "metrics": {},
                }
            )
        )

        async with ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        ) as client:
            health = await client.ahealth()
            assert health.status == "ok"

        assert route.called


class TestWorkflowExecution:
    """Test workflow execution endpoints."""

    @respx.mock
    def test_execute_workflow(self):
        """Should execute workflow and return dict."""
        route = respx.post("https://api.example.com/v1/workflows").mock(
            return_value=Response(
                200,
                json={
                    "workflow_instance_id": "wf-123",
                    "status": "started",
                },
            )
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        result = client.execute_workflow(
            workflow_type="roi_calculator",
            tenant_id="tenant-1",
            user_id="user-1",
        )

        assert route.called
        assert result["workflow_instance_id"] == "wf-123"
        assert result["status"] == "started"

    @respx.mock
    def test_get_workflow_status(self):
        """Should fetch workflow status."""
        route = respx.get("https://api.example.com/v1/workflows/wf-123").mock(
            return_value=Response(
                200,
                json={
                    "workflow_instance_id": "wf-123",
                    "workflow_type": "roi_calculator",
                    "status": "completed",
                    "current_state": None,
                    "current_node": None,
                    "progress_percentage": 100.0,
                    "started_at": now(),
                    "completed_at": now(),
                    "error_count": 0,
                    "has_output": True,
                    "results": {"roi": 2.5},
                    "tenant_id": "tenant-1",
                    "user_id": "user-1",
                    "priority": None,
                    "scheduler_status": None,
                },
            )
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        status = client.get_workflow("wf-123")

        assert route.called
        assert status.workflow_instance_id == "wf-123"
        assert status.status == "completed"


class TestModelRegistry:
    """Test model registry endpoints."""

    @respx.mock
    def test_list_model_versions(self):
        """Should list model versions."""
        models_data = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440010",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                "provider": "openai",
                "model_name": "gpt-4",
                "model_version": "0613",
                "stage": "production",
                "promoted_by": None,
                "eval_score": None,
                "eval_run_id": None,
                "config": {},
                "created_at": now(),
            },
        ]
        route = respx.get("https://api.example.com/v1/models").mock(
            return_value=Response(200, json=models_data)
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        models = list(client.list_models())

        assert route.called
        assert len(models) == 1
        assert models[0].provider == "openai"


class TestFeatureFlags:
    """Test feature flag endpoints."""

    @respx.mock
    def test_list_feature_flags(self):
        """Should list feature flags."""
        ts = now()
        flags_data = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440020",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                "flag_key": "new-ui",
                "enabled": True,
                "rollout_percentage": 50,
                "description": "New UI rollout",
                "metadata": {},
                "created_at": ts,
                "updated_at": ts,
                "updated_by": None,
            },
        ]
        route = respx.get("https://api.example.com/v1/feature-flags?limit=100&offset=0").mock(
            return_value=Response(200, json=flags_data)
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        flags = list(client.list_feature_flags())

        assert route.called
        assert len(flags) == 1
        assert flags[0].flag_key == "new-ui"
        assert flags[0].enabled is True

    @respx.mock
    def test_set_feature_flag(self):
        """Should set/update feature flag."""
        ts = now()
        route = respx.put("https://api.example.com/v1/feature-flags/new-ui").mock(
            return_value=Response(
                200,
                json={
                    "id": "550e8400-e29b-41d4-a716-446655440020",
                    "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                    "flag_key": "new-ui",
                    "enabled": True,
                    "rollout_percentage": 100,
                    "description": "New UI rollout",
                    "metadata": {},
                    "created_at": ts,
                    "updated_at": ts,
                    "updated_by": None,
                },
            )
        )

        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        flag = client.set_feature_flag("new-ui", enabled=True)

        assert route.called
        assert flag.flag_key == "new-ui"
        assert flag.enabled is True
