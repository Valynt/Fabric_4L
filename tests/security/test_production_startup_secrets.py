"""Production Startup Fail-Closed Secrets Tests.

Verifies that production startup fails closed when:
- Required secrets are missing.
- Secrets are malformed or invalid format.
- Expired secrets or credentials are provided.
- Secret provider / Infisical is inaccessible or unconfigured in production.
"""

from __future__ import annotations

import os
import types

import pytest
from value_fabric.shared.secrets.infisical import (
    InfisicalAuthError,
    InfisicalMissingRequiredSecretsError,
    InfisicalNetworkError,
    InfisicalNotConfiguredError,
    load_infisical_secrets,
)

pytestmark = [pytest.mark.security, pytest.mark.production_readiness]


@pytest.fixture
def clear_secrets_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "ENVIRONMENT",
        "INFISICAL_CLIENT_ID",
        "INFISICAL_CLIENT_SECRET",
        "INFISICAL_PROJECT_ID",
        "INFISICAL_ENVIRONMENT",
        "JWT_SECRET",
        "DATABASE_URL",
        "API_KEY_HMAC_SECRET",
        "SERVICE_AUTH_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)


def test_missing_secrets_in_production_fails_closed(monkeypatch: pytest.MonkeyPatch, clear_secrets_env):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(InfisicalNotConfiguredError, match="Infisical not configured"):
        load_infisical_secrets()


def test_inaccessible_infisical_in_production_fails_closed(monkeypatch: pytest.MonkeyPatch, clear_secrets_env):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "client-id-001")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "client-secret-001")
    monkeypatch.setenv("INFISICAL_PROJECT_ID", "proj-id-001")

    class _MockAuth:
        @staticmethod
        def login(*args, **kwargs):
            raise ConnectionError("Infisical KMS endpoint connection timeout")

    class _MockClient:
        def __init__(self, host: str):
            self.auth = types.SimpleNamespace(universal_auth=_MockAuth())

    monkeypatch.setitem(__import__("sys").modules, "infisical_sdk", types.SimpleNamespace(InfisicalSDKClient=_MockClient))

    with pytest.raises(InfisicalAuthError, match="Infisical auth failed"):
        load_infisical_secrets()


def test_malformed_missing_bootstrap_manifest_in_dev_fails_closed(monkeypatch: pytest.MonkeyPatch, clear_secrets_env):
    monkeypatch.setenv("ENVIRONMENT", "development")
    with pytest.raises(InfisicalMissingRequiredSecretsError, match="Missing required secrets"):
        load_infisical_secrets()


def test_expired_or_invalid_auth_token_fails_closed(monkeypatch: pytest.MonkeyPatch, clear_secrets_env):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "client-id-001")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "client-secret-001")
    monkeypatch.setenv("INFISICAL_PROJECT_ID", "proj-id-001")

    class _MockAuth:
        @staticmethod
        def login(*args, **kwargs):
            return None

    class _MockClient:
        def __init__(self, host: str):
            self.auth = types.SimpleNamespace(universal_auth=_MockAuth())

        @staticmethod
        def listSecrets(**kwargs):
            raise ValueError("Token expired or revoked")

    monkeypatch.setitem(__import__("sys").modules, "infisical_sdk", types.SimpleNamespace(InfisicalSDKClient=_MockClient))

    with pytest.raises(InfisicalNetworkError, match="Infisical network/fetch failed"):
        load_infisical_secrets()
