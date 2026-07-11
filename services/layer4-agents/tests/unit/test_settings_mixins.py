"""Regression tests for Settings mixin behavior."""

import pytest

from layer4_agents.config.settings import Settings


@pytest.fixture(autouse=True)
def _production_settings_env(monkeypatch):
    """Provide production-safe defaults for env vars that conftest sets to development values.

    The global Layer 4 conftest sets HTTP layer endpoints so that collection-time
    imports succeed. Tests that instantiate Settings with environment="production"
    need production-valid HTTPS endpoints and a database URL to avoid validation
    failures unrelated to the mixin behavior under test.
    """
    monkeypatch.setenv(
        "LAYER4_DATABASE_URL",
        "postgresql://layer4:strong-password@db.example.com:5432/layer4",
    )
    monkeypatch.setenv("LAYER4_LAYER1_API_URL", "https://layer1.internal.valuefabric.local")
    monkeypatch.setenv("LAYER4_LAYER2_API_URL", "https://layer2.internal.valuefabric.local")
    monkeypatch.setenv("LAYER4_LAYER3_API_URL", "https://layer3.internal.valuefabric.local")
    monkeypatch.setenv("LAYER4_LAYER5_API_URL", "https://layer5.internal.valuefabric.local")
    monkeypatch.setenv(
        "LAYER4_NEO4J_URI",
        "neo4j+s://example.databases.neo4j.io",
    )
    monkeypatch.setenv("LAYER4_NEO4J_PASSWORD", "strong-neo4j-password")


class TestBillingSettingsMixin:
    def test_is_billing_configured_when_enabled_and_secret_present(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            billing_enabled=True,
            stripe_secret_key="sk_test_xxx",
        )
        assert settings.is_billing_configured is True

    def test_is_billing_configured_false_when_disabled(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            billing_enabled=False,
            stripe_secret_key="sk_test_xxx",
        )
        assert settings.is_billing_configured is False

    def test_is_billing_configured_false_when_secret_missing(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            billing_enabled=True,
            stripe_secret_key=None,
        )
        assert settings.is_billing_configured is False


class TestRuntimeSettingsMixin:
    def test_is_production(self):
        settings = Settings(
            environment="production",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            cors_origins="https://app.example.com",
        )
        assert settings.is_production is True
        assert settings.is_development is False

    def test_is_development(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
        )
        assert settings.is_development is True
        assert settings.is_production is False

    def test_cors_origins_list_returns_wildcard_in_development(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
        )
        assert settings.cors_origins_list == ["*"]

    def test_cors_origins_list_parses_explicit_origins(self):
        settings = Settings(
            environment="production",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            cors_origins="https://a.example.com,https://b.example.com",
        )
        assert settings.cors_origins_list == [
            "https://a.example.com",
            "https://b.example.com",
        ]

    def test_cors_origins_list_rejects_wildcard_outside_development(self):
        settings = Settings(
            environment="staging",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            cors_origins="*",
        )
        with pytest.raises(ValueError, match="cannot contain '\\*' outside of development"):
            settings.cors_origins_list

    def test_cors_origins_list_strips_whitespace(self):
        settings = Settings(
            environment="production",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            cors_origins=" https://a.example.com , https://b.example.com ",
        )
        assert settings.cors_origins_list == [
            "https://a.example.com",
            "https://b.example.com",
        ]

    def test_cors_origins_list_returns_empty_in_non_development(self):
        settings = Settings(
            environment="staging",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
        )
        assert settings.cors_origins_list == []
