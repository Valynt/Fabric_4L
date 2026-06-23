"""H-03 tests: shared resolve_cors_policy and validate_production_safety gates.

Covers:
- resolve_cors_policy rejects wildcard origins in production-like environments
- resolve_cors_policy returns explicit methods/headers (no wildcards)
- validate_production_safety raises RuntimeError for short secrets, missing CORS, etc.
"""

import pytest

from value_fabric.shared.fastapi_framework.middleware import resolve_cors_policy
from value_fabric.shared.security.config import validate_production_safety


class TestResolveCorsPolicy:
    def test_rejects_empty_origins_in_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "")
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            resolve_cors_policy()

    def test_rejects_wildcard_origin_in_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        with pytest.raises(RuntimeError, match="wildcard"):
            resolve_cors_policy()

    def test_rejects_subdomain_wildcard_in_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "https://*.example.com")
        with pytest.raises(RuntimeError, match="wildcard"):
            resolve_cors_policy()

    def test_allows_explicit_origin_in_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        policy = resolve_cors_policy()
        assert policy.allow_origins == ["https://app.example.com"]
        assert policy.allow_credentials is True

    def test_treats_unknown_env_as_production_like(self, monkeypatch):
        """Fail-safe: unknown environments are treated as production-like."""
        monkeypatch.setenv("ENVIRONMENT", "qa")
        monkeypatch.setenv("CORS_ORIGINS", "")
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            resolve_cors_policy()

    def test_development_allows_wildcard(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("CORS_ORIGINS", "")
        policy = resolve_cors_policy()
        assert policy.allow_origins == ["*"]
        assert policy.allow_credentials is False

    def test_methods_are_explicit_not_wildcard(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("CORS_ORIGINS", "")
        policy = resolve_cors_policy()
        assert "*" not in policy.allow_methods
        assert policy.allow_methods == ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

    def test_headers_are_explicit_not_wildcard(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("CORS_ORIGINS", "")
        policy = resolve_cors_policy()
        assert "*" not in policy.allow_headers
        assert policy.allow_headers == ["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID"]


class TestValidateProductionSafety:
    def _set_valid_production_env(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "x" * 48)
        monkeypatch.setenv("DATABASE_URL", "postgresql://app_fabric:pass@db.internal:5432/fabric")
        monkeypatch.setenv("CREDENTIALS_MASTER_KEY", "x" * 48)
        monkeypatch.setenv("API_KEY_HMAC_SECRET", "x" * 48)
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        monkeypatch.setenv("DEFAULT_TENANT_ID", "12345678-1234-1234-1234-123456789abc")
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "x" * 48)
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("MOCK_PERSISTENCE", raising=False)

    def test_passes_with_valid_config(self, monkeypatch):
        self._set_valid_production_env(monkeypatch)
        monkeypatch.delenv("ALLOW_DEV_AUTH_BYPASS", raising=False)
        # Should not raise
        validate_production_safety()

    def test_fails_with_short_jwt_secret(self, monkeypatch):
        self._set_valid_production_env(monkeypatch)
        monkeypatch.setenv("JWT_SECRET", "short")
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            validate_production_safety()

    def test_fails_with_missing_cors_origins(self, monkeypatch):
        self._set_valid_production_env(monkeypatch)
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            validate_production_safety()

    def test_fails_with_dev_auth_bypass_in_production(self, monkeypatch):
        self._set_valid_production_env(monkeypatch)
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")

        with pytest.raises(RuntimeError, match="ALLOW_INSECURE_DEV_AUTH_BYPASS"):
            validate_production_safety()

    def test_fails_with_default_tenant_fallback_in_production(self, monkeypatch):
        self._set_valid_production_env(monkeypatch)
        monkeypatch.setenv("DEFAULT_TENANT_ID", "default")

        with pytest.raises(RuntimeError, match="DEFAULT_TENANT_ID"):
            validate_production_safety()
