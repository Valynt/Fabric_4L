"""Regression protection: L6 must wire Redis into its GovernanceMiddleware.

Failure mode covered: Layer 6 registered GovernanceMiddleware without a
rate_limiter, so the tenant kill-switch had no Redis handle and failed
closed with 503 tenant_status_unavailable on every tenant-checked route
(e.g. GET /v1/benchmarks/datasets via the gateway), even with Redis healthy
(observed via the Meridian certification journey, 2026-08-12).

The wiring happens at module import (redis.from_url is lazy), so these tests
set REDIS_URL and import the module fresh.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def _install_fake_redis(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake_client = MagicMock(name="fake-redis-client")

    redis_pkg = ModuleType("redis")
    redis_asyncio = ModuleType("redis.asyncio")
    redis_asyncio.from_url = lambda *args, **kwargs: fake_client
    redis_pkg.asyncio = redis_asyncio
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", redis_asyncio)
    return fake_client


def _import_main_fresh(monkeypatch: pytest.MonkeyPatch):
    for name in list(sys.modules):
        if name == "layer6_benchmarks" or name.startswith("layer6_benchmarks."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    import layer6_benchmarks.api.main as main_module

    return main_module


def test_middleware_receives_redis_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _install_fake_redis(monkeypatch)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")

    main_module = _import_main_fresh(monkeypatch)

    assert main_module._l6_redis_client is fake_client
    assert main_module.app.state.redis_client is fake_client


def test_middleware_wiring_without_redis_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_redis(monkeypatch)
    monkeypatch.delenv("REDIS_URL", raising=False)

    main_module = _import_main_fresh(monkeypatch)

    assert main_module._l6_redis_client is None
    assert main_module.app.state.redis_client is None
