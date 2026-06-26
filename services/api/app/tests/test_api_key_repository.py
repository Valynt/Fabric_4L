"""Tests for the gateway API-key repository."""

from __future__ import annotations

import pytest

from app.core.api_key_hash import generate_api_key, hash_api_key
from app.core.database import db
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-repository-32bytes")


@pytest.fixture
def repo():
    return APIKeyRepository(db)


def test_create_key_and_lookup_by_hash(repo):
    tenant_id = "tenant-alpha"
    request = APIKeyCreateRequest(name="Production key", role="analyst", permissions=["signals:read"])
    raw_key, key_id, prefix = generate_api_key(name=request.name)

    record = repo.create_key(tenant_id, request, raw_key, key_id, prefix)

    assert record.key_id == key_id
    assert record.tenant_id == tenant_id
    assert record.name == request.name
    assert record.key_hash == hash_api_key(raw_key)
    assert record.prefix == prefix
    assert record.role == request.role
    assert record.permissions == request.permissions
    assert record.enabled is True
    assert record.revoked_at is None

    looked_up = repo.get_by_hash(record.key_hash)
    assert looked_up is not None
    assert looked_up.key_id == key_id


def test_get_by_hash_missing_key_returns_none(repo):
    assert repo.get_by_hash("a" * 64) is None


def test_list_for_tenant_filters_by_tenant(repo):
    alpha = "tenant-alpha"
    beta = "tenant-beta"

    alpha_request = APIKeyCreateRequest(name="Alpha key")
    raw_alpha, key_id_alpha, prefix_alpha = generate_api_key(name=alpha_request.name)
    repo.create_key(alpha, alpha_request, raw_alpha, key_id_alpha, prefix_alpha)

    beta_request = APIKeyCreateRequest(name="Beta key")
    raw_beta, key_id_beta, prefix_beta = generate_api_key(name=beta_request.name)
    repo.create_key(beta, beta_request, raw_beta, key_id_beta, prefix_beta)

    alpha_items = repo.list_for_tenant(alpha)
    assert len(alpha_items) == 1
    assert alpha_items[0].key_id == key_id_alpha

    beta_items = repo.list_for_tenant(beta)
    assert len(beta_items) == 1
    assert beta_items[0].key_id == key_id_beta


def test_revoke_key_marks_disabled_and_prevents_lookup(repo):
    tenant_id = "tenant-alpha"
    request = APIKeyCreateRequest(name="Revokable key")
    raw_key, key_id, prefix = generate_api_key(name=request.name)
    record = repo.create_key(tenant_id, request, raw_key, key_id, prefix)

    revoked = repo.revoke_key(tenant_id, key_id)
    assert revoked is True

    looked_up = repo.get_by_hash(record.key_hash)
    assert looked_up is None

    items = repo.list_for_tenant(tenant_id)
    assert len(items) == 1
    assert items[0].enabled is False


def test_revoke_key_wrong_tenant_returns_false(repo):
    tenant_id = "tenant-alpha"
    request = APIKeyCreateRequest(name="Isolated key")
    raw_key, key_id, prefix = generate_api_key(name=request.name)
    repo.create_key(tenant_id, request, raw_key, key_id, prefix)

    assert repo.revoke_key("tenant-beta", key_id) is False
