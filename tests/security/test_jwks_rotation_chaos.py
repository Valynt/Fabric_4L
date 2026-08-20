from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from value_fabric.shared.identity.fabric_auth import (
    AuthContext,
    KeySet,
    SigningKey,
    VerificationKey,
    sign_envelope,
    verify_envelope,
)
from services.api.app.core.clerk_config import ClerkSettings
from services.api.app.core.clerk_verifier import (
    ClerkClaims,
    ClerkJWKSCache,
    ClerkTokenError,
    ClerkTokenExpired,
    ClerkVerifier,
)


def _generate_rsa_key_pair() -> tuple[rsa.RSAPrivateKey, str, dict]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    jwk_dict = json.loads(pyjwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    return private_key, public_pem, jwk_dict


def test_clerk_jwks_outage_resilience():
    """When JWKS endpoint goes down, cached keys continue serving requests."""
    priv_key, pub_pem, jwk_dict = _generate_rsa_key_pair()
    jwk_dict["kid"] = "clerk_k1"

    cache = ClerkJWKSCache(jwks_url="https://clerk.example.com/.well-known/jwks.json")
    
    # 1. Warm cache
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"keys": [jwk_dict]}
        key = cache.signing_key_for_kid("clerk_k1")
        assert key is not None

    # 2. Simulate JWKS outage (500 internal server error)
    with patch("httpx.Client.get") as mock_get:
        mock_get.side_effect = Exception("500 Internal Server Error / Network Timeout")
        
        # Stale cache read should NOT fail
        cache._fetched_at = 0.0  # Force stale
        key_during_outage = cache.signing_key_for_kid("clerk_k1")
        assert key_during_outage is not None


def test_clerk_jwks_mid_traffic_key_rotation():
    """Handles new key rotation dynamically when unknown kid arrives."""
    priv1, _, jwk1 = _generate_rsa_key_pair()
    jwk1["kid"] = "kid_old"

    priv2, _, jwk2 = _generate_rsa_key_pair()
    jwk2["kid"] = "kid_new"

    settings = ClerkSettings(
        issuer="https://clerk.example.com",
        jwt_audience="fabric4l-api",
        jwks_url="https://clerk.example.com/.well-known/jwks.json",
        authorized_parties=("http://localhost:3001",),
        leeway_seconds=10,
    )

    cache = ClerkJWKSCache(settings.jwks_url)
    
    # Initial state only has kid_old
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"keys": [jwk1]}
        verifier = ClerkVerifier(settings, jwks_cache=cache)

        # Issue token with kid_new
        now = int(time.time())
        token_new = pyjwt.encode(
            {
                "sub": "user_rotated",
                "iss": "https://clerk.example.com",
                "aud": "fabric4l-api",
                "azp": "http://localhost:3001",
                "iat": now,
                "nbf": now,
                "exp": now + 300,
                "org_id": "org_123",
                "org_role": "org:admin",
                "org_permissions": ["read", "write"],
            },
            priv2,
            algorithm="RS256",
            headers={"kid": "kid_new", "typ": "JWT"},
        )

        # On cache miss, force-refresh fetches kid_new
        mock_get.return_value.json.return_value = {"keys": [jwk1, jwk2]}
        claims = verifier.verify(token_new)
        assert claims.sub == "user_rotated"
        assert claims.org_id == "org_123"
        assert claims.org_role == "org:admin"


def test_clerk_clock_skew_leeway():
    """Tokens slightly in past (within leeway) pass validation."""
    priv_key, pub_pem, jwk_dict = _generate_rsa_key_pair()
    jwk_dict["kid"] = "clerk_skew_kid"

    settings = ClerkSettings(
        issuer="https://clerk.example.com",
        jwt_audience="fabric4l-api",
        jwks_url="https://clerk.example.com/.well-known/jwks.json",
        authorized_parties=("http://localhost:3001",),
        leeway_seconds=15,
    )

    cache = ClerkJWKSCache(settings.jwks_url)
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"keys": [jwk_dict]}
        verifier = ClerkVerifier(settings, jwks_cache=cache)

        now = int(time.time())
        token_skewed = pyjwt.encode(
            {
                "sub": "user_skew",
                "iss": "https://clerk.example.com",
                "aud": "fabric4l-api",
                "azp": "http://localhost:3001",
                "iat": now - 300,
                "nbf": now - 300,
                "exp": now - 5,
            },
            priv_key,
            algorithm="RS256",
            headers={"kid": "clerk_skew_kid", "typ": "JWT"},
        )

        claims = verifier.verify(token_skewed)
        assert claims.sub == "user_skew"


def test_ed25519_multi_kid_dual_key_rotation():
    """Verifies multi-kid KeySet enables zero-downtime Ed25519 gateway rotation."""
    # Key 1
    priv1 = ed25519.Ed25519PrivateKey.generate()
    priv1_pem = priv1.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    pub1_pem = priv1.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    # Key 2 (Rotated)
    priv2 = ed25519.Ed25519PrivateKey.generate()
    priv2_pem = priv2.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    pub2_pem = priv2.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    key_set = KeySet([
        VerificationKey(kid="gateway-k1", public_pem=pub1_pem),
        VerificationKey(kid="gateway-k2", public_pem=pub2_pem),
    ])

    now = int(time.time())
    
    # Token 1 signed with k1
    ctx1 = AuthContext(
        clerk_user_id="clerk_user_1",
        user_id="user_1",
        tenant_id="tenant_a",
        request_id="req_1",
        roles={"tenant_admin"},
        permissions={"*"},
        exp=now + 300,
        iat=now,
        nbf=now,
        iss="fabric4l-gateway",
        aud="fabric4l-internal",
        kid="gateway-k1",
    )
    tok1 = sign_envelope(ctx1, signing_key=SigningKey(kid="gateway-k1", private_pem=priv1_pem))

    # Token 2 signed with rotated key k2
    ctx2 = AuthContext(
        clerk_user_id="clerk_user_2",
        user_id="user_2",
        tenant_id="tenant_b",
        request_id="req_2",
        roles={"analyst"},
        permissions={"read"},
        exp=now + 300,
        iat=now,
        nbf=now,
        iss="fabric4l-gateway",
        aud="fabric4l-internal",
        kid="gateway-k2",
    )
    tok2 = sign_envelope(ctx2, signing_key=SigningKey(kid="gateway-k2", private_pem=priv2_pem))

    # Verify both tokens are accepted by the KeySet
    v_ctx1 = verify_envelope(tok1, key_set=key_set, now=now)
    v_ctx2 = verify_envelope(tok2, key_set=key_set, now=now)

    assert v_ctx1.user_id == "user_1"
    assert v_ctx1.kid == "gateway-k1"
    assert v_ctx2.user_id == "user_2"
    assert v_ctx2.kid == "gateway-k2"
