from __future__ import annotations

import types

import pytest
from value_fabric.shared.secrets.infisical import (
    InfisicalAuthError,
    InfisicalMissingRequiredSecretsError,
    InfisicalNetworkError,
    InfisicalNotConfiguredError,
    load_infisical_secrets,
)


@pytest.fixture
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _set_required_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "x" * 64)
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:pw@db:5432/value?sslmode=require")
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "y" * 64)
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "z" * 64)


def test_production_not_configured_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(InfisicalNotConfiguredError):
        load_infisical_secrets()


def test_production_not_configured_with_manifest_present_still_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    _set_required_secrets(monkeypatch)
    with pytest.raises(InfisicalNotConfiguredError):
        load_infisical_secrets()


def test_development_missing_manifest_raises_manifest_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    with pytest.raises(InfisicalMissingRequiredSecretsError, match="JWT_SECRET"):
        load_infisical_secrets()


def test_production_auth_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "client")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("INFISICAL_PROJECT_ID", "proj")

    class _Auth:
        @staticmethod
        def login(*args, **kwargs):
            raise RuntimeError("bad creds")

    class _Client:
        def __init__(self, host: str):
            self.auth = types.SimpleNamespace(universal_auth=_Auth())

    monkeypatch.setitem(__import__("sys").modules, "infisical_sdk", types.SimpleNamespace(InfisicalSDKClient=_Client))

    with pytest.raises(InfisicalAuthError):
        load_infisical_secrets()


def test_production_fetch_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "client")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("INFISICAL_PROJECT_ID", "proj")

    class _Auth:
        @staticmethod
        def login(*args, **kwargs):
            return None

    class _Client:
        def __init__(self, host: str):
            self.auth = types.SimpleNamespace(universal_auth=_Auth())

        @staticmethod
        def listSecrets(**kwargs):
            raise RuntimeError("timeout")

    monkeypatch.setitem(__import__("sys").modules, "infisical_sdk", types.SimpleNamespace(InfisicalSDKClient=_Client))

    with pytest.raises(InfisicalNetworkError):
        load_infisical_secrets()
