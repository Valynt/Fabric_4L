"""Unit tests for Layer 5 configuration validation (P0-004)."""

from __future__ import annotations

import pytest

from layer5_ground_truth.config import (
    Settings,
    _has_default_database_credentials,
    _is_local_database_url,
    _normalize_environment,
    _parse_cors_origins,
    is_production_like_environment,
)

pytestmark = [pytest.mark.unit]


class TestNormalizeEnvironment:
    """Environment name normalization."""

    def test_none_defaults_to_development(self) -> None:
        assert _normalize_environment(None) == "development"

    def test_strips_whitespace(self) -> None:
        assert _normalize_environment("  PRODUCTION  ") == "production"

    def test_lowercases(self) -> None:
        assert _normalize_environment("Staging") == "staging"


class TestIsProductionLikeEnvironment:
    """Production-like environment strict allowlist."""

    def test_staging_is_true(self) -> None:
        assert is_production_like_environment("staging") is True

    def test_stage_is_true(self) -> None:
        assert is_production_like_environment("stage") is True

    def test_production_is_true(self) -> None:
        assert is_production_like_environment("production") is True

    def test_prod_is_true(self) -> None:
        assert is_production_like_environment("prod") is True

    def test_none_is_false(self) -> None:
        assert is_production_like_environment(None) is False

    def test_development_is_false(self) -> None:
        assert is_production_like_environment("development") is False


class TestParseCorsOrigins:
    """CORS origin list parsing."""

    def test_empty_returns_empty(self) -> None:
        assert _parse_cors_origins("") == []

    def test_single_origin(self) -> None:
        assert _parse_cors_origins("https://app.example.com") == ["https://app.example.com"]

    def test_multiple_origins(self) -> None:
        assert _parse_cors_origins("https://a.com, https://b.com") == ["https://a.com", "https://b.com"]

    def test_trims_whitespace(self) -> None:
        assert _parse_cors_origins("  https://a.com  ,  https://b.com  ") == ["https://a.com", "https://b.com"]

    def test_skips_empty_entries(self) -> None:
        assert _parse_cors_origins("https://a.com,,https://b.com") == ["https://a.com", "https://b.com"]


class TestIsLocalDatabaseUrl:
    """Local database URL detection."""

    def test_sqlite_is_local(self) -> None:
        assert _is_local_database_url("sqlite:///./app.db") is True

    def test_localhost_postgres_is_local(self) -> None:
        assert _is_local_database_url("postgresql+asyncpg://user:pass@localhost:5432/db") is True

    def test_127_0_0_1_is_local(self) -> None:
        assert _is_local_database_url("postgresql+asyncpg://user:pass@127.0.0.1:5432/db") is True

    def test_remote_postgres_is_not_local(self) -> None:
        assert _is_local_database_url("postgresql+asyncpg://user:pass@db.example.com:5432/db") is False


class TestHasDefaultDatabaseCredentials:
    """Default/placeholder credential detection."""

    def test_postgres_username_is_default(self) -> None:
        assert _has_default_database_credentials("postgresql+asyncpg://postgres:secret@host/db") is True

    def test_empty_password_is_default(self) -> None:
        assert _has_default_database_credentials("postgresql+asyncpg://user:@host/db") is True

    def test_custom_credentials_are_safe(self) -> None:
        assert _has_default_database_credentials("postgresql+asyncpg://myuser:mypassword@host/db") is False


class TestSettingsValidators:
    """Pydantic settings validation rules — tested via env vars for determinism."""

    def test_database_url_asyncpg_injected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
        monkeypatch.setenv("ENVIRONMENT", "development")
        s = Settings()
        assert "asyncpg" in s.database_url

    def test_layer3_base_url_rejects_ftp(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER3_BASE_URL", "ftp://host")
        monkeypatch.setenv("ENVIRONMENT", "development")
        with pytest.raises(ValueError, match="http or https"):
            Settings()

    def test_layer3_base_url_rejects_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER3_BASE_URL", "http://host/api")
        monkeypatch.setenv("ENVIRONMENT", "development")
        with pytest.raises(ValueError, match="path"):
            Settings()

    def test_layer3_base_url_rejects_query(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER3_BASE_URL", "http://host?key=val")
        monkeypatch.setenv("ENVIRONMENT", "development")
        with pytest.raises(ValueError, match="query"):
            Settings()

    def test_layer3_base_url_strips_trailing_slash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER3_BASE_URL", "http://host/")
        monkeypatch.setenv("ENVIRONMENT", "development")
        s = Settings()
        assert s.layer3_base_url == "http://host"

    def test_production_rejects_debug(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        monkeypatch.setenv("JWT_ISSUER", "issuer")
        monkeypatch.setenv("JWT_AUDIENCE", "audience")
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@remote/db")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://u:p@remote/db")
        monkeypatch.setenv("LAYER3_BASE_URL", "http://remote")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        with pytest.raises(ValueError, match="DEBUG must be false"):
            Settings()

    def test_production_rejects_hs256(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("JWT_ALGORITHM", "HS256")
        monkeypatch.setenv("JWT_ISSUER", "issuer")
        monkeypatch.setenv("JWT_AUDIENCE", "audience")
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@remote/db")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://u:p@remote/db")
        monkeypatch.setenv("LAYER3_BASE_URL", "http://remote")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        with pytest.raises(ValueError, match="HS256"):
            Settings()

    def test_production_rejects_weak_jwt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("JWT_SECRET", "changeme-in-production")
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        monkeypatch.setenv("JWT_ISSUER", "issuer")
        monkeypatch.setenv("JWT_AUDIENCE", "audience")
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@remote/db")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://u:p@remote/db")
        monkeypatch.setenv("LAYER3_BASE_URL", "http://remote")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        with pytest.raises(ValueError, match="JWT_SECRET"):
            Settings()

    def test_production_rejects_localhost_layer3(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        monkeypatch.setenv("JWT_ISSUER", "issuer")
        monkeypatch.setenv("JWT_AUDIENCE", "audience")
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@remote/db")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://u:p@remote/db")
        monkeypatch.setenv("LAYER3_BASE_URL", "http://localhost:8003")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        with pytest.raises(ValueError, match="localhost"):
            Settings()

    def test_production_rejects_wildcard_cors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        monkeypatch.setenv("JWT_ISSUER", "issuer")
        monkeypatch.setenv("JWT_AUDIENCE", "audience")
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@remote/db")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://u:p@remote/db")
        monkeypatch.setenv("LAYER3_BASE_URL", "http://remote")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        with pytest.raises(ValueError, match="wildcard"):
            Settings()

    def test_production_rejects_empty_cors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        monkeypatch.setenv("JWT_ISSUER", "issuer")
        monkeypatch.setenv("JWT_AUDIENCE", "audience")
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@remote/db")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://u:p@remote/db")
        monkeypatch.setenv("LAYER3_BASE_URL", "http://remote")
        monkeypatch.setenv("CORS_ORIGINS", "")
        with pytest.raises(ValueError, match="CORS_ORIGINS"):
            Settings()

    def test_production_accepts_valid_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        monkeypatch.setenv("JWT_ISSUER", "issuer")
        monkeypatch.setenv("JWT_AUDIENCE", "audience")
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@remote/db")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://u:p@remote/db")
        monkeypatch.setenv("LAYER3_BASE_URL", "http://remote")
        monkeypatch.setenv("DEFAULT_TENANT_ID", "tenant-1")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        s = Settings()
        assert s.is_production_like is True
