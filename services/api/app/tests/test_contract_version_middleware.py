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
    raw, key_id, prefix = generate_api_key(name="contract-test")
    repo = APIKeyRepository()
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="contract-test", role="analyst"),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    return tenant_id, raw


def test_missing_contract_version_succeeds(api_key):
    tenant_id, raw = api_key
    with TestClient(app) as client:
        response = client.get(
            "/v1/usage/quotas",
            headers={"X-API-Key": raw, "X-Tenant-ID": tenant_id},
        )
    assert response.status_code == 200
    assert response.headers["X-API-Contract-Version"] == "v1"
    assert response.headers["X-SLA-Enforced"] == "true"


def test_supported_contract_version_succeeds(api_key):
    tenant_id, raw = api_key
    with TestClient(app) as client:
        response = client.get(
            "/v1/usage/quotas",
            headers={
                "X-API-Key": raw,
                "X-Tenant-ID": tenant_id,
                "X-API-Contract-Version": "v1",
            },
        )
    assert response.status_code == 200
    assert response.headers["X-API-Contract-Version"] == "v1"
    assert response.headers["X-SLA-Enforced"] == "true"


def test_unsupported_contract_version_rejected(api_key):
    tenant_id, raw = api_key
    with TestClient(app) as client:
        response = client.get(
            "/v1/usage/quotas",
            headers={
                "X-API-Key": raw,
                "X-Tenant-ID": tenant_id,
                "X-API-Contract-Version": "v0",
            },
        )
    assert response.status_code == 412
    body = response.json()
    assert body["detail"]["code"] == "UNSUPPORTED_CONTRACT_VERSION"
