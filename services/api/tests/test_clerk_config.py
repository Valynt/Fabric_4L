"""Tests for the auth provider configuration module.

Covers the default provider selection, legacy mode selection, and the key
validation gate for Clerk mode.
"""
from __future__ import annotations

import json
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.clerk_config import (
    AUTH_PROVIDER_CLERK,
    get_auth_settings,
    reset_auth_settings_cache,
)


def _generate_test_keys() -> tuple[str, str]:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


@pytest.fixture
def clerk_env_keys(monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    private_pem, public_pem = _generate_test_keys()
    monkeypatch.setenv("FABRIC_AUTH_SIGNING_KEY", private_pem)
    monkeypatch.setenv("FABRIC_AUTH_SIGNING_KID", "test-kid")
    monkeypatch.setenv(
        "FABRIC_AUTH_PUBLIC_KEYS",
        json.dumps([{"kid": "test-kid", "public_pem": public_pem}]),
    )
    return private_pem, public_pem


@pytest.fixture(autouse=True)
def _clear_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove auth env vars that could leak between tests."""
    for name in (
        "AUTH_PROVIDER",
        "CLERK_ISSUER",
        "CLERK_JWT_AUDIENCE",
        "CLERK_JWKS_URL",
        "CLERK_PINNED_JWT_PEM",
        "FABRIC_AUTH_SIGNING_KEY",
        "FABRIC_AUTH_SIGNING_PRIVATE_KEY",
        "FABRIC_AUTH_SIGNING_KID",
        "FABRIC_AUTH_PUBLIC_KEYS",
        "FABRIC_AUTH_VERIFYING_PUBLIC_KEY",
        "FABRIC_AUTH_ISSUER",
        "FABRIC_AUTH_AUDIENCE",
        "FABRIC_AUTH_ENVELOPE_TTL_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    reset_auth_settings_cache()


def _set_required_clerk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLERK_ISSUER", "https://accounts.example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "fabric4l-api")
    monkeypatch.setenv(
        "CLERK_JWKS_URL",
        "https://accounts.example.clerk.accounts.dev/.well-known/jwks.json",
    )


def test_default_provider_is_clerk(
    monkeypatch: pytest.MonkeyPatch, clerk_env_keys: tuple[str, str]
) -> None:
    _set_required_clerk_env(monkeypatch)
    settings = get_auth_settings()
    assert settings.provider == AUTH_PROVIDER_CLERK


def test_legacy_provider_is_selectable(clerk_env_keys: tuple[str, str]) -> None:
    os.environ["AUTH_PROVIDER"] = "layer4"
    reset_auth_settings_cache()
    settings = get_auth_settings()
    assert settings.provider == "layer4"


def test_clerk_mode_requires_jwt_verification_settings(clerk_env_keys: tuple[str, str]) -> None:
    os.environ["AUTH_PROVIDER"] = "clerk"
    reset_auth_settings_cache()
    with pytest.raises(ValueError, match="CLERK_ISSUER"):
        get_auth_settings()


def test_clerk_mode_requires_envelope_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_clerk_env(monkeypatch)
    monkeypatch.setenv("AUTH_PROVIDER", "clerk")
    reset_auth_settings_cache()
    with pytest.raises(ValueError, match="FABRIC_AUTH_SIGNING_KEY"):
        get_auth_settings()


def test_reset_auth_settings_cache_picks_up_env_changes(
    monkeypatch: pytest.MonkeyPatch, clerk_env_keys: tuple[str, str]
) -> None:
    _set_required_clerk_env(monkeypatch)
    os.environ["AUTH_PROVIDER"] = "layer4"
    reset_auth_settings_cache()
    assert get_auth_settings().provider == "layer4"

    os.environ["AUTH_PROVIDER"] = "clerk"
    reset_auth_settings_cache()
    assert get_auth_settings().provider == "clerk"


def test_envelope_settings_load_canonical_runtime_fields(
    monkeypatch: pytest.MonkeyPatch, clerk_env_keys: tuple[str, str]
) -> None:
    _set_required_clerk_env(monkeypatch)
    monkeypatch.setenv("FABRIC_AUTH_ISSUER", "gateway-test")
    monkeypatch.setenv("FABRIC_AUTH_AUDIENCE", "internal-test")
    monkeypatch.setenv("FABRIC_AUTH_ENVELOPE_TTL_SECONDS", "120")

    settings = get_auth_settings()

    assert settings.envelope is not None
    assert settings.envelope.signing_key is not None
    assert settings.envelope.signing_key.kid == "test-kid"
    assert settings.envelope.verification_keys is not None
    assert settings.envelope.verification_keys.kids() == ["test-kid"]
    assert settings.envelope.issuer == "gateway-test"
    assert settings.envelope.audience == "internal-test"
    assert settings.envelope.envelope_ttl_seconds == 120


def test_legacy_envelope_aliases_still_load(monkeypatch: pytest.MonkeyPatch) -> None:
    private_pem, public_pem = _generate_test_keys()
    _set_required_clerk_env(monkeypatch)
    monkeypatch.setenv("FABRIC_AUTH_SIGNING_PRIVATE_KEY", private_pem)
    monkeypatch.setenv("FABRIC_AUTH_SIGNING_KID", "legacy-kid")
    monkeypatch.setenv("FABRIC_AUTH_VERIFYING_PUBLIC_KEY", public_pem)

    settings = get_auth_settings()

    assert settings.envelope is not None
    assert settings.envelope.signing_key is not None
    assert settings.envelope.signing_key.kid == "legacy-kid"
    assert settings.envelope.verification_keys is not None
    assert settings.envelope.verification_keys.kids() == ["legacy-kid"]
