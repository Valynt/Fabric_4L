from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta

import pytest

from layer4_agents.shared.identity import oidc_state as oidc_state_module
from layer4_agents.shared.identity.oidc_state import (
    InMemoryOIDCStateStore,
    RedisOIDCStateStore,
    create_oidc_state_store,
)


class _FakeRedis:
    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: str, ex: int) -> None:
        with self._lock:
            self._data[key] = (value, time.time() + ex)

    def getdel(self, key: str):
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expires_at = item
            if time.time() > expires_at:
                del self._data[key]
                return None
            del self._data[key]
            return value


class _FrozenDateTime(datetime):
    """datetime subclass with a virtual ``now()`` for deterministic expiry tests."""

    _now: datetime = datetime(2026, 1, 1, tzinfo=UTC)

    @classmethod
    def now(cls, tz=None):
        current = cls._now
        return current if tz is None else current.astimezone(tz)


def test_in_memory_store_enforces_one_time_use() -> None:
    store = InMemoryOIDCStateStore(ttl_seconds=60, allow_non_production=True)
    store.store("state-1", "verifier-1")

    assert store.validate_and_consume("state-1") == "verifier-1"
    assert store.validate_and_consume("state-1") is None


def test_in_memory_store_enforces_expiry(monkeypatch) -> None:
    monkeypatch.setattr(oidc_state_module, "datetime", _FrozenDateTime)
    store = InMemoryOIDCStateStore(ttl_seconds=60, allow_non_production=True)
    store.store("state-exp", "verifier-exp")
    store.store("state-exp-2", "verifier-exp-2")
    # Still valid while within the TTL.
    assert store.validate_and_consume("state-exp") == "verifier-exp"

    # Advance the virtual clock past the TTL; the pre-existing token is expired.
    _FrozenDateTime._now = _FrozenDateTime._now + timedelta(seconds=61)
    assert store.validate_and_consume("state-exp-2") is None


def test_in_memory_store_requires_explicit_non_production_guard() -> None:
    with pytest.raises(RuntimeError, match="tests/development only"):
        InMemoryOIDCStateStore(ttl_seconds=60)


def test_redis_store_concurrent_consume_allows_single_winner() -> None:
    redis_store = RedisOIDCStateStore(redis_client=_FakeRedis(), ttl_seconds=30)
    redis_store.store("state-race", "verifier-race")

    results: list[str | None] = []

    def _consume() -> None:
        results.append(redis_store.validate_and_consume("state-race"))

    threads = [threading.Thread(target=_consume) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count("verifier-race") == 1
    assert results.count(None) == 15


def test_redis_store_enforces_expiry(monkeypatch) -> None:
    clock = {"now": 1_000.0}
    monkeypatch.setattr(time, "time", lambda: clock["now"])

    redis_store = RedisOIDCStateStore(redis_client=_FakeRedis(), ttl_seconds=1)
    redis_store.store("state-exp-redis", "verifier-exp-redis")
    redis_store.store("state-exp-redis-2", "verifier-exp-redis-2")
    # Still valid while within the TTL.
    assert redis_store.validate_and_consume("state-exp-redis") == "verifier-exp-redis"

    # Advance the virtual clock past the TTL; the pre-existing token is expired.
    clock["now"] += 1.5
    assert redis_store.validate_and_consume("state-exp-redis-2") is None


def test_factory_defaults_to_redis_backend() -> None:
    store = create_oidc_state_store(redis_client=_FakeRedis(), ttl_seconds=30)
    store.store("state-factory", "verifier-factory")
    assert store.validate_and_consume("state-factory") == "verifier-factory"
