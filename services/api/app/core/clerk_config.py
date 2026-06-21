"""Clerk gateway configuration with signed internal-envelope support.

Provides a cached ``AuthSettings`` aggregate that is used by the API gateway
when ``AUTH_PROVIDER=clerk`` is selected. The internal envelope is signed by
a configured Ed25519 key pair so that Clerk-issued JWTs can be re-wrapped into
a fabric-internal token that downstream layers trust.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


@dataclass(frozen=True)
class ClerkSettings:
    """Clerk-specific configuration."""

    issuer: str | None = None
    jwt_audience: str | None = None
    authorized_parties: tuple[str, ...] | None = None
    jwks_url: str | None = None
    pinned_jwt_pem: str | None = None
    webhook_secret: str | None = None
    secret_key: str | None = None
    publishable_key: str | None = None


@dataclass(frozen=True)
class SigningKey:
    """Configured internal-envelope signing key."""

    kid: str
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey


@dataclass(frozen=True)
class VerificationKeys:
    """Public keys used to verify internal-envelope tokens."""

    keys: dict[str, Ed25519PublicKey]

    def kids(self) -> list[str]:
        """Return the configured key IDs."""
        return list(self.keys.keys())


@dataclass(frozen=True)
class InternalEnvelope:
    """Internal JWT envelope configuration."""

    signing_key: SigningKey | None = None
    verification_keys: VerificationKeys | None = None


@dataclass(frozen=True)
class AuthSettings:
    """Aggregated auth provider settings returned by ``get_auth_settings``."""

    provider: str
    clerk: ClerkSettings | None = None
    envelope: InternalEnvelope | None = None


# Canonical provider identifiers for the auth layer.
AUTH_PROVIDER_CLERK = "clerk"


def _load_signing_key(pem: str, kid: str) -> SigningKey:
    private_key = serialization.load_pem_private_key(pem.encode(), password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("FABRIC_AUTH_SIGNING_KEY must be an Ed25519 private key")
    return SigningKey(
        kid=kid,
        private_key=private_key,
        public_key=private_key.public_key(),
    )


def _load_verification_keys(raw: str) -> VerificationKeys:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("FABRIC_AUTH_PUBLIC_KEYS must be valid JSON") from exc

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("FABRIC_AUTH_PUBLIC_KEYS must be a JSON list or object")

    keys: dict[str, Ed25519PublicKey] = {}
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("Each FABRIC_AUTH_PUBLIC_KEYS entry must be an object")
        kid = entry.get("kid")
        public_pem = entry.get("public_pem")
        if not kid or not public_pem:
            raise ValueError("FABRIC_AUTH_PUBLIC_KEYS entries must include 'kid' and 'public_pem'")
        public_key = serialization.load_pem_public_key(public_pem.encode())
        if not isinstance(public_key, Ed25519PublicKey):
            raise ValueError("FABRIC_AUTH_PUBLIC_KEYS must contain Ed25519 public keys")
        keys[kid] = public_key

    return VerificationKeys(keys=keys)


@lru_cache(maxsize=1)
def get_auth_settings() -> AuthSettings:
    """Return auth provider settings, loaded from environment and cached."""
    provider = os.getenv("AUTH_PROVIDER", "clerk").strip().lower()
    clerk_settings = ClerkSettings(
        issuer=os.getenv("CLERK_ISSUER") or None,
        jwt_audience=os.getenv("CLERK_JWT_AUDIENCE") or None,
        authorized_parties=_parse_authorized_parties(
            os.getenv("CLERK_AUTHORIZED_PARTIES", "")
        ),
        jwks_url=os.getenv("CLERK_JWKS_URL") or None,
        pinned_jwt_pem=os.getenv("CLERK_PINNED_JWT_PEM") or None,
        webhook_secret=os.getenv("CLERK_WEBHOOK_SECRET") or None,
        secret_key=os.getenv("CLERK_SECRET_KEY") or None,
        publishable_key=os.getenv("CLERK_PUBLISHABLE_KEY") or None,
    )

    signing_key_pem = os.getenv("FABRIC_AUTH_SIGNING_KEY", "").strip() or None
    signing_kid = os.getenv("FABRIC_AUTH_SIGNING_KID", "").strip() or None
    public_keys_raw = os.getenv("FABRIC_AUTH_PUBLIC_KEYS", "").strip() or None

    if provider == "clerk":
        if not signing_key_pem or not signing_kid or not public_keys_raw:
            raise ValueError(
                "AUTH_PROVIDER=clerk requires FABRIC_AUTH_SIGNING_KEY, "
                "FABRIC_AUTH_SIGNING_KID, and FABRIC_AUTH_PUBLIC_KEYS to be set."
            )

    envelope: InternalEnvelope | None = None
    if signing_key_pem and signing_kid and public_keys_raw:
        envelope = InternalEnvelope(
            signing_key=_load_signing_key(signing_key_pem, signing_kid),
            verification_keys=_load_verification_keys(public_keys_raw),
        )

    return AuthSettings(
        provider=provider,
        clerk=clerk_settings,
        envelope=envelope,
    )


def _parse_authorized_parties(raw: str) -> tuple[str, ...] | None:
    if not raw.strip():
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def reset_auth_settings_cache() -> None:
    """Clear cached auth settings so env changes are picked up."""
    get_auth_settings.cache_clear()
