import sys
import types

import pytest

from layer2_extraction.extraction import cache as cache_module


class BackendUnavailable(Exception):
    pass


def _install_fake_aioredis(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    redis_pkg = types.ModuleType("redis")
    redis_pkg.__path__ = []
    aioredis = types.ModuleType("redis.asyncio")

    def from_url(*_args, **_kwargs):
        raise error

    aioredis.from_url = from_url
    redis_pkg.asyncio = aioredis
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", aioredis)


def test_redis_backend_error_falls_back_to_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache_module, "_REDIS_ERRORS", (BackendUnavailable,))
    _install_fake_aioredis(monkeypatch, BackendUnavailable("redis unavailable"))

    cache = cache_module.ExtractionCache(redis_url="redis://localhost:6379")

    assert cache._redis is None
    assert cache._fallback is not None


def test_unexpected_redis_initialization_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache_module, "_REDIS_ERRORS", (BackendUnavailable,))
    _install_fake_aioredis(monkeypatch, ValueError("bad init"))

    with pytest.raises(ValueError, match="bad init"):
        cache_module.ExtractionCache(redis_url="redis://localhost:6379")

def test_omitted_redis_url_uses_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    configured_url = "redis://cache.internal:6379"
    seen_urls: list[str] = []
    redis_pkg = types.ModuleType("redis")
    redis_pkg.__path__ = []
    aioredis = types.ModuleType("redis.asyncio")

    def from_url(url: str, **_kwargs):
        seen_urls.append(url)
        return object()

    aioredis.from_url = from_url
    redis_pkg.asyncio = aioredis
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", aioredis)
    monkeypatch.setenv("REDIS_URL", configured_url)

    cache_module.ExtractionCache()

    assert seen_urls == [configured_url]


def test_explicit_none_redis_url_ignores_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://cache.internal:6379")

    cache = cache_module.ExtractionCache(redis_url=None)

    assert cache._redis is None
