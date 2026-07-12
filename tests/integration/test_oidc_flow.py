"""Integration tests for the OIDC authentication flow.

Uses respx to mock the IdP discovery, JWKS, and token endpoints so the full
OIDCClient path (discover → build_authorize_url → exchange_code → verify_id_token
→ map_role_from_claims) is exercised without a live Keycloak instance.

These tests validate:
- Happy path: full PKCE flow produces valid claims
- PKCE: code_challenge appears in authorize URL; code_verifier sent in token exchange
- Nonce mismatch → InvalidTokenError
- Expired id_token → ExpiredSignatureError
- Wrong audience → InvalidTokenError
- Wrong issuer → InvalidTokenError
- Stale iat → InvalidTokenError
- Role mapping: highest-privilege role selected from claims
- JWKS kid-miss triggers exactly one re-fetch

Note: auto_provision_users=False (user-not-found → 403) is a route-layer
concern tested in services/layer4-agents/tests/test_oidc.py, not here.
OIDCClient has no knowledge of provisioning policy.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import jwt as pyjwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from value_fabric.shared.identity.oidc import OIDCClient, map_role_from_claims
from value_fabric.shared.identity.oidc_config import OIDCProviderConfig

# ---------------------------------------------------------------------------
# Shared RSA key pair for the mock IdP
# ---------------------------------------------------------------------------

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()
_PRIVATE_PEM = _PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
_KID = "mock-idp-key-1"
_ISSUER = "https://mock-idp.example.com/realms/fabric"
_CLIENT_ID = "fabric-api"
_TENANT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

_DISCOVERY_URL = f"{_ISSUER}/.well-known/openid-configuration"
_JWKS_URI = f"{_ISSUER}/protocol/openid-connect/certs"
_TOKEN_ENDPOINT = f"{_ISSUER}/protocol/openid-connect/token"
_AUTH_ENDPOINT = f"{_ISSUER}/protocol/openid-connect/auth"


def _make_jwk() -> dict:
    from jwt.algorithms import RSAAlgorithm
    jwk = json.loads(RSAAlgorithm.to_jwk(_PUBLIC_KEY))
    jwk["kid"] = _KID
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    return jwk


def _make_id_token(
    *,
    nonce: str | None = "test-nonce",
    audience: str = _CLIENT_ID,
    issuer: str = _ISSUER,
    exp_offset: int = 300,
    iat_offset: int = -5,
    extra_claims: dict | None = None,
) -> str:
    now = datetime.now(UTC)
    claims: dict = {
        "sub": "user-001",
        "email": "user@example.com",
        "tenant_id": _TENANT_ID,
        "roles": ["analyst"],
        "iss": issuer,
        "aud": audience,
        "iat": int((now + timedelta(seconds=iat_offset)).timestamp()),
        "exp": int((now + timedelta(seconds=exp_offset)).timestamp()),
    }
    if nonce is not None:
        claims["nonce"] = nonce
    if extra_claims:
        claims.update(extra_claims)
    return pyjwt.encode(claims, _PRIVATE_PEM, algorithm="RS256", headers={"kid": _KID})


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


_DISCOVERY_RESPONSE = {
    "issuer": _ISSUER,
    "authorization_endpoint": _AUTH_ENDPOINT,
    "token_endpoint": _TOKEN_ENDPOINT,
    "jwks_uri": _JWKS_URI,
    "response_types_supported": ["code"],
    "subject_types_supported": ["public"],
    "id_token_signing_alg_values_supported": ["RS256"],
}

_JWKS_RESPONSE = {"keys": [_make_jwk()]}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def oidc_client():
    """OIDCClient with a fresh httpx.AsyncClient."""
    client = OIDCClient()
    yield client


@pytest.fixture
def oidc_config() -> OIDCProviderConfig:
    return OIDCProviderConfig(
        provider_name="mock-idp",
        issuer_url=_ISSUER,
        client_id=_CLIENT_ID,
        client_secret_ref=None,
        scopes=["openid", "email", "profile"],
        claim_mapping={"roles=analyst": "analyst", "roles=tenant_admin": "tenant_admin"},
        default_role="read_only",
        auto_provision_users=True,
        enabled=True,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_full_oidc_happy_path(oidc_client: OIDCClient, oidc_config: OIDCProviderConfig):
    """Full PKCE flow: discover → authorize URL → exchange code → verify id_token → claims."""
    nonce = "integration-test-nonce"
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")
    code_challenge = _pkce_challenge(code_verifier)
    state = "integration-test-state"
    redirect_uri = "https://app.example.com/callback"
    auth_code = "mock-auth-code-abc123"
    id_token = _make_id_token(nonce=nonce)

    # Mock discovery
    respx.get(_DISCOVERY_URL).mock(return_value=httpx.Response(200, json=_DISCOVERY_RESPONSE))
    # Mock JWKS
    respx.get(_JWKS_URI).mock(return_value=httpx.Response(200, json=_JWKS_RESPONSE))
    # Mock token exchange
    respx.post(_TOKEN_ENDPOINT).mock(return_value=httpx.Response(200, json={
        "access_token": "mock-access-token",
        "id_token": id_token,
        "token_type": "Bearer",
        "expires_in": 300,
    }))

    # Step 1: Discover
    metadata = await oidc_client.discover(oidc_config.issuer_url)
    assert metadata["authorization_endpoint"] == _AUTH_ENDPOINT
    assert metadata["token_endpoint"] == _TOKEN_ENDPOINT

    # Step 2: Build authorize URL with PKCE
    auth_url = oidc_client.build_authorize_url(
        metadata=metadata,
        client_id=oidc_config.client_id,
        redirect_uri=redirect_uri,
        state=state,
        nonce=nonce,
        scopes=oidc_config.scopes,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)
    assert params["response_type"] == ["code"]
    assert params["client_id"] == [_CLIENT_ID]
    assert params["code_challenge"] == [code_challenge]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"] == [state]
    assert params["nonce"] == [nonce]

    # Step 3: Exchange code (PKCE: code_verifier sent)
    token_response = await oidc_client.exchange_code(
        token_endpoint=metadata["token_endpoint"],
        code=auth_code,
        redirect_uri=redirect_uri,
        client_id=oidc_config.client_id,
        client_secret="mock-secret",
        code_verifier=code_verifier,
    )
    assert "id_token" in token_response

    # Verify code_verifier was included in the POST body
    token_request = respx.calls.last.request
    body = dict(parse_qs(token_request.content.decode()))
    assert body.get("code_verifier") == [code_verifier]

    # Step 4: Verify id_token
    claims = await oidc_client.verify_id_token(
        id_token=token_response["id_token"],
        issuer_url=oidc_config.issuer_url,
        client_id=oidc_config.client_id,
        nonce=nonce,
    )
    assert claims["sub"] == "user-001"
    assert claims["tenant_id"] == _TENANT_ID
    assert claims["email"] == "user@example.com"

    # Step 5: Map role
    role = map_role_from_claims(
        claims,
        claim_mapping=oidc_config.claim_mapping,
        default_role=oidc_config.default_role,
    )
    assert role == "analyst"


# ---------------------------------------------------------------------------
# Nonce mismatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_nonce_mismatch_raises(oidc_client: OIDCClient):
    """verify_id_token raises InvalidTokenError when nonce does not match."""
    id_token = _make_id_token(nonce="correct-nonce")
    respx.get(_JWKS_URI).mock(return_value=httpx.Response(200, json=_JWKS_RESPONSE))
    respx.get(_DISCOVERY_URL).mock(return_value=httpx.Response(200, json=_DISCOVERY_RESPONSE))

    with pytest.raises(pyjwt.InvalidTokenError, match="nonce"):
        await oidc_client.verify_id_token(
            id_token=id_token,
            issuer_url=_ISSUER,
            client_id=_CLIENT_ID,
            nonce="wrong-nonce",
        )


# ---------------------------------------------------------------------------
# Expired id_token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_expired_id_token_raises(oidc_client: OIDCClient):
    """verify_id_token raises ExpiredSignatureError for an expired token."""
    id_token = _make_id_token(exp_offset=-60, iat_offset=-120)
    respx.get(_JWKS_URI).mock(return_value=httpx.Response(200, json=_JWKS_RESPONSE))
    respx.get(_DISCOVERY_URL).mock(return_value=httpx.Response(200, json=_DISCOVERY_RESPONSE))

    with pytest.raises(pyjwt.ExpiredSignatureError):
        await oidc_client.verify_id_token(
            id_token=id_token,
            issuer_url=_ISSUER,
            client_id=_CLIENT_ID,
        )


# ---------------------------------------------------------------------------
# Wrong audience
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_wrong_audience_raises(oidc_client: OIDCClient):
    """verify_id_token raises InvalidTokenError when audience does not match."""
    id_token = _make_id_token(audience="wrong-client")
    respx.get(_JWKS_URI).mock(return_value=httpx.Response(200, json=_JWKS_RESPONSE))
    respx.get(_DISCOVERY_URL).mock(return_value=httpx.Response(200, json=_DISCOVERY_RESPONSE))

    with pytest.raises(pyjwt.InvalidTokenError):
        await oidc_client.verify_id_token(
            id_token=id_token,
            issuer_url=_ISSUER,
            client_id=_CLIENT_ID,
        )


# ---------------------------------------------------------------------------
# Wrong issuer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_wrong_issuer_raises(oidc_client: OIDCClient):
    """verify_id_token raises InvalidTokenError when issuer does not match."""
    id_token = _make_id_token(issuer="https://evil.example.com")
    respx.get(_JWKS_URI).mock(return_value=httpx.Response(200, json=_JWKS_RESPONSE))
    respx.get(_DISCOVERY_URL).mock(return_value=httpx.Response(200, json=_DISCOVERY_RESPONSE))

    with pytest.raises(pyjwt.InvalidTokenError):
        await oidc_client.verify_id_token(
            id_token=id_token,
            issuer_url=_ISSUER,
            client_id=_CLIENT_ID,
        )


# ---------------------------------------------------------------------------
# Stale iat
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_stale_iat_raises(oidc_client: OIDCClient):
    """verify_id_token raises InvalidTokenError when iat is older than max_iat_age_seconds."""
    stale_iat = int((datetime.now(UTC) - timedelta(seconds=700)).timestamp())
    id_token = _make_id_token(iat_offset=0)
    # Manually re-encode with stale iat
    claims = pyjwt.decode(id_token, options={"verify_signature": False,
                                              "verify_exp": False, "verify_aud": False})
    claims["iat"] = stale_iat
    id_token_stale = pyjwt.encode(claims, _PRIVATE_PEM, algorithm="RS256",
                                   headers={"kid": _KID})

    respx.get(_JWKS_URI).mock(return_value=httpx.Response(200, json=_JWKS_RESPONSE))
    respx.get(_DISCOVERY_URL).mock(return_value=httpx.Response(200, json=_DISCOVERY_RESPONSE))

    with pytest.raises(pyjwt.InvalidTokenError, match="iat"):
        await oidc_client.verify_id_token(
            id_token=id_token_stale,
            issuer_url=_ISSUER,
            client_id=_CLIENT_ID,
            max_iat_age_seconds=600,
        )


# ---------------------------------------------------------------------------
# Role mapping: highest-privilege wins
# ---------------------------------------------------------------------------

def test_role_mapping_highest_privilege_selected():
    """When multiple claim mappings match, the highest-privilege role is returned."""
    claims = {
        "roles": ["analyst", "tenant_admin"],
        "tenant_id": _TENANT_ID,
    }
    mapping = {
        "roles=analyst": "analyst",
        "roles=tenant_admin": "tenant_admin",
    }
    role = map_role_from_claims(claims, claim_mapping=mapping, default_role="read_only")
    assert role == "tenant_admin"


def test_role_mapping_default_when_no_match():
    """Returns default_role when no claim mapping matches."""
    claims = {"roles": ["unknown_group"], "tenant_id": _TENANT_ID}
    mapping = {"roles=admin": "tenant_admin"}
    role = map_role_from_claims(claims, claim_mapping=mapping, default_role="read_only")
    assert role == "read_only"


# ---------------------------------------------------------------------------
# JWKS key rotation: kid-miss triggers re-fetch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_jwks_kid_miss_triggers_refetch(oidc_client: OIDCClient):
    """get_signing_key re-fetches JWKS when kid is not in the cached set."""
    # First call returns a JWKS with a different kid
    stale_jwks = {"keys": [dict(_make_jwk(), kid="old-kid")]}
    fresh_jwks = {"keys": [_make_jwk()]}  # contains _KID

    call_count = {"n": 0}

    def _jwks_side_effect(request):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(200, json=stale_jwks)
        return httpx.Response(200, json=fresh_jwks)

    respx.get(_JWKS_URI).mock(side_effect=_jwks_side_effect)
    respx.get(_DISCOVERY_URL).mock(return_value=httpx.Response(200, json=_DISCOVERY_RESPONSE))

    # Clear OIDCClient's in-memory JWKS cache
    from value_fabric.shared.identity.oidc import _JWKS_CACHE
    _JWKS_CACHE.clear()

    key = await oidc_client.get_signing_key(_ISSUER, kid=_KID)
    assert key is not None
    assert call_count["n"] == 2, "Expected exactly 2 JWKS fetches (initial + re-fetch)"
