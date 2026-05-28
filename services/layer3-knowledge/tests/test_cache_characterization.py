from __future__ import annotations

"""OSS-0 characterization tests for L3 cache behavior.

These tests freeze observable cache-manager and request-deduplication behavior before
future OSS-backed cache implementations are introduced behind CachePort.
"""


import asyncio
from typing import Any

import pytest

from value_fabric.layer3.cache.redis_cache import CacheManager, RequestDeduplicator


class FakeAsyncCache:
    """Minimal async cache test double matching the RedisCache public surface."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self.set_calls: list[tuple[str, Any, int | None]] = []
        self.delete_calls: list[str] = []

    async def get(self, key: str) -> Any:
        return self.values.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self.values[key] = value
        self.set_calls.append((key, value, ttl))
        return True

    async def delete(self, key: str) -> bool:
        self.delete_calls.append(key)
        self.values.pop(key, None)
        return True

    async def clear_pattern(self, pattern: str) -> int:
        matching = [key for key in self.values if key.startswith(pattern.rstrip("*"))]
        for key in matching:
            self.values.pop(key, None)
        return len(matching)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_manager_get_or_set_coalesces_concurrent_same_key_misses() -> None:
    """Concurrent callers for the same missing key share one factory execution."""

    cache = FakeAsyncCache()
    manager = CacheManager(cache)  # type: ignore[arg-type]
    factory_calls = 0

    async def factory() -> dict[str, str]:
        nonlocal factory_calls
        factory_calls += 1
        await asyncio.sleep(0.01)
        return {"source": "factory"}

    results = await asyncio.gather(
        manager.get_or_set("expensive:key", factory, ttl=60),
        manager.get_or_set("expensive:key", factory, ttl=60),
        manager.get_or_set("expensive:key", factory, ttl=60),
    )

    assert results == [{"source": "factory"}] * 3
    assert factory_calls == 1
    assert cache.set_calls == [("expensive:key", {"source": "factory"}, 60)]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_manager_get_or_set_returns_cached_value_without_factory() -> None:
    """A cache hit bypasses the factory and preserves the cached value shape."""

    cache = FakeAsyncCache()
    cache.values["cached:key"] = {"source": "cache"}
    manager = CacheManager(cache)  # type: ignore[arg-type]

    async def factory() -> dict[str, str]:
        raise AssertionError("factory should not be called on cache hit")

    assert await manager.get_or_set("cached:key", factory, ttl=60) == {"source": "cache"}
    assert cache.set_calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_deduplicator_uses_stable_sorted_parameter_hashes() -> None:
    """Parameter order does not affect request-deduplication keys."""

    cache = FakeAsyncCache()
    deduplicator = RequestDeduplicator(cache)  # type: ignore[arg-type]

    key_a = deduplicator._generate_request_key("hybrid_search", {"b": 2, "a": 1})
    key_b = deduplicator._generate_request_key("hybrid_search", {"a": 1, "b": 2})

    assert key_a == key_b
    assert key_a.startswith("dedup:hybrid_search:")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_deduplicator_shares_in_flight_results_and_cleans_lock() -> None:
    """Identical concurrent requests execute once and share the same result."""

    cache = FakeAsyncCache()
    deduplicator = RequestDeduplicator(cache)  # type: ignore[arg-type]
    executor_calls = 0

    async def executor() -> dict[str, str]:
        nonlocal executor_calls
        executor_calls += 1
        await asyncio.sleep(0.01)
        return {"result": "shared"}

    results = await asyncio.gather(
        deduplicator.execute("graphrag_query", {"query": "same"}, executor),
        deduplicator.execute("graphrag_query", {"query": "same"}, executor),
    )

    assert results == [{"result": "shared"}, {"result": "shared"}]
    assert executor_calls == 1
    assert any(key.startswith("dedup:graphrag_query:") for key in cache.delete_calls)
    assert deduplicator._pending == {}
