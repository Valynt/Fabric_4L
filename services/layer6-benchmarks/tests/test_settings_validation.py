import os
from unittest.mock import patch

import pytest
from layer6_benchmarks.settings import (
    Layer6Settings,
    get_layer6_settings,
    validate_layer6_startup_settings,
)
from pydantic import ValidationError


def _base_env() -> dict[str, str]:
    return {
        "ENVIRONMENT": "test",
        "AUTH_REQUIRED": "true",
        "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/fabric",
        "DATABASE_URL_SYNC": "postgresql+psycopg2://postgres:postgres@localhost:5432/fabric",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "fabric",
        "DB_USER": "postgres",
        "DB_PASSWORD": "postgres-strong-password",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "strong-password-123",
        "JWT_SECRET": "j" * 32,
        "API_KEY_HMAC_SECRET": "a" * 32,
        "SERVICE_AUTH_SECRET": "s" * 32,
        "LAYER3_API_KEY": "l3" * 8,
        "LAYER5_API_KEY": "l5" * 8,
        "PORT": "8006",
        "API_PORT": "8006",
        "API_HOST": "0.0.0.0",
        "LOG_LEVEL": "INFO",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_MAX_POOL_SIZE": "10",
        "LAYER6_SERVICE_NAME": "layer6-benchmarks",
        "LAYER6_VERSION": "test",
        "LAYER6_BUILD_SHA": "test-build",
    }


def test_missing_critical_secret_fails_validation() -> None:
    env = _base_env()
    env["JWT_SECRET"] = ""

    with pytest.raises(ValidationError):
        Layer6Settings.model_validate(env)


def test_short_service_auth_secret_fails_validation() -> None:
    env = _base_env()
    env["SERVICE_AUTH_SECRET"] = "too-short"

    with pytest.raises(ValidationError):
        Layer6Settings.model_validate(env)


def test_missing_database_url_sync_fails_validation() -> None:
    env = _base_env()
    env.pop("DATABASE_URL_SYNC")

    get_layer6_settings.cache_clear()
    try:
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError, match="DATABASE_URL_SYNC"):
                validate_layer6_startup_settings()
    finally:
        get_layer6_settings.cache_clear()


def test_production_database_sslmode_is_required() -> None:
    env = _base_env()
    env["ENVIRONMENT"] = "production"
    env["DATABASE_URL"] = "postgresql://postgres:postgres@db:5432/fabric"
    env["DATABASE_URL_SYNC"] = (
        "postgresql+psycopg2://postgres:postgres@db:5432/fabric?sslmode=require"
    )

    with pytest.raises(ValidationError, match="sslmode"):
        Layer6Settings.model_validate(env)


def test_production_database_url_sync_sslmode_is_required() -> None:
    env = _base_env()
    env["ENVIRONMENT"] = "production"
    env["DATABASE_URL"] = "postgresql://postgres:postgres@db:5432/fabric?sslmode=require"
    env["DATABASE_URL_SYNC"] = "postgresql+psycopg2://postgres:postgres@db:5432/fabric"

    with pytest.raises(ValidationError, match="DATABASE_URL_SYNC"):
        Layer6Settings.model_validate(env)


def test_production_neo4j_requires_tls_scheme() -> None:
    env = _base_env()
    env["ENVIRONMENT"] = "production"
    env["DATABASE_URL"] = "postgresql://postgres:postgres@db:5432/fabric?sslmode=require"
    env["DATABASE_URL_SYNC"] = (
        "postgresql+psycopg2://postgres:postgres@db:5432/fabric?sslmode=require"
    )
    env["NEO4J_URI"] = "bolt://neo4j:7687"

    with pytest.raises(ValidationError, match="NEO4J_URI"):
        Layer6Settings.model_validate(env)


def test_production_config_passes_with_secure_values() -> None:
    env = _base_env()
    env["ENVIRONMENT"] = "production"
    env["DATABASE_URL"] = "postgresql://postgres:postgres@db:5432/fabric?sslmode=verify-full"
    env["DATABASE_URL_SYNC"] = (
        "postgresql+psycopg2://postgres:postgres@db:5432/fabric?sslmode=verify-full"
    )
    env["NEO4J_URI"] = "neo4j+s://neo4j.example.com:7687"
    env["ALLOW_INSECURE_DEV_AUTH_BYPASS"] = "false"
    env["DEV_AUTH_BYPASS"] = "false"
    env["AUTH_BYPASS_ENABLED"] = "false"
    env["JWT_FALLBACK_TO_QUERY_PARAM"] = "false"
    env["ALLOW_EPHEMERAL_ENCRYPTION"] = "false"
    env["ALLOW_DEV_AUTH_BYPASS"] = ""

    settings = Layer6Settings.model_validate(env)

    assert settings.environment == "production"


