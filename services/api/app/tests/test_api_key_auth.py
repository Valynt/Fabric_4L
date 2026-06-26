from uuid import uuid4

import pytest

from app.core.api_key_auth import resolve_api_key
from app.core.api_key_hash import generate_api_key
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


@pytest.fixture
def repo():
    return APIKeyRepository()


async def test_resolve_api_key_returns_context(repo):
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="test")
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="resolver-test", role="analyst", permissions=["benchmarks:read"]),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    ctx = await resolve_api_key(raw)
    assert ctx is not None
    assert ctx["tenant_id"] == tenant_id
    assert ctx["key_id"] == key_id
    assert "benchmarks:read" in ctx["permissions"]


async def test_resolve_invalid_key_returns_none():
    assert await resolve_api_key("not-a-key") is None


async def test_resolve_revoked_key_returns_none(repo):
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="test")
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="revoked"),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    repo.revoke_key(tenant_id, key_id)
    assert await resolve_api_key(raw) is None
