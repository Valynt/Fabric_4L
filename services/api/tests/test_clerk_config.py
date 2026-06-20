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
        "FABRIC_AUTH_SIGNING_KEY",
        "FABRIC_AUTH_SIGNING_KID",
        "FABRIC_AUTH_PUBLIC_KEYS",
    ):
        monkeypatch.delenv(name, raising=False)
    reset_auth_settings_cache()


def test_default_provider_is_clerk(clerk_env_keys: tuple[str, str]) -> None:
    settings = get_auth_settings()
    assert settings.provider == AUTH_PROVIDER_CLERK


def test_legacy_provider_is_selectable(clerk_env_keys: tuple[str, str]) -> None:
    os.environ["AUTH_PROVIDER"] = "layer4"
    reset_auth_settings_cache()
    settings = get_auth_settings()
    assert settings.provider == "layer4"


def test_clerk_mode_requires_envelope_keys() -> None:
    os.environ["AUTH_PROVIDER"] = "clerk"
    reset_auth_settings_cache()
    with pytest.raises(ValueError, match="AUTH_PROVIDER=clerk requires"):
        get_auth_settings()


def test_reset_auth_settings_cache_picks_up_env_changes(clerk_env_keys: tuple[str, str]) -> None:
    os.environ["AUTH_PROVIDER"] = "layer4"
    reset_auth_settings_cache()
    assert get_auth_settings().provider == "layer4"

    os.environ["AUTH_PROVIDER"] = "clerk"
    reset_auth_settings_cache()
    assert get_auth_settings().provider == "clerk"