@pytest.mark.parametrize(
    ("flag_name", "flag_value", "expected_match"),
    [
        ("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true", "ALLOW_INSECURE_DEV_AUTH_BYPASS"),
        # Legacy aliases are folded into ALLOW_INSECURE_DEV_AUTH_BYPASS before the
        # production check runs, so the error message names the canonical flag.
        ("DEV_AUTH_BYPASS", "true", "ALLOW_INSECURE_DEV_AUTH_BYPASS"),
        ("AUTH_BYPASS_ENABLED", "true", "ALLOW_INSECURE_DEV_AUTH_BYPASS"),
        ("JWT_FALLBACK_TO_QUERY_PARAM", "true", "JWT_FALLBACK_TO_QUERY_PARAM"),
        ("ALLOW_EPHEMERAL_ENCRYPTION", "true", "ALLOW_EPHEMERAL_ENCRYPTION"),
        ("ALLOW_DEV_AUTH_BYPASS", "I_UNDERSTAND_RISK", "ALLOW_INSECURE_DEV_AUTH_BYPASS"),
    ],
)
def test_production_rejects_bypass_flags(
    flag_name: str, flag_value: str, expected_match: str
) -> None:
    env = _base_env()
    env["ENVIRONMENT"] = "production"
    env["DATABASE_URL"] = "postgresql://postgres:postgres@db:5432/fabric?sslmode=verify-full"
    env["DATABASE_URL_SYNC"] = (
        "postgresql+psycopg2://postgres:postgres@db:5432/fabric?sslmode=verify-full"
    )
    env["NEO4J_URI"] = "neo4j+s://neo4j.example.com:7687"
    env[flag_name] = flag_value

    with pytest.raises(ValidationError, match=expected_match):
        Layer6Settings.model_validate(env)


def test_non_production_can_explicitly_enable_bypass_flag() -> None:
    env = _base_env()
    env["ENVIRONMENT"] = "test"
    env["ALLOW_INSECURE_DEV_AUTH_BYPASS"] = "true"

    settings = Layer6Settings.model_validate(env)

    assert settings.allow_insecure_dev_auth_bypass is True


def test_production_rejects_auth_required_false() -> None:
    env = _base_env()
    env["ENVIRONMENT"] = "production"
    env["AUTH_REQUIRED"] = "false"
    env["DATABASE_URL"] = "postgresql://postgres:postgres@db:5432/fabric?sslmode=verify-full"
    env["DATABASE_URL_SYNC"] = (
        "postgresql+psycopg2://postgres:postgres@db:5432/fabric?sslmode=verify-full"
    )
    env["NEO4J_URI"] = "neo4j+s://neo4j.example.com:7687"

    with pytest.raises(ValidationError, match="AUTH_REQUIRED"):
        Layer6Settings.model_validate(env)


def test_port_mismatch_is_rejected() -> None:
    env = _base_env()
    env["PORT"] = "8006"
    env["API_PORT"] = "9000"

    with pytest.raises(ValidationError, match="API_PORT and PORT must match"):
        Layer6Settings.model_validate(env)


def test_startup_validation_hook_fails_fast_for_missing_required_env() -> None:
    env = _base_env()
    env.pop("LAYER3_API_KEY")

    get_layer6_settings.cache_clear()
    try:
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError, match="LAYER3_API_KEY"):
                validate_layer6_startup_settings()
    finally:
        get_layer6_settings.cache_clear()


def test_log_level_uppercase_is_accepted() -> None:
    env = _base_env()
    env["LOG_LEVEL"] = "INFO"

    settings = Layer6Settings.model_validate(env)

    assert settings.log_level == "INFO"


def test_log_level_lowercase_is_normalized() -> None:
    env = _base_env()
    env["LOG_LEVEL"] = "info"

    settings = Layer6Settings.model_validate(env)

    assert settings.log_level == "INFO"
