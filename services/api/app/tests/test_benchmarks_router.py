from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.api_key_hash import generate_api_key
from app.main import app
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "s" * 32)


@pytest.fixture
def api_key():
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="bench-test")
    repo = APIKeyRepository()
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="bench-test", role="analyst", permissions=["benchmarks:read"]),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    return tenant_id, raw


def _mock_transport():
    def handler(request: httpx.Request):
        if request.url.path == "/v1/benchmarks/datasets":
            return httpx.Response(200, json=[{"dataset_id": "ds1"}])
        if request.url.path == "/v1/benchmarks/compare":
            return httpx.Response(200, json={"percentile": 50})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_list_benchmarks_with_api_key(api_key, monkeypatch):
    tenant_id, raw = api_key
    original_async_client = httpx.AsyncClient

    def _patched_async_client(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original_async_client(transport=_mock_transport(), timeout=1.0)

    monkeypatch.setattr("httpx.AsyncClient", _patched_async_client)

    with TestClient(app) as client:
        response = client.get(
            "/v1/benchmarks",
            headers={"X-API-Key": raw, "X-Tenant-ID": tenant_id},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["items"]


def test_list_benchmarks_unauthenticated():
    with TestClient(app) as client:
        response = client.get("/v1/benchmarks")
    assert response.status_code == 401


def test_list_benchmarks_without_permission_denied(monkeypatch):
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="bench-no-perm")
    repo = APIKeyRepository()
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="bench-no-perm", role="read_only"),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    original_async_client = httpx.AsyncClient

    def _patched_async_client(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original_async_client(transport=_mock_transport(), timeout=1.0)

    monkeypatch.setattr("httpx.AsyncClient", _patched_async_client)

    with TestClient(app) as client:
        response = client.get(
            "/v1/benchmarks",
            headers={"X-API-Key": raw, "X-Tenant-ID": tenant_id},
        )
    assert response.status_code == 403
    body = response.json()
    assert body.get("detail", {}).get("code") == "INSUFFICIENT_SCOPE" or body.get("error", {}).get("code") == "INSUFFICIENT_SCOPE"


def test_list_benchmarks_quota_exceeded(api_key, monkeypatch):
    tenant_id, raw = api_key
    monkeypatch.setenv("QUOTA_BENCHMARKS", "0")
    original_async_client = httpx.AsyncClient

    def _patched_async_client(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original_async_client(transport=_mock_transport(), timeout=1.0)

    monkeypatch.setattr("httpx.AsyncClient", _patched_async_client)

    with TestClient(app) as client:
        response = client.get(
            "/v1/benchmarks",
            headers={"X-API-Key": raw, "X-Tenant-ID": tenant_id},
        )
    assert response.status_code == 429
    body = response.json()
    assert body.get("detail", {}).get("code") == "QUOTA_EXCEEDED" or body.get("error", {}).get("code") == "QUOTA_EXCEEDED"
