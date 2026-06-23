from __future__ import annotations

"""Route-level tests for CRM webhook tenant resolution hardening."""


import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.integration

with patch.dict(
    "sys.modules",
    {
        "langgraph.checkpoint.postgres.aio": MagicMock(),
        "langgraph.checkpoint.postgres": MagicMock(),
        "langgraph.checkpoint": MagicMock(),
        "psycopg": MagicMock(),
    },
):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from value_fabric.shared.error_handling import register_exception_handlers

    from layer4_agents.api.routes import crm_webhooks as crm_webhooks_module
    from layer4_agents.models.account import CRMProvider
    from layer4_agents.models.integration import Integration, IntegrationStatus


@pytest.fixture(autouse=True)
def clear_env():
    """Reset webhook-related environment flags between tests."""
    original = {
        "ENVIRONMENT": os.environ.get("ENVIRONMENT"),
        "APP_ENV": os.environ.get("APP_ENV"),
        "CRM_WEBHOOKS_ALLOW_DEV_RELAXED_TENANT_RESOLUTION": os.environ.get(
            "CRM_WEBHOOKS_ALLOW_DEV_RELAXED_TENANT_RESOLUTION"
        ),
    }
    os.environ["ENVIRONMENT"] = "development"
    os.environ.pop("APP_ENV", None)
    os.environ.pop("CRM_WEBHOOKS_ALLOW_DEV_RELAXED_TENANT_RESOLUTION", None)
    yield
    for key, value in original.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def mock_db():
    """Create an async session double with query hooks used by the route."""
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def _result_with_scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_client(mock_db):
    app = FastAPI()
    register_exception_handlers(app)

    async def _override():
        yield mock_db

    app.dependency_overrides[crm_webhooks_module.get_db_from_context] = _override
    app.include_router(crm_webhooks_module.router, prefix="/v1")
    return TestClient(app)


def _make_integration(
    *,
    provider: CRMProvider = CRMProvider.SALESFORCE,
    tenant_id: str = "tenant-test",
    enabled: bool = True,
):
    integration = MagicMock(spec=Integration)
    integration.enabled = enabled
    integration.tenant_id = tenant_id
    integration.provider = provider
    integration.refresh_token_encrypted = None
    integration.instance_url = "https://test.crm.example"
    integration.sync_status = IntegrationStatus.IDLE
    integration.credentials_encrypted = b"enc:{}"
    integration.encryption_key_id = "test-key"
    integration.salesforce_org_id = None
    return integration


class TestSalesforceWebhookTenantIsolation:
    def test_missing_tenant_id_is_rejected(self, mock_db):
        client = _make_client(mock_db)

        response = client.post("/v1/webhooks/crm/salesforce", json={})

        assert response.status_code == 422
        assert "tenant_id" in response.json()["error"]["message"]

    def test_unknown_tenant_integration_is_rejected(self, mock_db):
        client = _make_client(mock_db)
        mock_db.execute.return_value = _result_with_scalar(None)

        response = client.post(
            "/v1/webhooks/crm/salesforce?tenant_id=unknown-tenant",
            headers={"X-Webhook-Token": "ignored"},
            json={},
        )

        assert response.status_code == 404
        assert "No Salesforce integration configured" in response.json()["error"]["message"]

    def test_token_mismatch_is_rejected(self, mock_db):
        client = _make_client(mock_db)
        mock_db.execute.return_value = _result_with_scalar(_make_integration())

        with patch.object(
            crm_webhooks_module,
            "_decrypt_integration_credentials",
            AsyncMock(return_value={"webhook_token": "expected-token"}),
        ):
            response = client.post(
                "/v1/webhooks/crm/salesforce?tenant_id=tenant-test",
                headers={"X-Webhook-Token": "wrong-token"},
                json={},
            )

        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Invalid webhook credentials"

    def test_valid_tenant_and_auth_are_scoped_to_resolved_tenant(self, mock_db):
        client = _make_client(mock_db)
        mock_db.execute.return_value = _result_with_scalar(_make_integration())

        payload = {
            "data": {
                "payload": {
                    "RecordId": "001TEST123456789",
                    "ChangeEventHeader": {
                        "entityName": "Account",
                        "recordIds": ["001TEST123456789"],
                        "changeType": "UPDATE",
                    },
                }
            }
        }

        with patch.object(
            crm_webhooks_module,
            "_decrypt_integration_credentials",
            AsyncMock(return_value={"webhook_token": "expected-token"}),
        ), patch.object(crm_webhooks_module, "CRMSyncService") as mock_sync_class:
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            mock_sync.sync_provider.return_value = {"synced": 1, "updated": 0, "failed": 0}

            response = client.post(
                "/v1/webhooks/crm/salesforce?tenant_id=tenant-test",
                headers={"X-Webhook-Token": "expected-token"},
                json=payload,
            )

        assert response.status_code == 202
        call_kwargs = mock_sync.sync_provider.call_args.kwargs
        assert call_kwargs["tenant_id"] == "tenant-test"
        assert call_kwargs["account_ids"] == ["001TEST123456789"]


class TestHubSpotWebhookTenantIsolation:
    def test_missing_tenant_id_is_rejected(self, mock_db):
        client = _make_client(mock_db)

        response = client.post("/v1/webhooks/crm/hubspot", json=[])

        assert response.status_code == 422
        assert "tenant_id" in response.json()["error"]["message"]
