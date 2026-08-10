"""Tests for ``ValueFabricClient`` using mocked HTTP transports."""

from __future__ import annotations

import httpx
import pytest

from valuefabric.client import ValueFabricClient
from valuefabric.models import (
    APIKey,
    APIKeyCreateResult,
    FeatureFlag,
    HealthResponse,
    ModelVersion,
    Tenant,
    User,
    Workflow,
    WorkflowTypeInfo,
)


def _mock_transport(responses: dict) -> httpx.MockTransport:
    """Build a mock transport that maps (method, path) -> JSON response."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        status_code, payload = responses.get(key, (404, {"detail": "not found"}))
        return httpx.Response(
            status_code,
            json=payload,
            headers={"content-type": "application/json"},
        )

    return httpx.MockTransport(handler)


@pytest.fixture
def mock_client():
    transport = _mock_transport({
        ("GET", "/v1/tenants"): (200, [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "name": "Acme",
                "slug": "acme",
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        ]),
        ("GET", "/v1/tenants/11111111-1111-1111-1111-111111111111"): (200, {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Acme",
            "slug": "acme",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }),
        ("GET", "/v1/users"): (200, [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "tenant_id": "11111111-1111-1111-1111-111111111111",
                "email": "alice@example.com",
                "role": "analyst",
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        ]),
        ("POST", "/v1/users/invite"): (201, {
            "id": "33333333-3333-3333-3333-333333333333",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "email": "bob@example.com",
            "role": "analyst",
            "status": "invited",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }),
        ("GET", "/v1/api-keys"): (200, [
            {
                "key_id": "vf_abc",
                "tenant_id": "11111111-1111-1111-1111-111111111111",
                "name": "test-key",
                "prefix": "vf_ab",
                "role": "analyst",
                "permissions": [],
                "enabled": True,
                "created_at": "2024-01-01T00:00:00Z",
            }
        ]),
        ("POST", "/v1/api-keys"): (201, {
            "key_id": "vf_def",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "name": "new-key",
            "api_key": "vf_def_secret",
            "prefix": "vf_de",
            "role": "analyst",
            "permissions": [],
            "created_at": "2024-01-01T00:00:00Z",
        }),
        ("GET", "/v1/workflows/types"): (200, {
            "workflows": [
                {
                    "type": "roi_calculator",
                    "name": "ROI Calculator",
                    "description": "Calculate ROI",
                }
            ]
        }),
        ("GET", "/v1/workflows/active"): (200, [
            {
                "workflow_instance_id": "wf-1",
                "workflow_type": "roi_calculator",
                "status": "running",
                "progress_percentage": 50.0,
            }
        ]),
        ("POST", "/v1/workflows"): (201, {
            "workflow_instance_id": "wf-2",
            "status": "scheduled",
            "estimated_duration_seconds": 300,
        }),
        ("GET", "/v1/workflows/wf-1"): (200, {
            "workflow_instance_id": "wf-1",
            "workflow_type": "roi_calculator",
            "status": "running",
            "progress_percentage": 50.0,
        }),
        ("GET", "/v1/models"): (200, [
            {
                "id": "44444444-4444-4444-4444-444444444444",
                "tenant_id": "11111111-1111-1111-1111-111111111111",
                "provider": "openai",
                "model_name": "gpt-4",
                "model_version": "1.0",
                "stage": "dev",
                "config": {},
                "created_at": "2024-01-01T00:00:00Z",
            }
        ]),
        ("POST", "/v1/models/44444444-4444-4444-4444-444444444444/promote"): (200, {
            "id": "44444444-4444-4444-4444-444444444444",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "provider": "openai",
            "model_name": "gpt-4",
            "model_version": "1.0",
            "stage": "staging",
            "config": {},
            "created_at": "2024-01-01T00:00:00Z",
        }),
        ("GET", "/v1/feature-flags"): (200, [
            {
                "id": "55555555-5555-5555-5555-555555555555",
                "flag_key": "new_ui",
                "enabled": True,
                "rollout_percentage": 100,
                "metadata": {},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        ]),
        ("PUT", "/v1/feature-flags/new_ui"): (200, {
            "id": "55555555-5555-5555-5555-555555555555",
            "flag_key": "new_ui",
            "enabled": False,
            "rollout_percentage": 0,
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }),
        ("GET", "/health"): (200, {
            "status": "healthy",
            "service": "layer4-agents",
            "version": "0.2.0",
            "timestamp": "2024-01-01T00:00:00Z",
            "executor_ready": True,
            "uptime_seconds": 123.0,
            "dependencies": [],
            "metrics": {},
        }),
    })

    client = ValueFabricClient(
        base_url="https://api.example.com",
        api_key="test-api-key",
    )
    # Replace with mock transport for testing
    client._sync_client = httpx.Client(
        transport=transport,
        base_url="https://api.example.com",
    )
    client._async_client = httpx.AsyncClient(
        transport=transport,
        base_url="https://api.example.com",
    )
    yield client
    client.close()


class TestTenants:
    def test_list_tenants(self, mock_client):
        tenants = mock_client.list_tenants()
        assert len(tenants) == 1
        assert tenants[0].name == "Acme"
        assert isinstance(tenants[0], Tenant)

    def test_get_tenant(self, mock_client):
        tenant = mock_client.get_tenant("11111111-1111-1111-1111-111111111111")
        assert tenant.name == "Acme"
        assert isinstance(tenant, Tenant)


class TestUsers:
    def test_list_users(self, mock_client):
        users = mock_client.list_users()
        assert len(users) == 1
        assert users[0].email == "alice@example.com"
        assert isinstance(users[0], User)

    def test_invite_user(self, mock_client):
        user = mock_client.invite_user("bob@example.com", "analyst")
        assert user.email == "bob@example.com"
        assert isinstance(user, User)


class TestApiKeys:
    def test_list_api_keys(self, mock_client):
        keys = mock_client.list_api_keys()
        assert len(keys) == 1
        assert keys[0].name == "test-key"
        assert isinstance(keys[0], APIKey)

    def test_create_api_key(self, mock_client):
        result = mock_client.create_api_key("new-key", "analyst")
        assert result.api_key == "vf_def_secret"
        assert isinstance(result, APIKeyCreateResult)


class TestWorkflows:
    def test_list_workflows(self, mock_client):
        workflows = mock_client.list_workflows()
        assert len(workflows) == 1
        assert workflows[0].type == "roi_calculator"
        assert isinstance(workflows[0], WorkflowTypeInfo)

    def test_list_active_workflows(self, mock_client):
        workflows = mock_client.list_active_workflows()
        assert len(workflows) == 1
        assert workflows[0].workflow_instance_id == "wf-1"
        assert isinstance(workflows[0], Workflow)

    def test_execute_workflow(self, mock_client):
        result = mock_client.execute_workflow(
            "roi_calculator", "tenant-1", "user-1"
        )
        assert result["workflow_instance_id"] == "wf-2"

    def test_get_workflow(self, mock_client):
        wf = mock_client.get_workflow("wf-1")
        assert wf.workflow_instance_id == "wf-1"
        assert isinstance(wf, Workflow)


class TestModels:
    def test_list_models(self, mock_client):
        models = mock_client.list_models()
        assert len(models) == 1
        assert models[0].model_name == "gpt-4"
        assert isinstance(models[0], ModelVersion)

    def test_promote_model(self, mock_client):
        model = mock_client.promote_model(
            "44444444-4444-4444-4444-444444444444", "staging"
        )
        assert model.stage == "staging"
        assert isinstance(model, ModelVersion)


class TestFeatureFlags:
    def test_list_feature_flags(self, mock_client):
        flags = mock_client.list_feature_flags()
        assert len(flags) == 1
        assert flags[0].flag_key == "new_ui"
        assert isinstance(flags[0], FeatureFlag)

    def test_set_feature_flag(self, mock_client):
        flag = mock_client.set_feature_flag("new_ui", False, rollout_percentage=0)
        assert flag.enabled is False
        assert isinstance(flag, FeatureFlag)


class TestHealth:
    def test_health(self, mock_client):
        health = mock_client.health()
        assert health.status == "healthy"
        assert isinstance(health, HealthResponse)


@pytest.mark.asyncio
class TestAsyncClient:
    async def test_alist_tenants(self):
        transport = _mock_transport({
            ("GET", "/v1/tenants"): (200, [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "name": "Acme",
                    "slug": "acme",
                    "status": "active",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            ]),
        })
        client = ValueFabricClient(
            base_url="https://api.example.com",
            api_key="test-api-key",
        )
        client._async_client = httpx.AsyncClient(
            transport=transport,
            base_url="https://api.example.com",
        )
        tenants = await client.alist_tenants()
        assert len(tenants) == 1
        assert tenants[0].name == "Acme"
        await client.aclose()
