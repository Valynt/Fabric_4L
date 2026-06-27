from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.clients.billing_publisher import BillingEventPublisher
from app.clients.layer4_client import Layer4Client
from app.core.api_key_hash import generate_api_key
from app.main import app
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


@pytest.fixture
def api_key(monkeypatch):
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="jobs-test")
    repo = APIKeyRepository()
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="jobs-test", role="analyst"),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )

    class _MockLayer4(Layer4Client):
        def __init__(self):
            pass

        async def get_workflow(self, tenant_id_param, job_id):
            if job_id == "missing":
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            return {"id": job_id, "status": "completed", "metadata": {"product_code": "value_drivers"}}

        async def get_workflow_result(self, tenant_id_param, job_id):
            return {"output": {"drivers": []}}

    monkeypatch.setattr("app.routers.jobs.Layer4Client", _MockLayer4)
    monkeypatch.setattr(BillingEventPublisher, "publish", lambda self, event: {"forwarded": True})
    return tenant_id, raw


def test_get_job_status_returns_product_job(api_key):
    tenant_id, raw = api_key
    with TestClient(app) as client:
        response = client.get(
            "/v1/jobs/wf-123",
            headers={"X-API-Key": raw, "X-Tenant-ID": tenant_id},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "wf-123"
    assert body["status"] == "completed"
    assert body["product_code"] == "value_drivers"


def test_get_missing_job_returns_404(api_key):
    tenant_id, raw = api_key
    with TestClient(app) as client:
        response = client.get(
            "/v1/jobs/missing",
            headers={"X-API-Key": raw, "X-Tenant-ID": tenant_id},
        )
    assert response.status_code == 404
