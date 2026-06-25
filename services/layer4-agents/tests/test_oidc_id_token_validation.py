from __future__ import annotations

"""Tests for canonical OIDCClient.verify_id_token with JWKS validation."""


from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from value_fabric.shared.identity.oidc import OIDCClient


def _rsa_keypair() -> tuple[rsa.RSAPrivateKey, dict[str, str]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()

    def _b64url_uint(value: int) -> str:
        import base64

        byte_length = (value.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).decode("ascii").rstrip("=")

    jwk = {
        "kty": "RSA",
        "kid": "kid-1",
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_uint(public_numbers.n),
        "e": _b64url_uint(public_numbers.e),
    }
    return private_key, jwk


def _build_token(private_key: rsa.RSAPrivateKey, issuer: str, audience: str, **claims_overrides):
    now = datetime.now(UTC)
    claims = {
        "sub": "user-123",
        "iss": issuer,
        "aud": audience,
        "iat": int((now - timedelta(seconds=5)).timestamp()),
        "nbf": int((now - timedelta(seconds=5)).timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    claims.update(claims_overrides)
    return pyjwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "kid-1"})


@pytest.fixture
async def oidc_client():
    client = OIDCClient()
    yield client
    await client._http.aclose()


@pytest.mark.asyncio
async def test_verify_id_token_invalid_signature(oidc_client: OIDCClient):
    priv1, jwk1 = _rsa_keypair()
    priv2, _ = _rsa_keypair()
    token = _build_token(priv2, "https://issuer.example.com", "client-123")

    # Pre-seed JWKS cache with the first public key
    from value_fabric.shared.identity.oidc import _JWKS_CACHE

    _JWKS_CACHE["https://issuer.example.com"] = {"jwks": {"keys": [jwk1]}, "fetched_at": datetime.now(UTC).timestamp()}

    with pytest.raises(pyjwt.InvalidSignatureError):
        await oidc_client.verify_id_token(token, issuer_url="https://issuer.example.com", client_id="client-123")

    del _JWKS_CACHE["https://issuer.example.com"]


@pytest.mark.asyncio
async def test_verify_id_token_wrong_issuer(oidc_client: OIDCClient):
    priv, jwk = _rsa_keypair()
    token = _build_token(priv, "https://other-issuer.example.com", "client-123")

    from value_fabric.shared.identity.oidc import _JWKS_CACHE

    _JWKS_CACHE["https://issuer.example.com"] = {"jwks": {"keys": [jwk]}, "fetched_at": datetime.now(UTC).timestamp()}

    with pytest.raises(pyjwt.InvalidTokenError, match="issuer"):
        await oidc_client.verify_id_token(token, issuer_url="https://issuer.example.com", client_id="client-123")

    del _JWKS_CACHE["https://issuer.example.com"]


@pytest.mark.asyncio
async def test_verify_id_token_wrong_audience(oidc_client: OIDCClient):
    priv, jwk = _rsa_keypair()
    token = _build_token(priv, "https://issuer.example.com", "wrong-client")

    from value_fabric.shared.identity.oidc import _JWKS_CACHE

    _JWKS_CACHE["https://issuer.example.com"] = {"jwks": {"keys": [jwk]}, "fetched_at": datetime.now(UTC).timestamp()}

    with pytest.raises(pyjwt.InvalidAudienceError):
        await oidc_client.verify_id_token(token, issuer_url="https://issuer.example.com", client_id="client-123")

    del _JWKS_CACHE["https://issuer.example.com"]


@pytest.mark.asyncio
async def test_verify_id_token_expired(oidc_client: OIDCClient):
    priv, jwk = _rsa_keypair()
    token = _build_token(
        priv,
        "https://issuer.example.com",
        "client-123",
        exp=int((datetime.now(UTC) - timedelta(minutes=10)).timestamp()),
    )

    from value_fabric.shared.identity.oidc import _JWKS_CACHE

    _JWKS_CACHE["https://issuer.example.com"] = {"jwks": {"keys": [jwk]}, "fetched_at": datetime.now(UTC).timestamp()}

    with pytest.raises(pyjwt.ExpiredSignatureError):
        await oidc_client.verify_id_token(token, issuer_url="https://issuer.example.com", client_id="client-123")

    del _JWKS_CACHE["https://issuer.example.com"]


@pytest.mark.asyncio
async def test_verify_id_token_malformed(oidc_client: OIDCClient):
    with pytest.raises(pyjwt.PyJWTError):
        await oidc_client.verify_id_token("not-a-jwt", issuer_url="https://issuer.example.com", client_id="client-123")


@pytest.mark.asyncio
async def test_verify_id_token_nonce_mismatch(oidc_client: OIDCClient):
    priv, jwk = _rsa_keypair()
    token = _build_token(priv, "https://issuer.example.com", "client-123", nonce="expected-nonce")

    from value_fabric.shared.identity.oidc import _JWKS_CACHE

    _JWKS_CACHE["https://issuer.example.com"] = {"jwks": {"keys": [jwk]}, "fetched_at": datetime.now(UTC).timestamp()}

    with pytest.raises(pyjwt.InvalidTokenError, match="nonce mismatch"):
        await oidc_client.verify_id_token(token, issuer_url="https://issuer.example.com", client_id="client-123", nonce="wrong-nonce")

    del _JWKS_CACHE["https://issuer.example.com"]


@pytest.mark.asyncio
async def test_verify_id_token_stale_iat_rejected(oidc_client: OIDCClient):
    priv, jwk = _rsa_keypair()
    now = datetime.now(UTC)
    token = _build_token(
        priv,
        "https://issuer.example.com",
        "client-123",
        iat=int((now - timedelta(minutes=15)).timestamp()),
    )

    from value_fabric.shared.identity.oidc import _JWKS_CACHE

    _JWKS_CACHE["https://issuer.example.com"] = {"jwks": {"keys": [jwk]}, "fetched_at": now.timestamp()}

    with pytest.raises(pyjwt.InvalidTokenError, match="iat is too old"):
        await oidc_client.verify_id_token(token, issuer_url="https://issuer.example.com", client_id="client-123", max_iat_age_seconds=600)

    del _JWKS_CACHE["https://issuer.example.com"]
