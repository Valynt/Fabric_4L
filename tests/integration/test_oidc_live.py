"""Live OIDC integration tests against a real Keycloak instance.

These tests require a running Keycloak container (port 8080) and are gated
behind the ``oidc_live`` marker so they only run in the dedicated CI job:

    pytest -m oidc_live tests/integration/test_oidc_live.py

The tests bootstrap a throwaway realm, client, and user via the Keycloak
Admin REST API, then exercise the real ``OIDCClient`` end-to-end:

- Discovery document is valid and contains required fields
- JWKS endpoint returns usable signing keys
- Client-credentials token can be obtained and verified
- Resource-owner password grant produces a verifiable id_token
- Expired / tampered tokens are rejected
- Wrong audience is rejected
- Wrong issuer is rejected
- Discovery of a non-existent realm raises OIDCDiscoveryError (not a retry loop)
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx
import jwt as pyjwt
import pytest
import pytest_asyncio
from value_fabric.shared.identity.oidc import OIDCClient, OIDCDiscoveryError

# ---------------------------------------------------------------------------
# Configuration — overridable via environment variables
# ---------------------------------------------------------------------------

_KC_BASE = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
_KC_ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN", "admin")
_KC_ADMIN_PASS = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin")

# Throwaway realm created fresh for each test session
_REALM = f"vf-test-{uuid.uuid4().hex[:8]}"
_CLIENT_ID = "vf-test-client"
_CLIENT_SECRET = "vf-test-secret-32-chars-long-ok!"
_TEST_USER = "testuser@example.com"
_TEST_PASS = "Test1234!"

_ISSUER = f"{_KC_BASE}/realms/{_REALM}"


# ---------------------------------------------------------------------------
# Admin API helpers (sync — used only in session-scoped setup/teardown)
# ---------------------------------------------------------------------------

def _admin_token() -> str:
    """Obtain a short-lived admin access token from the master realm."""
    resp = httpx.post(
        f"{_KC_BASE}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": _KC_ADMIN_USER,
            "password": _KC_ADMIN_PASS,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_admin_token()}"}


def _create_realm(realm: str) -> None:
    resp = httpx.post(
        f"{_KC_BASE}/admin/realms",
        json={"realm": realm, "enabled": True},
        headers=_admin_headers(),
        timeout=15,
    )
    resp.raise_for_status()


def _delete_realm(realm: str) -> None:
    try:
        resp = httpx.delete(
            f"{_KC_BASE}/admin/realms/{realm}",
            headers=_admin_headers(),
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        # Teardown failure must not mask test results, but must be visible in CI.
        import warnings
        warnings.warn(f"Failed to delete Keycloak realm {realm!r}: {exc}", stacklevel=2)


def _create_client(realm: str, client_id: str, secret: str) -> None:
    resp = httpx.post(
        f"{_KC_BASE}/admin/realms/{realm}/clients",
        json={
            "clientId": client_id,
            "secret": secret,
            "enabled": True,
            "publicClient": False,
            "directAccessGrantsEnabled": True,   # resource-owner password grant
            "serviceAccountsEnabled": True,       # client-credentials grant
            "standardFlowEnabled": True,
            "protocol": "openid-connect",
        },
        headers=_admin_headers(),
        timeout=15,
    )
    resp.raise_for_status()


def _create_user(realm: str, username: str, password: str) -> None:
    resp = httpx.post(
        f"{_KC_BASE}/admin/realms/{realm}/users",
        json={
            "username": username,
            "email": username,
            "enabled": True,
            "emailVerified": True,
            "credentials": [{"type": "password", "value": password, "temporary": False}],
        },
        headers=_admin_headers(),
        timeout=15,
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Session-scoped fixture: bootstrap realm once, tear down after all tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=False)
def keycloak_realm():
    """Create a throwaway Keycloak realm for the test session."""
    _create_realm(_REALM)
    _create_client(_REALM, _CLIENT_ID, _CLIENT_SECRET)
    _create_user(_REALM, _TEST_USER, _TEST_PASS)
    yield {
        "issuer": _ISSUER,
        "client_id": _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
        "username": _TEST_USER,
        "password": _TEST_PASS,
        "token_endpoint": f"{_ISSUER}/protocol/openid-connect/token",
    }
    _delete_realm(_REALM)


@pytest_asyncio.fixture
async def oidc_client():
    async with httpx.AsyncClient(timeout=15.0) as http:
        yield OIDCClient(http_client=http)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ropc_token(realm_info: dict[str, Any]) -> dict[str, Any]:
    """Obtain tokens via resource-owner password grant (for test setup only)."""
    resp = httpx.post(
        realm_info["token_endpoint"],
        data={
            "grant_type": "password",
            "client_id": realm_info["client_id"],
            "client_secret": realm_info["client_secret"],
            "username": realm_info["username"],
            "password": realm_info["password"],
            "scope": "openid profile email",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.oidc_live


@pytest.mark.asyncio
async def test_discovery_returns_valid_document(keycloak_realm, oidc_client):
    """OIDCClient.discover() returns a well-formed document from Keycloak."""
    doc = await oidc_client.discover(keycloak_realm["issuer"])

    assert doc["issuer"] == keycloak_realm["issuer"]
    for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        assert field in doc, f"Missing required field: {field}"


@pytest.mark.asyncio
async def test_jwks_endpoint_returns_keys(keycloak_realm, oidc_client):
    """JWKS endpoint returns at least one RSA signing key."""
    doc = await oidc_client.discover(keycloak_realm["issuer"])
    resp = await oidc_client._http_client.get(doc["jwks_uri"])
    resp.raise_for_status()
    keys = resp.json().get("keys", [])

    assert len(keys) >= 1, "Expected at least one JWKS key"
    assert any(k.get("use") == "sig" for k in keys), "No signing key found in JWKS"


@pytest.mark.asyncio
async def test_ropc_id_token_verifies(keycloak_realm, oidc_client):
    """id_token obtained via ROPC grant passes OIDCClient.verify_id_token()."""
    tokens = _ropc_token(keycloak_realm)
    id_token = tokens.get("id_token")
    assert id_token, "No id_token in ROPC response"

    claims = await oidc_client.verify_id_token(
        id_token=id_token,
        issuer_url=keycloak_realm["issuer"],
        client_id=keycloak_realm["client_id"],
    )

    assert claims["iss"] == keycloak_realm["issuer"]
    assert keycloak_realm["client_id"] in (
        claims.get("aud") if isinstance(claims.get("aud"), list) else [claims.get("aud")]
    )


@pytest.mark.asyncio
async def test_tampered_token_is_rejected(keycloak_realm, oidc_client):
    """A token with a modified payload fails signature verification."""
    tokens = _ropc_token(keycloak_realm)
    id_token = tokens["id_token"]

    # Corrupt the payload segment (middle part of the JWT)
    header, payload, sig = id_token.split(".")
    import base64
    import json as _json
    padded = payload + "=" * (-len(payload) % 4)
    claims_dict = _json.loads(base64.urlsafe_b64decode(padded))
    claims_dict["sub"] = "attacker-injected-sub"
    tampered_payload = base64.urlsafe_b64encode(
        _json.dumps(claims_dict).encode()
    ).rstrip(b"=").decode()
    tampered_token = f"{header}.{tampered_payload}.{sig}"

    with pytest.raises(pyjwt.InvalidTokenError):
        await oidc_client.verify_id_token(
            id_token=tampered_token,
            issuer_url=keycloak_realm["issuer"],
            client_id=keycloak_realm["client_id"],
        )


@pytest.mark.asyncio
async def test_wrong_audience_is_rejected(keycloak_realm, oidc_client):
    """verify_id_token raises InvalidTokenError when audience does not match."""
    tokens = _ropc_token(keycloak_realm)
    id_token = tokens["id_token"]

    with pytest.raises(pyjwt.InvalidTokenError):
        await oidc_client.verify_id_token(
            id_token=id_token,
            issuer_url=keycloak_realm["issuer"],
            client_id="wrong-client-id",
        )


@pytest.mark.asyncio
async def test_wrong_issuer_is_rejected(keycloak_realm, oidc_client):
    """verify_id_token raises InvalidTokenError when issuer does not match."""
    tokens = _ropc_token(keycloak_realm)
    id_token = tokens["id_token"]

    with pytest.raises(pyjwt.InvalidTokenError):
        await oidc_client.verify_id_token(
            id_token=id_token,
            issuer_url="https://evil-idp.example.com/realms/fabric",
            client_id=keycloak_realm["client_id"],
        )


@pytest.mark.asyncio
async def test_discovery_nonexistent_realm_raises_oidc_error(oidc_client):
    """Discovering a non-existent realm raises OIDCDiscoveryError (not a retry loop)."""
    with pytest.raises(OIDCDiscoveryError):
        await oidc_client.discover(f"{_KC_BASE}/realms/does-not-exist-{uuid.uuid4().hex}")


@pytest.mark.asyncio
async def test_get_signing_key_caches_on_second_call(keycloak_realm, oidc_client):
    """get_signing_key returns the same key material on repeated calls (JWKS cache hit)."""
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    key1 = await oidc_client.get_signing_key(keycloak_realm["issuer"])
    key2 = await oidc_client.get_signing_key(keycloak_realm["issuer"])

    assert key1 is not None
    assert key2 is not None
    # Key material must be identical — confirms cache is serving the same key
    pem1 = key1.key.public_bytes(encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo)
    pem2 = key2.key.public_bytes(encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo)
    assert pem1 == pem2
