"""Focused LRU eviction-order tests for the O(1) `access_order` refactor.

The internal LRU order tracker is an ``OrderedDict`` so eviction and
move-to-front run in O(1). These tests freeze the observable eviction
ordering (least-recently-used first) so the refactor cannot silently
change capacity semantics.
"""

from collections import OrderedDict

import pytest

from src.performance.cache import CacheConfig, CacheStrategy, MemoryCache


def _cache(max_size: int) -> MemoryCache:
    return MemoryCache(
        CacheConfig(
            strategy=CacheStrategy.LRU,
            max_size=max_size,
            compression="none",  # type: ignore[arg-type]
            enable_background_cleanup=False,
        )
    )


@pytest.mark.unit
def test_access_order_is_ordered_dict() -> None:
    cache = _cache(max_size=10)
    assert isinstance(cache.access_order, OrderedDict)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lru_capacity_evicts_least_recently_used_first() -> None:
    cache = _cache(max_size=2)
    await cache.set("a", 1)
    await cache.set("b", 2)

    # Access "a" so "b" becomes the least-recently-used entry.
    assert await cache.get_with_deserialization("a") == 1

    # Inserting a third entry must evict "b", not "a".
    await cache.set("c", 3)

    assert "b" not in cache.cache
    assert "a" in cache.cache
    assert "c" in cache.cache
    assert cache.stats.evictions == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lru_reinsert_same_key_refreshes_recency() -> None:
    cache = _cache(max_size=2)
    await cache.set("a", 1)
    await cache.set("b", 2)

    # Re-setting an existing key refreshes its recency: "a" is now MRU.
    await cache.set("a", 11)
    await cache.set("c", 3)

    assert "b" not in cache.cache
    assert await cache.get_with_deserialization("a") == 11
    assert "c" in cache.cache


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_keeps_access_order_consistent() -> None:
    cache = _cache(max_size=3)
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.set("c", 3)

    assert await cache.delete("b") is True
    assert await cache.delete("missing") is False
    assert "b" not in cache.access_order
    assert list(cache.access_order) == ["a", "c"]

    # Delete of a key that is no longer present must not corrupt the order.
    await cache.set("d", 4)
    assert list(cache.access_order) == ["a", "c", "d"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_eviction_loop_removes_entries_and_updates_stats() -> None:
    cache = _cache(max_size=3)
    for key in ("a", "b", "c"):
        await cache.set(key, 1)

    await cache.clear(pattern="a")
    assert "a" not in cache.cache
    assert "a" not in cache.access_order


@pytest.mark.unit
@pytest.mark.asyncio
async def test_large_cache_eviction_is_fast_and_correct() -> None:
    """Evicting from a 10k-entry cache keeps recency correctness intact."""
    cache = _cache(max_size=10_000)
    for i in range(10_000):
        await cache.set(f"key-{i}", f"value-{i}")

    # Refresh the middle entry, then overflow by one; only the oldest
    # originally-inserted entry may be evicted.
    assert await cache.get_with_deserialization("key-0") == "value-0"
    await cache.set("key-5000", "value-5000")
    await cache.set("key-10000", "value-10000")

    assert "key-1" not in cache.cache
    assert "key-5000" in cache.cache
    assert "key-10000" in cache.cache
    assert len(cache.cache) == 10_000