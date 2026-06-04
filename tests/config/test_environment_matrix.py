"""Repository-level environment-matrix tests for production safety policy.

Every service must fail startup when required production dependencies are
unavailable. Authentication, persistence, encryption, API keys, CORS origins,
and tenant isolation must never downgrade to mock, fallback, or development
behavior in ``production`` or ``staging`` modes.

These tests exercise the shared configuration utility across the full
environment matrix to ensure the policy is enforced consistently.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from value_fabric.shared.security.config import (
    ProductionSafetyValidator,
    is_production_like_environment,
    is_strict_environment,
    validate_production_safety,
)


# ---------------------------------------------------------------------------
# Environment classification (repository-level sanity)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEnvironmentClassificationMatrix:
    @pytest.mark.parametrize(
        ("env_value", "expected_production_like", "expected_strict"),
        [
            ("production", True, True),
            ("prod", False, True),
            ("staging", False, True),
            ("stage", False, True),
            ("development", False, False),
            ("dev", False, False),
            ("local", False, False),
            ("test", False, False),
            ("testing", False, False),
            ("ci", False, False),
            ("unknown", False, True),
            ("custom-env", False, True),
            ("UAT", False, True),
            ("preprod", False, True),
        ],
    )
    def test_environment_classification(
        self,
        env_value: str,
        expected_production_like: bool,
        expected_strict: bool,
    ) -> None:
        assert is_production_like_environment(env_value) is expected_production_like
        assert is_strict_environment(env_value) is expected_strict


# ---------------------------------------------------------------------------
# Shared validator — cross-cutting controls
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSharedProductionSafetyControls:
    """Validate each control domain using the shared ProductionSafetyValidator."""

    PRODUCTION_LIKE_ENVS = ["production", "staging", "unknown"]
    DEV_ENVS = ["development", "test", "ci"]

    VALID_ENV = {
        "ENVIRONMENT": "production",
        "JWT_SECRET": "a" * 48,
        "DATABASE_URL": "postgresql://app_user:StrongP@ssw0rd@db.internal.example.com:5432/fabric_prod?sslmode=require",
        "CREDENTIALS_MASTER_KEY": "d2ViYXBwLWFwaS1rZXktZm9yLXRlc3Rpbmctb25seS0xMjM0NTY3OA==",
        "API_KEY_HMAC_SECRET": "api-key-hmac-secret-for-testing-only-12345678",
        "CORS_ORIGINS": "https://app.example.com,https://admin.example.com",
        "DEFAULT_TENANT_ID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "SERVICE_AUTH_SECRET": "service-auth-secret-for-testing-only-12345678",
        "LLM_PROVIDER": "openai",
        "DEBUG": "false",
        "ALLOW_INSECURE_DEV_AUTH_BYPASS": "false",
        "JWT_FALLBACK_TO_QUERY_PARAM": "false",
        "MOCK_PERSISTENCE": "false",
        "ALLOW_EPHEMERAL_ENCRYPTION": "false",
        "ALLOW_MOCK_LLM": "false",
        "SEED_DEMO_DATA": "false",
        "MULTI_TENANT_MODE": "true",
    }

    def _validate(self, env: dict[str, str]) -> None:
        with patch.dict(os.environ, env, clear=True):
            validate_production_safety()

    # --- Authentication --------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_auth_missing_jwt_secret(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "JWT_SECRET": ""}
        with pytest.raises(RuntimeError, match="JWT_SECRET is required"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_auth_weak_jwt_secret(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "JWT_SECRET": "short"}
        with pytest.raises(RuntimeError, match="JWT_SECRET is too short"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_auth_placeholder_jwt_secret(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "JWT_SECRET": "changeme"}
        with pytest.raises(RuntimeError, match="placeholder"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_auth_dev_bypass_enabled(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "ALLOW_INSECURE_DEV_AUTH_BYPASS": "true"}
        with pytest.raises(RuntimeError, match="ALLOW_INSECURE_DEV_AUTH_BYPASS"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_auth_query_param_fallback_enabled(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "JWT_FALLBACK_TO_QUERY_PARAM": "true"}
        with pytest.raises(RuntimeError, match="JWT_FALLBACK_TO_QUERY_PARAM"):
            self._validate(env)

    # --- Persistence -----------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_persistence_missing_database_url(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DATABASE_URL": ""}
        with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_persistence_sqlite_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DATABASE_URL": "sqlite:///./app.db"}
        with pytest.raises(RuntimeError, match="SQLite is not permitted"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_persistence_localhost_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DATABASE_URL": "postgresql://user:pass@localhost:5432/db"}
        with pytest.raises(RuntimeError, match="localhost"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_persistence_default_user_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DATABASE_URL": "postgresql://postgres:pass@db.internal:5432/db"}
        with pytest.raises(RuntimeError, match="default/weak account"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_persistence_superuser_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DATABASE_URL": "postgresql://rdsadmin:pass@db.internal:5432/db"}
        with pytest.raises(RuntimeError, match="superuser"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_persistence_mock_persistence_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "MOCK_PERSISTENCE": "true"}
        with pytest.raises(RuntimeError, match="MOCK_PERSISTENCE"):
            self._validate(env)

    # --- Encryption ------------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_encryption_missing_master_key(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "CREDENTIALS_MASTER_KEY": ""}
        with pytest.raises(RuntimeError, match="CREDENTIALS_MASTER_KEY is required"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_encryption_ephemeral_allowed_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "ALLOW_EPHEMERAL_ENCRYPTION": "true"}
        with pytest.raises(RuntimeError, match="ALLOW_EPHEMERAL_ENCRYPTION"):
            self._validate(env)

    # --- API Keys --------------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_api_keys_missing_hmac_secret(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "API_KEY_HMAC_SECRET": ""}
        with pytest.raises(RuntimeError, match="API_KEY_HMAC_SECRET is required"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_api_keys_weak_hmac_secret(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "API_KEY_HMAC_SECRET": "short"}
        with pytest.raises(RuntimeError, match="API_KEY_HMAC_SECRET is too short"):
            self._validate(env)

    # --- CORS Origins ----------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_cors_missing_origins(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "CORS_ORIGINS": ""}
        with pytest.raises(RuntimeError, match="CORS_ORIGINS is required"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_cors_wildcard_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "CORS_ORIGINS": "*"}
        with pytest.raises(RuntimeError, match="wildcard"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_cors_http_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "CORS_ORIGINS": "http://app.example.com"}
        with pytest.raises(RuntimeError, match="HTTPS"):
            self._validate(env)

    # --- Tenant Isolation ------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_tenant_missing_default_tenant(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DEFAULT_TENANT_ID": ""}
        with pytest.raises(RuntimeError, match="DEFAULT_TENANT_ID is required"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_tenant_literal_default_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DEFAULT_TENANT_ID": "default"}
        with pytest.raises(RuntimeError, match="literal value 'default'"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_tenant_invalid_uuid_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DEFAULT_TENANT_ID": "not-a-uuid"}
        with pytest.raises(RuntimeError, match="not a valid UUID"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_tenant_missing_service_auth_secret(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "SERVICE_AUTH_SECRET": ""}
        with pytest.raises(RuntimeError, match="SERVICE_AUTH_SECRET is required"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_tenant_disabled_multi_tenant_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "MULTI_TENANT_MODE": "false"}
        with pytest.raises(RuntimeError, match="MULTI_TENANT_MODE"):
            self._validate(env)

    # --- External Providers ----------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_providers_mock_llm_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "LLM_PROVIDER": "mock"}
        with pytest.raises(RuntimeError, match="mock"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_providers_allow_mock_llm_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "ALLOW_MOCK_LLM": "true"}
        with pytest.raises(RuntimeError, match="ALLOW_MOCK_LLM"):
            self._validate(env)

    # --- Debug Flags -----------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_debug_true_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DEBUG": "true"}
        with pytest.raises(RuntimeError, match="DEBUG"):
            self._validate(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_seed_demo_data_rejected(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "SEED_DEMO_DATA": "true"}
        with pytest.raises(RuntimeError, match="SEED_DEMO_DATA"):
            self._validate(env)

    # --- Valid configuration passes --------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS + DEV_ENVS)
    def test_valid_config_passes(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment}
        self._validate(env)

    # --- Development relaxations -----------------------------------------

    @pytest.mark.parametrize("environment", DEV_ENVS)
    def test_dev_allows_sqlite(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "DATABASE_URL": "sqlite:///./dev.db"}
        self._validate(env)

    @pytest.mark.parametrize("environment", DEV_ENVS)
    def test_dev_allows_wildcard_cors(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "CORS_ORIGINS": "*"}
        self._validate(env)

    @pytest.mark.parametrize("environment", DEV_ENVS)
    def test_dev_allows_mock_llm(self, environment: str) -> None:
        env = {**self.VALID_ENV, "ENVIRONMENT": environment, "LLM_PROVIDER": "mock"}
        self._validate(env)

    # --- Accumulated errors ----------------------------------------------

    def test_all_errors_reported_together(self) -> None:
        env = {
            **self.VALID_ENV,
            "JWT_SECRET": "short",
            "DATABASE_URL": "sqlite:///./app.db",
            "CREDENTIALS_MASTER_KEY": "",
            "API_KEY_HMAC_SECRET": "",
            "CORS_ORIGINS": "*",
            "DEFAULT_TENANT_ID": "default",
            "SERVICE_AUTH_SECRET": "",
            "LLM_PROVIDER": "mock",
            "DEBUG": "true",
            "ALLOW_INSECURE_DEV_AUTH_BYPASS": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                validate_production_safety()

        message = str(exc_info.value)
        assert "JWT_SECRET is too short" in message
        assert "SQLite is not permitted" in message
        assert "CREDENTIALS_MASTER_KEY is required" in message
        assert "API_KEY_HMAC_SECRET is required" in message
        assert "wildcard" in message.lower()
        assert "literal value 'default'" in message
        assert "SERVICE_AUTH_SECRET is required" in message
        assert "mock" in message.lower()
        assert "DEBUG" in message
        assert "ALLOW_INSECURE_DEV_AUTH_BYPASS" in message


# ---------------------------------------------------------------------------
# Canonical entry-point sanity
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCanonicalEntryPoint:
    def test_validate_production_safety_is_callable(self) -> None:
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 48,
            "DATABASE_URL": "postgresql://app_user:pass@db.internal:5432/fabric_prod?sslmode=require",
            "CREDENTIALS_MASTER_KEY": "d2ViYXBwLWFwaS1rZXktZm9yLXRlc3Rpbmctb25seS0xMjM0NTY3OA==",
            "API_KEY_HMAC_SECRET": "api-key-hmac-secret-for-testing-only-12345678",
            "CORS_ORIGINS": "https://app.example.com",
            "DEFAULT_TENANT_ID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "SERVICE_AUTH_SECRET": "service-auth-secret-for-testing-only-12345678",
            "LLM_PROVIDER": "openai",
            "DEBUG": "false",
            "ALLOW_INSECURE_DEV_AUTH_BYPASS": "false",
            "JWT_FALLBACK_TO_QUERY_PARAM": "false",
            "MOCK_PERSISTENCE": "false",
            "ALLOW_EPHEMERAL_ENCRYPTION": "false",
            "ALLOW_MOCK_LLM": "false",
            "SEED_DEMO_DATA": "false",
            "MULTI_TENANT_MODE": "true",
        }, clear=True):
            validate_production_safety()
