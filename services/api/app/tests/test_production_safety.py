import importlib

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_require_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError, match=r"secret_key\s+Field required"):
        Settings(_env_file=None)


def test_settings_keep_legacy_per_layer_timeout_fields():
    # The layer{1,2,3,5}_timeout_seconds fields must remain on Settings:
    # app/clients/layer{1,2,3,5}_client.py read them at construction time
    # (review finding F-1). L1/L2 keep their 30s defaults — crawling and
    # LLM extraction legitimately exceed 10s; the delegation router uses
    # delegation_timeout_seconds instead.
    settings = Settings()
    assert settings.layer1_timeout_seconds == 30.0
    assert settings.layer2_timeout_seconds == 30.0
    assert settings.layer3_timeout_seconds == 10.0
    assert settings.layer5_timeout_seconds == 10.0


def test_production_like_environment_rejects_mock_persistence_and_mock_llm():
    with pytest.raises(Exception, match="Unsafe production configuration"):
        Settings(
            app_env="production",
            mock_persistence=True,
            database_url=None,
            llm_provider="layer4",
            seed_demo_data=True,
            secret_key="x" * 48,
            cors_origins=["*"],
        )


def test_production_like_environment_rejects_sqlite_durable_configuration():
    with pytest.raises(Exception, match="SQLite is not supported"):
        Settings(
            app_env="production",
            mock_persistence=False,
            database_url="sqlite:////var/lib/fabric_4l/api.db",
            llm_provider="layer4",
            seed_demo_data=False,
            secret_key="x" * 48,
            cors_origins=["https://app.example.com"],
        )


def test_production_like_environment_accepts_postgres_with_rls_facade():
    settings = Settings(
        app_env="production",
        mock_persistence=False,
        database_url="postgresql://fabric:secret@postgres:5432/fabric",
        llm_provider="layer4",
        algorithm="RS256",
        seed_demo_data=False,
        secret_key="x" * 48,
        cors_origins=["https://app.example.com"],
    )
    assert settings.database_url is not None
    assert not settings.mock_persistence


def test_database_factory_accepts_postgresql_in_development(monkeypatch, tmp_path):
    """PostgreSQL async engine is now supported; facade is returned for router compatibility."""
    monkeypatch.setenv("APP_ENV", "development")
    database = importlib.import_module("app.core.database")

    safe_dev_settings = Settings(
        app_env="development",
        mock_persistence=False,
        database_url="postgresql://fabric:example@localhost:5432/fabric",
        llm_provider="mock",
        seed_demo_data=False,
        secret_key="x" * 48,
    )
    monkeypatch.setattr(database, "get_settings", lambda: safe_dev_settings)

    db = database.create_database()
    assert isinstance(db, (database.InMemoryDatabase, database.PostgreSQLDatabase))


def test_unknown_environment_is_not_production_like_and_allows_dev_defaults():
    """Unknown environments are no longer treated as production-like (explicit allowlist)."""
    settings = Settings(
        app_env="qa",
        mock_persistence=False,
        database_url="postgresql://fabric:secret@postgres:5432/fabric",
        llm_provider="openai",
        seed_demo_data=False,
        secret_key="x" * 48,
        cors_origins=["https://app.example.com"],
    )
    # qa is NOT production-like, so settings are accepted without production validation
    assert settings.is_production_like is False
    assert settings.cors_policy["allow_origins"] == ["https://app.example.com"]


def test_production_like_environment_rejects_placeholder_and_wildcard_cors():
    with pytest.raises(Exception, match="Unsafe production configuration") as exc_info:
        Settings(
            app_env="production",
            mock_persistence=False,
            database_url="postgresql://fabric:secret@postgres:5432/fabric",
            llm_provider="layer4",
            algorithm="RS256",
            seed_demo_data=False,
            secret_key="x" * 48,
            cors_origins=["https://*.example.com", "CHANGE_ME"],
        )

    message = str(exc_info.value)
    assert "wildcard" in message.lower()
    assert "deployable origin" in message


def test_standalone_api_cors_policy_is_explicit_and_credentials_safe():
    settings = Settings(
        app_env="development",
        mock_persistence=False,
        database_url="postgresql://fabric:secret@postgres:5432/fabric",
        llm_provider="openai",
        seed_demo_data=False,
        secret_key="x" * 48,
        cors_origins=["https://app.example.com"],
    )

    assert settings.cors_policy == {
        "allow_origins": ["https://app.example.com"],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID"],
    }
