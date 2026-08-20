"""Focused serialization tests for the performance cache implementations."""

from collections.abc import Callable
from typing import cast

import pytest

from src.performance.cache import (
    CacheConfig,
    CompressionType,
    MemoryCache,
    RedisCache,
    SerializationType,
)


def _memory_cache(serialization: SerializationType) -> MemoryCache:
    return MemoryCache(
        CacheConfig(
            serialization=serialization,
            compression=CompressionType.NONE,
            enable_background_cleanup=False,
        )
    )


def _redis_cache(serialization: SerializationType) -> RedisCache:
    return RedisCache(
        "redis://unused",
        CacheConfig(serialization=serialization, compression=CompressionType.NONE),
    )


@pytest.fixture(params=[_memory_cache, _redis_cache], ids=["memory", "redis"])
def cache_factory(request: pytest.FixtureRequest) -> Callable[[SerializationType], object]:
    return request.param


@pytest.mark.unit
def test_msgpack_round_trip_preserves_supported_nested_values(
    cache_factory: Callable[[SerializationType], object],
) -> None:
    cache = cache_factory(SerializationType.MSGPACK)
    value = {
        "mapping": {
            "list": ["value", 42, True, False, None, b"binary-value"],
        },
        "integer": -7,
    }

    assert cache._deserialize(cache._serialize(value)) == value


@pytest.mark.unit
@pytest.mark.parametrize("operation", ["serialize", "deserialize"])
def test_pickle_serialization_is_rejected(
    cache_factory: Callable[[SerializationType], object], operation: str
) -> None:
    cache = cache_factory(SerializationType.PICKLE)

    with pytest.raises(ValueError, match="pickle serializer is disabled"):
        if operation == "serialize":
            cache._serialize({"unsafe": True})
        else:
            cache._deserialize(b"unsafe")


@pytest.mark.unit
@pytest.mark.parametrize("operation", ["serialize", "deserialize"])
def test_unknown_serialization_type_is_rejected(
    cache_factory: Callable[[SerializationType], object], operation: str
) -> None:
    cache = cache_factory(SerializationType.JSON)
    cache.config.serialization = cast(SerializationType, "unknown")

    with pytest.raises(ValueError, match="Unsupported serialization type"):
        if operation == "serialize":
            cache._serialize({"value": True})
        else:
            cache._deserialize(b'{"value": true}')
