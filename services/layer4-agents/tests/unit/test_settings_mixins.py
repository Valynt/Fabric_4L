"""Regression tests for Settings mixin behavior."""

import pytest

from layer4_agents.config.settings import Settings


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
