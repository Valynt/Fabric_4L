"""Environment-matrix tests for ProductionSafetyValidator.

Every service must fail startup when required production dependencies are
unavailable. Authentication, persistence, encryption, API keys, CORS origins,
and tenant isolation must never downgrade to mock, fallback, or development
behavior in ``production`` or ``staging`` modes (or any unknown environment).
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from value_fabric.shared.security.config import (
    ProductionSafetyValidator,
    is_production_like_environment,
    validate_production_safety,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(**kwargs: str) -> dict[str, str]:
    """Build a clean environment dict with only the given variables set."""
    base: dict[str, str] = {}
    for key, value in kwargs.items():
        base[key.upper()] = value
    return base


_VALID_PROD_ENV = _env(
    ENVIRONMENT="production",
    JWT_SECRET="a" * 48,
    DATABASE_URL="postgresql://app_user:StrongP@ssw0rd@db.internal.example.com:5432/fabric_prod?sslmode=require",
    CREDENTIALS_MASTER_KEY="d2ViYXBwLWFwaS1rZXktZm9yLXRlc3Rpbmctb25seS0xMjM0NTY3OA==",
    API_KEY_HMAC_SECRET="api-key-hmac-secret-for-testing-only-12345678",
    CORS_ORIGINS="https://app.example.com,https://admin.example.com",
    DEFAULT_TENANT_ID="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    SERVICE_AUTH_SECRET="service-auth-secret-for-testing-only-12345678",
    LLM_PROVIDER="openai",
    DEBUG="false",
    ALLOW_INSECURE_DEV_AUTH_BYPASS="false",
    JWT_FALLBACK_TO_QUERY_PARAM="false",
    MOCK_PERSISTENCE="false",
    ALLOW_EPHEMERAL_ENCRYPTION="false",
    ALLOW_MOCK_LLM="false",
    SEED_DEMO_DATA="false",
    MULTI_TENANT_MODE="true",
)


# ---------------------------------------------------------------------------
# Environment classification
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEnvironmentClassification:
    @pytest.mark.parametrize(
        ("env_value", "expected"),
        [
            ("production", True),
            ("prod", False),
            ("staging", False),
            ("stage", False),
            ("development", False),
            ("dev", False),
            ("local", False),
            ("test", False),
            ("testing", False),
            ("ci", False),
            ("unknown", False),
            ("custom-env", False),
        ],
    )
    def test_is_production_like_environment(self, env_value: str, expected: bool) -> None:
        assert is_production_like_environment(env_value) is expected

    @pytest.mark.parametrize(
        ("env_value", "expected"),
        [
            ("production", True),
            ("prod", True),
            ("staging", True),
            ("stage", True),
            ("development", False),
            ("dev", False),
            ("local", False),
            ("test", False),
            ("testing", False),
            ("ci", False),
            ("unknown", True),   # fail-safe: unknown = strict
            ("custom-env", True),  # fail-safe: unknown = strict
        ],
    )
    def test_is_strict_environment(self, env_value: str, expected: bool) -> None:
        from value_fabric.shared.security.config import is_strict_environment
        assert is_strict_environment(env_value) is expected


# ---------------------------------------------------------------------------
# Matrix: every control × every environment class
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestProductionSafetyMatrix:
    """Parametrised matrix across environment modes and missing controls."""

    # Environments that MUST fail closed
    PRODUCTION_LIKE_ENVS = ["production", "staging", "unknown"]
    # Environments that MUST allow startup (with warnings)
    DEV_ENVS = ["development", "test", "ci"]

    def _run_validation(self, env: dict[str, str]) -> None:
        """Call validate_production_safety under a patched environment."""
        with patch.dict(os.environ, env, clear=True):
            validate_production_safety()

    # --- Authentication --------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_missing_jwt_secret_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "JWT_SECRET": ""}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "JWT_SECRET is required" in str(exc_info.value)

    @pytest.mark.parametrize("environment", DEV_ENVS)
    def test_missing_jwt_secret_warns_in_dev(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "JWT_SECRET": ""}
        # Should NOT raise in dev
        self._run_validation(env)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_weak_jwt_secret_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "JWT_SECRET": "short"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "JWT_SECRET is too short" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_placeholder_jwt_secret_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "JWT_SECRET": "changeme"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "placeholder" in str(exc_info.value).lower()

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_dev_auth_bypass_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "ALLOW_INSECURE_DEV_AUTH_BYPASS": "true"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "ALLOW_INSECURE_DEV_AUTH_BYPASS" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_jwt_query_param_fallback_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "JWT_FALLBACK_TO_QUERY_PARAM": "true"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "JWT_FALLBACK_TO_QUERY_PARAM" in str(exc_info.value)

    # --- Persistence -----------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_missing_database_url_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "DATABASE_URL": ""}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "DATABASE_URL is required" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_sqlite_database_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "DATABASE_URL": "sqlite:///./app.db"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "SQLite is not permitted" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_localhost_database_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "DATABASE_URL": "postgresql://user:pass@localhost:5432/db"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "localhost" in str(exc_info.value).lower()

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_default_db_user_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "DATABASE_URL": "postgresql://postgres:pass@db.internal:5432/db"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "default/weak account" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_superuser_db_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "DATABASE_URL": "postgresql://rdsadmin:pass@db.internal:5432/db"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "superuser" in str(exc_info.value).lower()

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_mock_persistence_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "MOCK_PERSISTENCE": "true"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "MOCK_PERSISTENCE" in str(exc_info.value)

    # --- Encryption ------------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_missing_master_key_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "CREDENTIALS_MASTER_KEY": ""}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "CREDENTIALS_MASTER_KEY is required" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_ephemeral_encryption_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "ALLOW_EPHEMERAL_ENCRYPTION": "true"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "ALLOW_EPHEMERAL_ENCRYPTION" in str(exc_info.value)

    # --- API Keys --------------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_missing_api_key_hmac_secret_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "API_KEY_HMAC_SECRET": ""}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "API_KEY_HMAC_SECRET is required" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_weak_api_key_hmac_secret_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "API_KEY_HMAC_SECRET": "short"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "API_KEY_HMAC_SECRET is too short" in str(exc_info.value)

    # --- CORS Origins ----------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_missing_cors_origins_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "CORS_ORIGINS": ""}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "CORS_ORIGINS is required" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_wildcard_cors_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "CORS_ORIGINS": "*"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "wildcard" in str(exc_info.value).lower()

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_http_cors_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "CORS_ORIGINS": "http://app.example.com"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "HTTPS" in str(exc_info.value)

    # --- Tenant Isolation ------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_missing_default_tenant_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "DEFAULT_TENANT_ID": ""}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "DEFAULT_TENANT_ID is required" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_literal_default_tenant_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "DEFAULT_TENANT_ID": "default"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "literal value 'default'" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_invalid_uuid_tenant_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "DEFAULT_TENANT_ID": "not-a-uuid"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "not a valid UUID" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_missing_service_auth_secret_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "SERVICE_AUTH_SECRET": ""}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "SERVICE_AUTH_SECRET is required" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_disabled_multi_tenant_mode_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "MULTI_TENANT_MODE": "false"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "MULTI_TENANT_MODE" in str(exc_info.value)

    # --- External Providers ----------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_mock_llm_provider_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "LLM_PROVIDER": "mock"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "mock" in str(exc_info.value).lower()

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_allow_mock_llm_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "ALLOW_MOCK_LLM": "true"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "ALLOW_MOCK_LLM" in str(exc_info.value)

    # --- Debug Flags -----------------------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_debug_true_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "DEBUG": "true"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "DEBUG" in str(exc_info.value)

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS)
    def test_seed_demo_data_fails_in_production_like(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "SEED_DEMO_DATA": "true"}
        with pytest.raises(RuntimeError) as exc_info:
            self._run_validation(env)
        assert "SEED_DEMO_DATA" in str(exc_info.value)

    # --- Valid configuration passes --------------------------------------

    @pytest.mark.parametrize("environment", PRODUCTION_LIKE_ENVS + DEV_ENVS)
    def test_valid_configuration_passes(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment}
        self._run_validation(env)

    # --- Development allows relaxed config -------------------------------

    @pytest.mark.parametrize("environment", DEV_ENVS)
    def test_development_allows_sqlite(self, environment: str) -> None:
        env = {
            **_VALID_PROD_ENV,
            "ENVIRONMENT": environment,
            "DATABASE_URL": "sqlite:///./dev.db",
            "JWT_SECRET": "a" * 48,
        }
        self._run_validation(env)

    @pytest.mark.parametrize("environment", DEV_ENVS)
    def test_development_allows_wildcard_cors(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "CORS_ORIGINS": "*"}
        self._run_validation(env)

    @pytest.mark.parametrize("environment", DEV_ENVS)
    def test_development_allows_mock_llm(self, environment: str) -> None:
        env = {**_VALID_PROD_ENV, "ENVIRONMENT": environment, "LLM_PROVIDER": "mock"}
        self._run_validation(env)


# ---------------------------------------------------------------------------
# Accumulated errors
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAccumulatedErrors:
    def test_all_errors_are_reported_together(self) -> None:
        """Every misconfiguration must be listed so operators can fix them all at once."""
        bad_env = _env(
            ENVIRONMENT="production",
            JWT_SECRET="short",
            DATABASE_URL="sqlite:///./app.db",
            CREDENTIALS_MASTER_KEY="",
            API_KEY_HMAC_SECRET="",
            CORS_ORIGINS="*",
            DEFAULT_TENANT_ID="default",
            SERVICE_AUTH_SECRET="",
            LLM_PROVIDER="mock",
            DEBUG="true",
            ALLOW_INSECURE_DEV_AUTH_BYPASS="true",
        )
        with patch.dict(os.environ, bad_env, clear=True):
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
# Validator class direct usage
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestProductionSafetyValidatorDirectly:
    def test_validator_exposes_environment_and_production_like(self) -> None:
        validator_staging = ProductionSafetyValidator(environment="staging")
        assert validator_staging.environment == "staging"
        assert validator_staging.is_strict is True
        assert validator_staging.is_production_like is False

        validator_prod = ProductionSafetyValidator(environment="production")
        assert validator_prod.environment == "production"
        assert validator_prod.is_strict is True
        assert validator_prod.is_production_like is True

    def test_validator_clears_errors_after_dev_warning(self) -> None:
        """In dev mode, errors are converted to warnings and the internal list is cleared."""
        env = {
            **_VALID_PROD_ENV,
            "ENVIRONMENT": "development",
            "JWT_SECRET": "",
        }
        with patch.dict(os.environ, env, clear=True):
            validator = ProductionSafetyValidator()
            validator.validate()
            assert validator.errors == []
