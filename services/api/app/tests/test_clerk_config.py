"""Regression coverage for Clerk gateway configuration hardening."""

from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.clerk_config import get_auth_settings, reset_auth_settings_cache


def _ed25519_keypair() -> tuple[str, str]:
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture(autouse=True)
def clear_auth_settings_cache() -> None:
    reset_auth_settings_cache()
    yield
    reset_auth_settings_cache()


def test_clerk_provider_requires_gateway_and_fabric_envelope_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_PROVIDER", "clerk")
    monkeypatch.setenv("CLERK_ISSUER", "https://accounts.example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "fabric4l-api")
    monkeypatch.delenv("FABRIC_AUTH_PUBLIC_KEYS", raising=False)
    monkeypatch.delenv("FABRIC_AUTH_SIGNING_KEY", raising=False)
    monkeypatch.delenv("FABRIC_AUTH_SIGNING_KID", raising=False)

    with pytest.raises(ValueError, match="AUTH_PROVIDER=clerk requires"):
        get_auth_settings()


def test_clerk_provider_loads_with_signed_internal_envelope_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_pem, public_pem = _ed25519_keypair()
    monkeypatch.setenv("AUTH_PROVIDER", "clerk")
    monkeypatch.setenv("CLERK_ISSUER", "https://accounts.example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "fabric4l-api")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "https://www.valuepact.ai,https://app.valuepact.ai")
    monkeypatch.setenv("FABRIC_AUTH_SIGNING_KEY", private_pem)
    monkeypatch.setenv("FABRIC_AUTH_SIGNING_KID", "gateway-k1")
    monkeypatch.setenv(
        "FABRIC_AUTH_PUBLIC_KEYS",
        json.dumps([{"kid": "gateway-k1", "public_pem": public_pem}]),
    )

    settings = get_auth_settings()

    assert settings.provider == "clerk"
    assert settings.clerk is not None
    assert settings.clerk.issuer == "https://accounts.example.clerk.accounts.dev"
    assert settings.clerk.jwt_audience == "fabric4l-api"
    assert settings.clerk.authorized_parties == (
        "https://www.valuepact.ai",
        "https://app.valuepact.ai",
    )
    assert settings.envelope is not None
    assert settings.envelope.signing_key is not None
    assert settings.envelope.verification_keys.kids() == ["gateway-k1"]
