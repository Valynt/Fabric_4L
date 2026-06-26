from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

from .conftest import mint_token


def _headers(tenant_id: str):
    token = mint_token(tenant_id=tenant_id)
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def test_get_usage_returns_events():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        response = client.get("/v1/usage", headers=_headers(tenant_id))
    assert response.status_code == 200
    assert response.json()["tenant_id"] == tenant_id


def test_get_quotas_stub():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        response = client.get("/v1/usage/quotas", headers=_headers(tenant_id))
    assert response.status_code == 200
    assert "benchmarks" in response.json()["quotas"]
