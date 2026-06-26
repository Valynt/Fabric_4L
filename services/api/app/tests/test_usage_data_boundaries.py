from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.clients.billing_publisher import BillingEventPublisher
from app.core.api_key_hash import generate_api_key
from app.main import app
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


@pytest.fixture(autouse=True)
def _noop_billing_publisher(monkeypatch):
    async def _noop_publish(self, event):
        return {"forwarded": True}

    monkeypatch.setattr(BillingEventPublisher, "publish", _noop_publish)


def _create_key(tenant_id: str, name: str):
    raw, key_id, prefix = generate_api_key(name=name)
    repo = APIKeyRepository()
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name=name, role="analyst"),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    return raw


def test_usage_events_isolated_by_tenant():
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    key_a = _create_key(tenant_a, "usage-a")
    key_b = _create_key(tenant_b, "usage-b")

    with TestClient(app) as client:
        # Generate usage for tenant A
        response = client.post(
            "/v1/value-drivers/map",
            json={"context": "A"},
            headers={"X-API-Key": key_a, "X-Tenant-ID": tenant_a},
        )
        assert response.status_code == 200

        # Generate usage for tenant B
        response = client.post(
            "/v1/value-drivers/map",
            json={"context": "B"},
            headers={"X-API-Key": key_b, "X-Tenant-ID": tenant_b},
        )
        assert response.status_code == 200

        # Tenant A sees only one event
        response = client.get(
            "/v1/usage",
            headers={"X-API-Key": key_a, "X-Tenant-ID": tenant_a},
        )
        assert response.status_code == 200
        body_a = response.json()
        assert len(body_a["events"]) == 1
        assert body_a["events"][0]["tenant_id"] == tenant_a

        # Tenant B sees only one event
        response = client.get(
            "/v1/usage",
            headers={"X-API-Key": key_b, "X-Tenant-ID": tenant_b},
        )
        assert response.status_code == 200
        body_b = response.json()
        assert len(body_b["events"]) == 1
        assert body_b["events"][0]["tenant_id"] == tenant_b


def test_usage_quota_isolated_by_tenant():
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    key_a = _create_key(tenant_a, "quota-a")
    key_b = _create_key(tenant_b, "quota-b")

    with TestClient(app) as client:
        client.post(
            "/v1/value-drivers/map",
            json={"context": "A"},
            headers={"X-API-Key": key_a, "X-Tenant-ID": tenant_a},
        )

        quotas_a = client.get(
            "/v1/usage/quotas",
            headers={"X-API-Key": key_a, "X-Tenant-ID": tenant_a},
        ).json()["quotas"]
        quotas_b = client.get(
            "/v1/usage/quotas",
            headers={"X-API-Key": key_b, "X-Tenant-ID": tenant_b},
        ).json()["quotas"]

        assert quotas_a["value_drivers"]["used"] == 1
        assert quotas_b["value_drivers"]["used"] == 0
