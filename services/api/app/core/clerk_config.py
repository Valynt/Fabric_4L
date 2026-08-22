"""Clerk gateway configuration with signed internal-envelope support.

Provides a cached ``AuthSettings`` aggregate that is used by the API gateway
when ``AUTH_PROVIDER=clerk`` is selected. The internal envelope is signed by
a configured Ed25519 key pair so that Clerk-issued JWTs can be re-wrapped into
a fabric-internal token that downstream layers trust.

Canonical Clerk defaults are loaded from the platform-contract JSON file so
frontend and backend cannot silently diverge.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from value_fabric.shared.identity.fabric_auth import KeySet, SigningKey, VerificationKey
from value_fabric.shared.identity.fabric_auth.context import DEFAULT_AUDIENCE, DEFAULT_ISSUER


def _load_clerk_defaults() -> dict[str, Any]:
    """Load the canonical Clerk defaults from the platform-contract JSON file."""
    marker_names = {".git", "package.json", "pnpm-workspace.yaml", "pnpm-lock.yaml"}
    start = Path(__file__).resolve()
    for parent in (start, *start.parents):
        if any((parent / marker).exists() for marker in marker_names):
            candidate = parent / "packages" / "platform-contract" / "src" / "clerk_defaults.json"
            if candidate.exists():
                return json.loads(candidate.read_text(encoding="utf-8")).get("clerk", {})
        candidate = parent / "packages" / "platform-contract" / "src" / "clerk_defaults.json"
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8")).get("clerk", {})
    return {}


_CLERK_DEFAULTS = _load_clerk_defaults()
_DEFAULT_CLERK_JWT_AUDIENCE = _CLERK_DEFAULTS.get("jwtAudience", "fabric4l-api")
_DEFAULT_CLERK_AUTHORIZED_PARTIES = tuple(_CLERK_DEFAULTS.get("authorizedParties", ["http://localhost:3001"]))
_DEFAULT_FABRIC_AUTH_SIGNING_KID = _CLERK_DEFAULTS.get("authSigningKid", "gateway-k1")
_DEFAULT_FABRIC_AUTH_ENVELOPE_TTL_SECONDS = int(_CLERK_DEFAULTS.get("authEnvelopeTtlSeconds", 300))
_DEFAULT_CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE = int(_CLERK_DEFAULTS.get("webhookRateLimitPerMinute", 30))


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
    leeway_seconds: int = 10


@dataclass(frozen=True)
class InternalEnvelopeSettings:
    """Internal JWT envelope configuration."""

    signing_key: SigningKey | None = None
    verification_keys: KeySet | None = None
    issuer: str = DEFAULT_ISSUER
    audience: str = DEFAULT_AUDIENCE
    envelope_ttl_seconds: int = 300


@dataclass(frozen=True)
class AuthSettings:
    """Aggregated auth provider settings returned by ``get_auth_settings``."""

    provider: str
    clerk: ClerkSettings | None = None
    envelope: InternalEnvelopeSettings | None = None


# Canonical provider identifiers for the auth layer.
AUTH_PROVIDER_CLERK = "clerk"


def _load_signing_key(pem: str, kid: str) -> SigningKey:
    private_key = serialization.load_pem_private_key(pem.encode(), password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        msg = "FABRIC_AUTH_SIGNING_KEY must be an Ed25519 private key"
        raise TypeError(msg)
    return SigningKey(kid=kid, private_pem=pem)


def _load_verification_keys(raw: str) -> KeySet:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = "FABRIC_AUTH_PUBLIC_KEYS must be valid JSON"
        raise ValueError(msg) from exc

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        msg = "FABRIC_AUTH_PUBLIC_KEYS must be a JSON list or object"
        raise TypeError(msg)

    keys: list[VerificationKey] = []
    for entry in data:
        if not isinstance(entry, dict):
            msg = "Each FABRIC_AUTH_PUBLIC_KEYS entry must be an object"
            raise TypeError(msg)
        kid = entry.get("kid")
        public_pem = entry.get("public_pem")
        if not kid or not public_pem:
            msg = "FABRIC_AUTH_PUBLIC_KEYS entries must include 'kid' and 'public_pem'"
            raise ValueError(msg)
        public_key = serialization.load_pem_public_key(public_pem.encode())
        if not isinstance(public_key, Ed25519PublicKey):
            msg = "FABRIC_AUTH_PUBLIC_KEYS must contain Ed25519 public keys"
            raise TypeError(msg)
        keys.append(VerificationKey(kid=str(kid), public_pem=str(public_pem)))

    return KeySet(keys)


@lru_cache(maxsize=1)
def get_auth_settings() -> AuthSettings:
    """Return auth provider settings, loaded from environment and cached."""
    provider = os.getenv("AUTH_PROVIDER", "clerk").strip().lower()
    leeway_raw = os.getenv("CLERK_JWT_LEEWAY_SECONDS", "10").strip()
    try:
        leeway_sec = max(0, min(60, int(leeway_raw)))
    except ValueError:
        leeway_sec = 10

    clerk_settings = ClerkSettings(
        issuer=os.getenv("CLERK_ISSUER") or None,
        jwt_audience=os.getenv("CLERK_JWT_AUDIENCE") or _DEFAULT_CLERK_JWT_AUDIENCE,
        authorized_parties=_parse_authorized_parties(
            os.getenv("CLERK_AUTHORIZED_PARTIES", "")
        ) or _DEFAULT_CLERK_AUTHORIZED_PARTIES,
        jwks_url=os.getenv("CLERK_JWKS_URL") or None,
        pinned_jwt_pem=os.getenv("CLERK_PINNED_JWT_PEM") or None,
        webhook_secret=os.getenv("CLERK_WEBHOOK_SECRET") or None,
        secret_key=os.getenv("CLERK_SECRET_KEY") or None,
        publishable_key=os.getenv("CLERK_PUBLISHABLE_KEY") or None,
        leeway_seconds=leeway_sec,
    )

    signing_key_pem = (
        os.getenv("FABRIC_AUTH_SIGNING_KEY", "").strip()
        or os.getenv("FABRIC_AUTH_SIGNING_PRIVATE_KEY", "").strip()
        or None
    )
    signing_kid = os.getenv("FABRIC_AUTH_SIGNING_KID", "").strip() or _DEFAULT_FABRIC_AUTH_SIGNING_KID
    public_keys_raw = os.getenv("FABRIC_AUTH_PUBLIC_KEYS", "").strip() or None
    legacy_public_key = os.getenv("FABRIC_AUTH_VERIFYING_PUBLIC_KEY", "").strip()
    if not public_keys_raw and legacy_public_key:
        public_keys_raw = json.dumps([{"kid": signing_kid, "public_pem": legacy_public_key}])

    if provider == "clerk":
        missing_clerk = []
        if not clerk_settings.issuer:
            missing_clerk.append("CLERK_ISSUER")
        if not clerk_settings.jwt_audience:
            missing_clerk.append("CLERK_JWT_AUDIENCE")
        if not (clerk_settings.jwks_url or clerk_settings.pinned_jwt_pem):
            missing_clerk.append("CLERK_JWKS_URL or CLERK_PINNED_JWT_PEM")
        if missing_clerk:
            raise ValueError(
                "AUTH_PROVIDER=clerk requires " + ", ".join(missing_clerk) + " to be set."
            )
        if not signing_key_pem or not public_keys_raw:
            msg = (
                "AUTH_PROVIDER=clerk requires FABRIC_AUTH_SIGNING_KEY, "
                "FABRIC_AUTH_PUBLIC_KEYS, and optionally FABRIC_AUTH_SIGNING_KID "
                "to be set."
            )
            raise ValueError(msg)

    envelope: InternalEnvelopeSettings | None = None
    if signing_key_pem and signing_kid and public_keys_raw:
        envelope = InternalEnvelopeSettings(
            signing_key=_load_signing_key(signing_key_pem, signing_kid),
            verification_keys=_load_verification_keys(public_keys_raw),
            issuer=os.getenv("FABRIC_AUTH_ISSUER", DEFAULT_ISSUER),
            audience=os.getenv("FABRIC_AUTH_AUDIENCE", DEFAULT_AUDIENCE),
            envelope_ttl_seconds=int(os.getenv("FABRIC_AUTH_ENVELOPE_TTL_SECONDS", str(_DEFAULT_FABRIC_AUTH_ENVELOPE_TTL_SECONDS))),
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
