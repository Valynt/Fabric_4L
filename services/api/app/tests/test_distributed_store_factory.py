"""Tests for the distributed store factory and its test-time fallback.

These tests verify that ``get_distributed_store()`` can operate without a live
Redis server when ``MOCK_PERSISTENCE=true``, matching the existing in-memory
database fallback used by the rest of the API test suite.
"""

from __future__ import annotations

import pytest

import app.services.distributed_store as _store_mod
from app.core.config import get_settings


def _reset_store_singleton() -> None:
    """Clear the module-level store singleton so tests observe fresh creation."""
    _store_mod._store_singleton = None  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _reset_singleton():
    _reset_store_singleton()
    get_settings.cache_clear()
    yield
    _reset_store_singleton()
    get_settings.cache_clear()


def test_get_distributed_store_uses_in_memory_when_mock_persistence(
    monkeypatch: pytest.MonkeyPatch,
):
    """With MOCK_PERSISTENCE=true, the factory returns an in-memory store."""
    monkeypatch.setenv("MOCK_PERSISTENCE", "true")

    store = _store_mod.get_distributed_store()

    assert isinstance(store, _store_mod.InMemoryDistributedStore)
    # Must not raise; this is the call made during app startup lifespan.
    store.validate_backend()


def test_in_memory_store_round_trips_json():
    """The in-memory store satisfies the DistributedStore contract."""
    store = _store_mod.InMemoryDistributedStore()
    store.set_json("key", {"tenant_id": "t1"}, ttl_seconds=60)
    assert store.get_json("key") == {"tenant_id": "t1"}
    assert store.delete("key") is True
    assert store.get_json("key") is None


def test_get_distributed_store_fails_when_redis_not_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    """Without MOCK_PERSISTENCE and without REDIS_URL, the factory fails fast."""
    monkeypatch.delenv("MOCK_PERSISTENCE", raising=False)
    # Override any repository-local .env value so this test remains hermetic in
    # developer environments that have Redis configured.
    monkeypatch.setenv("REDIS_URL", "")

    with pytest.raises(_store_mod.StoreUnavailableError):
        _store_mod.get_distributed_store()
