from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

from layer5_ground_truth.config import Settings, get_settings


VALID_JWT_SECRET = "layer5-production-secret-with-more-than-32-characters"
VALID_DATABASE_URL = "postgresql://layer5_app:strong-password@layer5-db.internal:5432/layer5_prod"
VALID_DATABASE_URL_SYNC = "postgresql+psycopg://layer5_app:strong-password@layer5-db.internal:5432/layer5_prod"
VALID_CORS_ORIGINS = "https://fabric.example.com,https://admin.fabric.example.com"
VALID_LAYER3_BASE_URL = "https://layer3.internal"
VALID_SERVICE_AUTH_SECRET = "layer5-service-auth-secret-with-more-than-32-characters"


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "ENVIRONMENT",
        "APP_ENV",
        "JWT_SECRET",
        "JWT_ALGORITHM",
        "JWT_ISSUER",
        "JWT_AUDIENCE",
        "JWT_FALLBACK_TO_QUERY_PARAM",
        "ALLOW_INSECURE_DEV_AUTH_BYPASS",
        "CORS_ORIGINS",
        "DATABASE_URL",
        "DATABASE_URL_SYNC",
        "DEFAULT_TENANT_ID",
        "SERVICE_AUTH_SECRET",
        "REDIS_RATE_LIMITING_REQUIRED",
        "VAULT_ADDR",
    ):
        monkeypatch.delenv(key, raising=False)


def _set_valid_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "RS256")
    monkeypatch.setenv("JWT_ISSUER", "value-fabric-internal")
    monkeypatch.setenv("JWT_AUDIENCE", "value-fabric-services")
    monkeypatch.setenv("JWT_FALLBACK_TO_QUERY_PARAM", "false")
    monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "false")
    monkeypatch.setenv("CORS_ORIGINS", VALID_CORS_ORIGINS)
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("DATABASE_URL_SYNC", VALID_DATABASE_URL_SYNC)
    monkeypatch.setenv("LAYER3_BASE_URL", VALID_LAYER3_BASE_URL)
    monkeypatch.setenv("DEFAULT_TENANT_ID", "11111111-1111-4111-8111-111111111111")
    monkeypatch.setenv("SERVICE_AUTH_SECRET", VALID_SERVICE_AUTH_SECRET)


def _install_fake_redis(monkeypatch: pytest.MonkeyPatch, *, ping_error: Exception | None) -> None:
    redis_pkg = ModuleType("redis")
    redis_asyncio = ModuleType("redis.asyncio")

    class _RedisClient:
        async def ping(self) -> None:
            if ping_error is not None:
                raise ping_error

    redis_asyncio.from_url = lambda *args, **kwargs: _RedisClient()
    redis_pkg.asyncio = redis_asyncio
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", redis_asyncio)

    rate_limiter_module = ModuleType("value_fabric.shared.identity.rate_limiter")

    class RedisRateLimiter:
        def __init__(self, client) -> None:
            self.client = client

        async def close(self) -> None:
            return None

    rate_limiter_module.RedisRateLimiter = RedisRateLimiter
    monkeypatch.setitem(sys.modules, "value_fabric.shared.identity.rate_limiter", rate_limiter_module)


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.state.telemetry_provider = None
    return app


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_startup_uses_app_env_production_for_redis_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from layer5_ground_truth.api import main

    _set_valid_production_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("APP_ENV", "production")
    _install_fake_redis(monkeypatch, ping_error=RuntimeError("redis unavailable"))

    monkeypatch.setattr(main, "validate_production_safety", lambda: None)
    monkeypatch.setattr(main, "init_db", AsyncMock())
    monkeypatch.setattr(main, "close_db", AsyncMock())
    monkeypatch.setattr(main, "is_vault_healthy", None)

    settings = Settings()
    assert settings.effective_environment == "production"
    assert settings.is_production_like is True

    with pytest.raises(RuntimeError, match="Redis rate limiting required in production but unavailable"):
        async with main.lifespan(_build_test_app()):
            pass


@pytest.mark.asyncio
async def test_startup_uses_app_env_development_to_disable_production_like_redis_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from layer5_ground_truth.api import main

    _clear_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("DATABASE_URL_SYNC", "sqlite:///:memory:")
    _install_fake_redis(monkeypatch, ping_error=RuntimeError("redis unavailable"))

    monkeypatch.setattr(main, "validate_production_safety", lambda: None)
    monkeypatch.setattr(main, "init_db", AsyncMock())
    monkeypatch.setattr(main, "close_db", AsyncMock())

    settings = Settings()
    assert settings.effective_environment == "development"
    assert settings.is_production_like is False

    app = _build_test_app()
    async with main.lifespan(app):
        assert app.state.redis_rate_limiter is None


@pytest.mark.asyncio
@pytest.mark.parametrize("app_env_alias", ["stage", "staging"])
async def test_staging_aliases_drive_vault_startup_gate(
    monkeypatch: pytest.MonkeyPatch,
    app_env_alias: str,
) -> None:
    from layer5_ground_truth.api import main

    _set_valid_production_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("APP_ENV", app_env_alias)
    monkeypatch.setenv("VAULT_ADDR", "https://vault.internal:8200")
    _install_fake_redis(monkeypatch, ping_error=None)

    monkeypatch.setattr(main, "validate_production_safety", lambda: None)
    monkeypatch.setattr(main, "init_db", AsyncMock())
    monkeypatch.setattr(main, "close_db", AsyncMock())
    monkeypatch.setattr(main, "is_vault_healthy", AsyncMock(return_value=False))

    settings = Settings()
    assert settings.effective_environment == app_env_alias
    assert settings.is_production_like is True

    with pytest.raises(RuntimeError, match="Vault unreachable"):
        async with main.lifespan(_build_test_app()):
            pass


def test_settings_normalize_mixed_environment_sources_consistently(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_valid_production_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("APP_ENV", "production")

    settings = Settings()

    assert settings.effective_environment == "production"
    assert settings.is_production_like is True

    _clear_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)

    settings = Settings()

    assert settings.effective_environment == "development"
    assert settings.is_production_like is False


@pytest.mark.asyncio
async def test_startup_exposes_redis_client_on_app_state_for_tenant_kill_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: the tenant-status kill-switch middleware reads
    ``app.state.redis_client``. The lifespan previously stored only
    ``redis_rate_limiter``, so every tenant-checked request failed closed with
    503 tenant_status_unavailable even when Redis was healthy (observed via
    the Meridian certification journey, 2026-08-12).
    """
    from layer5_ground_truth.api import main

    _clear_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("DATABASE_URL_SYNC", "sqlite:///:memory:")
    _install_fake_redis(monkeypatch, ping_error=None)

    monkeypatch.setattr(main, "validate_production_safety", lambda: None)
    monkeypatch.setattr(main, "init_db", AsyncMock())
    monkeypatch.setattr(main, "close_db", AsyncMock())
    monkeypatch.setattr(main, "is_vault_healthy", None)

    app = _build_test_app()
    async with main.lifespan(app):
        assert app.state.redis_client is not None, (
            "lifespan must expose app.state.redis_client so the tenant "
            "kill-switch can evaluate suspension status instead of failing closed"
        )
        assert app.state.redis_rate_limiter is not None
