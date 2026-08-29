"""AC#8: the pinned-PEM / mock-JWKS path must stay test-only and fail closed.

Guarantees asserted:
- A Clerk token signed by a "mock"/test key is rejected when the verifier's
  configured trust anchor is a real JWKS (no pinned PEM) -- the mock/pinned key
  is never a silent fallback, so it cannot authenticate in production-like
  environments.
- Even when a pinned PEM IS configured, a token signed by a different key is
  rejected (signature mismatch). The pinned path cannot be abused to accept an
  arbitrary mock key.
- A token whose kid does not resolve in the configured JWKS is rejected, not
  accepted.

These are unit-level hostile tests: no live Clerk is required. They mirror the
"no static/mock key in production" guarantee that ProductionSafetyValidator is
responsible for enforcing at the environment level.
"""
from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest
from app.core.clerk_config import ClerkSettings
from app.core.clerk_verifier import ClerkTokenError, ClerkVerifier
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://accounts.example.clerk.accounts.dev"
AUDIENCE = "fabric4l-api"


def _b64e(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode()


def _jwk_from_public_pem(public_pem: str) -> dict[str, str]:
    """Build a minimal RSA JWK for a public PEM (kid left to the caller)."""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    public_key = load_pem_public_key(public_pem.encode())
    numbers = public_key.public_numbers()
    return {
        "kty": "RSA",
        "alg": "RS256",
        "n": _b64e(numbers.n),
        "e": _b64e(numbers.e),
    }


def _rsa_keypair(tag: str) -> tuple[str, str, str]:
    """Return (kid, private_pem, public_pem) for an RSA key pair."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
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
    return tag, private_pem, public_pem


def _signed_jwt(kid: str, private_pem: str, *, sub: str = "user_1") -> str:
    now = int(datetime.now(UTC).timestamp())
    payload = {
        "sub": sub,
        "org_id": "org_1",
        "org_role": "org:admin",
        "org_permissions": [],
        "iat": now,
        "nbf": now,
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        "iss": ISSUER,
        "aud": AUDIENCE,
    }
    return pyjwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid, "alg": "RS256"})


def _stub_cache(kid_for_pem: dict[str, str]) -> _StubCache:
    """Return a network-free cache double resolving kids against preloaded keys."""
    return _StubCache(kid_for_pem=kid_for_pem)


class _StubCache:
    """Minimal ClerkJWKSCache double: no HTTP, no refresh, fail-closed on miss.

    ``kid_for_pem`` maps a real JWK kid to a public PEM so we can simulate a
    Clerk trust anchor that resolves a subset of kids. An unresolvable kid
    raises ClerkTokenError, exactly like a live JWKS that lacks the key.
    """

    def __init__(self, *, kid_for_pem: dict[str, str]) -> None:
        self._kid_for_pem = kid_for_pem

    def signing_key_for_kid(
        self, kid: str, *, force_refresh: bool = False
    ) -> pyjwt.algorithms.RSAAlgorithm:
        pem = self._kid_for_pem.get(kid)
        if pem is None:
            raise ClerkTokenError(log_detail=f"no JWKS entry for kid={kid!r}")
        return pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(_jwk_from_public_pem(pem)))

    def get_status(self) -> dict[str, str | int]:
        return {"status": "stub", "cached_keys_count": len(self._kid_for_pem)}


def _settings(*, pinned_jwt_pem: str | None) -> ClerkSettings:
    return ClerkSettings(
        issuer=ISSUER,
        jwt_audience=AUDIENCE,
        authorized_parties=None,
        jwks_url="https://example.invalid/clerk/jwks",
        pinned_jwt_pem=pinned_jwt_pem,
    )


def _verifier(*, pinned_jwt_pem: str | None, cache: _StubCache) -> ClerkVerifier:
    return ClerkVerifier(_settings(pinned_jwt_pem=pinned_jwt_pem), jwks_cache=cache)


def test_mock_key_cannot_authenticate_when_production_uses_real_jwks() -> None:
    """Without a pinned PEM, a token signed by a mock/test key is rejected.

    In production-like configuration the verifier resolves the signing key only
    from the real JWKS. A test/pinned key is never a silent fallback, so a JWT
    signed by it fails closed.
    """
    real_kid, _, real_public_pem = _rsa_keypair("clerk_real_k1")
    mock_kid, mock_private_pem, _ = _rsa_keypair("clerk_mock_k1")

    cache = _stub_cache(kid_for_pem={real_kid: real_public_pem})
    verifier = _verifier(pinned_jwt_pem=None, cache=cache)

    token = _signed_jwt(mock_kid, mock_private_pem)

    with pytest.raises(ClerkTokenError):
        verifier.verify(token)


def test_pinned_pem_rejects_tokens_signed_by_different_key() -> None:
    """When a pinned PEM is configured, a token from a different key is rejected."""
    _, _, pinned_public_pem = _rsa_keypair("clerk_pinned_k1")
    other_kid, other_private_pem, _ = _rsa_keypair("clerk_other_k1")

    cache = _stub_cache(kid_for_pem={})
    verifier = _verifier(pinned_jwt_pem=pinned_public_pem, cache=cache)

    token = _signed_jwt(other_kid, other_private_pem)

    with pytest.raises(ClerkTokenError):
        verifier.verify(token)


def test_unknown_kid_in_jwks_is_rejected_not_accepted() -> None:
    """A kid that does not resolve in the configured JWKS is rejected."""
    real_kid, _, real_public_pem = _rsa_keypair("clerk_real_k1")
    _, forged_private_pem, _ = _rsa_keypair("clerk_forged_k1")

    cache = _stub_cache(kid_for_pem={real_kid: real_public_pem})
    verifier = _verifier(pinned_jwt_pem=None, cache=cache)

    # Signed with the forged key but claims a kid equal to the real key: the
    # signature must still fail against the real key (kid alone is not trusted).
    token = _signed_jwt(real_kid, forged_private_pem)

    with pytest.raises(ClerkTokenError):
        verifier.verify(token)


def test_no_pinned_pem_and_empty_jwks_fails_closed() -> None:
    """An empty/absent JWKS rejects rather than opening a static fallback."""
    _, mock_private_pem, _ = _rsa_keypair("clerk_mock_k1")
    cache = _stub_cache(kid_for_pem={})
    verifier = _verifier(pinned_jwt_pem=None, cache=cache)

    token = _signed_jwt("clerk_mock_k1", mock_private_pem)

    with pytest.raises(ClerkTokenError):
        verifier.verify(token)



