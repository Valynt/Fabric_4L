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


@pytest.fixture
def api_key():
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="product-test")
    repo = APIKeyRepository()
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="product-test", role="analyst"),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    return tenant_id, raw


ENDPOINTS = [
    ("/v1/value-drivers/map", {"context": "Increase revenue"}),
    ("/v1/value-models/generate", {"drivers": ["revenue"]}),
    ("/v1/value-models/validate", {"value_model": {}}),
    ("/v1/value-models/qa", {"value_model": {}, "question": "Is this realistic?"}),
    ("/v1/assumptions/score", {"assumption": "We will grow 10%"}),
    ("/v1/evidence/extract-value-signals", {"source_text": "Revenue increased 20%"}),
    ("/v1/cfo-narratives/generate", {"value_model": {}}),
    ("/v1/realization/compare", {}),
]


@pytest.mark.parametrize("path,payload", ENDPOINTS)
def test_product_endpoint_accepts_request(path, payload, api_key):
    tenant_id, raw = api_key
    with TestClient(app) as client:
        response = client.post(
            path,
            json=payload,
            headers={"X-API-Key": raw, "X-Tenant-ID": tenant_id},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["product_code"]
    assert body["job_id"].startswith("job_")


def test_product_endpoints_require_auth():
    with TestClient(app) as client:
        response = client.post("/v1/value-drivers/map", json={"context": "x"})
    assert response.status_code == 401


def test_product_endpoint_quota_exceeded(api_key, monkeypatch):
    tenant_id, raw = api_key
    monkeypatch.setenv("QUOTA_VALUE_DRIVERS", "0")
    with TestClient(app) as client:
        response = client.post(
            "/v1/value-drivers/map",
            json={"context": "Increase revenue"},
            headers={"X-API-Key": raw, "X-Tenant-ID": tenant_id},
        )
    assert response.status_code == 429
    body = response.json()
    assert (
        body.get("detail", {}).get("code") == "QUOTA_EXCEEDED"
        or body.get("error", {}).get("code") == "QUOTA_EXCEEDED"
    )
