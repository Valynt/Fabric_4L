from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

from .conftest import mint_token


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


def _admin_headers(tenant_id: str):
    token = mint_token(tenant_id=tenant_id, extra_claims={"roles": ["tenant_admin"]})
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def test_create_api_key_returns_raw_key_once():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        response = client.post(
            "/v1/auth/api-keys",
            json={"name": "test-key", "role": "analyst", "permissions": ["benchmarks:read"]},
            headers=_admin_headers(tenant_id),
        )
    assert response.status_code == 201
    body = response.json()
    assert body["api_key"].startswith("vf_")
    assert body["tenant_id"] == tenant_id


def test_list_api_keys():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        client.post(
            "/v1/auth/api-keys",
            json={"name": "list-me"},
            headers=_admin_headers(tenant_id),
        )
        response = client.get("/v1/auth/api-keys", headers=_admin_headers(tenant_id))
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
