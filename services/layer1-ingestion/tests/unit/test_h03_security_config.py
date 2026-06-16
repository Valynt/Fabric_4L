import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
LAYER1_SRC = REPO_ROOT / "services" / "layer1-ingestion" / "src"
SHARED_SRC = REPO_ROOT / "packages" / "shared" / "src"
if str(LAYER1_SRC) not in sys.path:
    sys.path.insert(0, str(LAYER1_SRC))
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))


def _load_config(monkeypatch, **env):
    for key in (
        "ENVIRONMENT",
        "ENV",
        "APP_ENV",
        "CORS_ORIGINS",
        "JWT_SECRET",
        "DATABASE_URL",
        "LAYER1_S3_ACCESS_KEY",
        "LAYER1_S3_SECRET_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    # S3/MinIO credentials are required (no hardcoded defaults). Provide safe test
    # defaults so the module-level settings instance can be imported; individual
    # tests override these values as needed.
    monkeypatch.setenv("LAYER1_S3_ACCESS_KEY", "test-access-key")
    monkeypatch.setenv("LAYER1_S3_SECRET_KEY", "test-secret-key")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    module = importlib.import_module("layer1_ingestion.shared.config")
    return importlib.reload(module)


def test_layer1_unknown_environment_is_not_production_like(monkeypatch):
    """Unknown environments are no longer treated as production-like (explicit allowlist)."""
    config = _load_config(monkeypatch, ENVIRONMENT="development")

    # 'qa' is NOT production-like, so dev defaults are accepted without error.
    # S3/MinIO credentials are required in every environment (no hardcoded defaults).
    settings = config.Settings(
        environment="qa",
        s3_access_key="qa-access-key",
        s3_secret_key="qa-secret-key",
    )
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.s3_access_key == "qa-access-key"


def test_layer1_rejects_wildcard_and_placeholder_cors_in_production_like_env(monkeypatch):
    config = _load_config(monkeypatch, ENVIRONMENT="development")

    with pytest.raises(Exception, match="Unsafe production configuration") as exc_info:
        config.Settings(
            environment="production",
            jwt_secret="x" * 48,
            database_url="postgresql://fabric:example@db.internal:5432/layer1",
            redis_url="rediss://redis.internal:6379/0",
            s3_endpoint="https://s3.internal",
            cors_origins=["https://*.example.com", "CHANGE_ME"],
            s3_access_key="custom_access_key",
            s3_secret_key="custom_secret_key",
        )

    message = str(exc_info.value)
    assert "Unsafe production configuration" in message


def test_layer1_cors_policy_uses_explicit_origins_methods_and_headers(monkeypatch):
    config = _load_config(monkeypatch, ENVIRONMENT="development")
    settings = config.Settings(
        environment="production",
        jwt_secret="x" * 48,
        database_url="postgresql://fabric:example@db.internal:5432/layer1",
        cors_origins=["https://app.example.com"],
        redis_url="rediss://redis.internal:6379/0",
        s3_endpoint="https://s3.internal",
        s3_access_key="custom_access_key",
        s3_secret_key="custom_secret_key",
    )

    assert settings.cors_policy == {
        "allow_origins": ["https://app.example.com"],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID"],
    }


def test_layer1_development_default_cors_is_localhost_not_wildcard(monkeypatch):
    config = _load_config(monkeypatch, ENVIRONMENT="development")
    settings = config.Settings(environment="development")

    assert settings.cors_policy["allow_origins"] == ["http://localhost:5173", "http://localhost:3000"]
    assert settings.cors_policy["allow_credentials"] is True
    assert "*" not in settings.cors_policy["allow_methods"]
    assert "*" not in settings.cors_policy["allow_headers"]


def test_layer1_rejects_insecure_dependency_defaults_in_production_like_env(monkeypatch):
    config = _load_config(monkeypatch, ENVIRONMENT="development")
    with pytest.raises(Exception, match="Unsafe production configuration") as exc_info:
        config.Settings(
            environment="production",
            jwt_secret="x" * 48,
            database_url="postgresql://fabric:strong-pass@db.internal:5432/layer1",
            cors_origins=["https://app.example.com"],
            s3_access_key="minioadmin",
            s3_secret_key="minioadmin",
        )

    message = str(exc_info.value)
    assert "REDIS_URL is using default localhost value" in message
    assert "default placeholder value 'minioadmin'" in message
    assert "cannot target localhost" in message


def test_layer1_rejects_missing_or_invalid_dependency_settings_in_production_like_env(monkeypatch):
    config = _load_config(monkeypatch, ENVIRONMENT="development")
    with pytest.raises(Exception, match="Unsafe production configuration") as exc_info:
        config.Settings(
            environment="production",
            jwt_secret="x" * 48,
            database_url="postgresql://fabric:strong-pass@db.internal:5432/layer1",
            cors_origins=["https://app.example.com"],
            redis_url="not-a-redis-url",
            s3_endpoint="",
            s3_access_key="",
            s3_secret_key="",
        )

    message = str(exc_info.value)
    assert "REDIS_URL is invalid for a production-like environment" in message
    assert "S3_ACCESS_KEY and S3_SECRET_KEY must be set" in message
    assert "S3_ENDPOINT is missing or invalid" in message


def test_layer1_allows_dev_test_defaults(monkeypatch):
    config = _load_config(monkeypatch, ENVIRONMENT="development")
    dev_settings = config.Settings(
        environment="development",
        s3_access_key="dev-access-key",
        s3_secret_key="dev-secret-key",
    )
    test_settings = config.Settings(
        environment="test",
        s3_access_key="test-access-key",
        s3_secret_key="test-secret-key",
    )
    assert dev_settings.redis_url == "redis://localhost:6379/0"
    assert test_settings.s3_access_key == "test-access-key"


def test_layer1_unknown_environment_allows_dev_defaults(monkeypatch):
    """Unknown environments are not production-like, so dev defaults are allowed."""
    config = _load_config(monkeypatch, ENVIRONMENT="development")
    settings = config.Settings(
        environment="qa-sandbox",
        jwt_secret="x" * 48,
        database_url="postgresql://fabric:strong-pass@db.internal:5432/layer1",
        cors_origins=["https://app.example.com"],
        s3_access_key="qa-access-key",
        s3_secret_key="qa-secret-key",
    )
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.s3_access_key == "qa-access-key"


def test_layer1_rejects_non_tls_storage_endpoint_unless_private_host_is_allowlisted(monkeypatch):
    config = _load_config(monkeypatch, ENVIRONMENT="development")

    with pytest.raises(Exception, match="Unsafe production configuration") as exc_info:
        config.Settings(
            environment="production",
            jwt_secret="x" * 48,
            database_url="postgresql://fabric:strong-pass@db.internal:5432/layer1",
            cors_origins=["https://app.example.com"],
            redis_url="rediss://redis.internal:6379/0",
            s3_endpoint="http://storage.svc.cluster.local",
            s3_access_key="custom_access_key",
            s3_secret_key="custom_secret_key",
        )

    assert "S3_ENDPOINT must use TLS (https)" in str(exc_info.value)


def test_layer1_allows_allowlisted_private_non_tls_storage_endpoint_in_production(monkeypatch):
    config = _load_config(monkeypatch, ENVIRONMENT="development")
    settings = config.Settings(
        environment="production",
        jwt_secret="x" * 48,
        database_url="postgresql://fabric:strong-pass@db.internal:5432/layer1",
        cors_origins=["https://app.example.com"],
        redis_url="rediss://redis.internal:6379/0",
        s3_endpoint="http://storage.svc.cluster.local",
        s3_access_key="custom_access_key",
        s3_secret_key="custom_secret_key",
        private_storage_endpoint_allowlist=["storage.svc.cluster.local"],
    )

    assert settings.s3_endpoint == "http://storage.svc.cluster.local"
