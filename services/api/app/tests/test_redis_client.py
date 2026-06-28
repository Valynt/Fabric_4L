"""Tests for ``app.core.redis_client``.

These tests exercise the Redis client factory used by account idempotency
and token revocation.  They do not require a running Redis server.
"""

from __future__ import annotations

import pytest

import app.core.redis_client as _redis_client_mod
from app.core.config import get_settings


def _reset_redis_singleton() -> None:
    """Clear the module-level singleton so tests can observe creation."""
    _redis_client_mod._redis_client = None  # type: ignore[attr-defined]
    _redis_client_mod._client_initialised = False  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    _reset_redis_singleton()
    get_settings.cache_clear()
    yield
    _reset_redis_singleton()
    get_settings.cache_clear()


def test_get_redis_client_returns_singleton():
    """Calling the factory twice returns the same cached client."""
    client = _redis_client_mod.get_redis_client()
    assert client is _redis_client_mod.get_redis_client()


def test_get_redis_client_returns_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch):
    """Without REDIS_URL, the factory returns None."""
    # Override any repository-local .env value so this test remains hermetic in
    # developer environments that have Redis configured.
    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()

    client = _redis_client_mod.get_redis_client()
    assert client is None


def test_get_redis_client_uses_settings_redis_url(monkeypatch: pytest.MonkeyPatch):
    """When Settings.redis_url is set, a Redis client is created."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()

    client = _redis_client_mod.get_redis_client()
    assert client is not None
    # Do not attempt a network operation; just verify the object was constructed.
