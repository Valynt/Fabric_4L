from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.api_key_hash import generate_api_key
from app.main import app
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


@pytest.fixture
def api_key():
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="route-test")
    repo = APIKeyRepository()
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="route-test", role="analyst", permissions=["benchmarks:read"]),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    return tenant_id, raw


def test_api_key_request_resolves_tenant(api_key):
    tenant_id, raw = api_key
    with TestClient(app) as client:
        response = client.get(
            "/v1/accounts",
            headers={"X-API-Key": raw, "X-Tenant-ID": tenant_id},
        )
    # /v1/accounts still requires a JWT via the legacy route dependency, so the
    # route itself returns 401. The important auth-layer assertion is that the
    # governance middleware resolved the API key to the correct tenant.
    assert response.headers.get("X-Tenant-ID-Resolved") == tenant_id


def test_missing_api_key_is_rejected():
    with TestClient(app) as client:
        response = client.get("/v1/accounts")
    assert response.status_code == 401
