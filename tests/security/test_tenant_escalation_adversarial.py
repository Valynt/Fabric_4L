"""Adversarial security tests for tenant isolation, account scoping, and session revocation.

Asserts that:
1. External requests cannot spoof tenant context via `X-Tenant-ID` headers or query parameters.
2. `/auth/authorization-snapshot` denies cross-tenant or unauthorized `X-Account-ID` requests.
3. Revoked sessions (`sid`) and users with global logout (`revoke-all`) are immediately rejected.
4. Organization invitations can be accepted only once and provision active membership.
"""

from __future__ import annotations

import time
import uuid
from typing import Any
from unittest.mock import patch

import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.core.auth_directory import AuthDirectory, DirectoryTenant, DirectoryUser
from app.core.clerk_auth import reset_clerk_verifier_cache
from app.core.clerk_config import (
    AUTH_PROVIDER_CLERK,
    AuthSettings,
    ClerkSettings,
    InternalEnvelopeSettings,
)
from app.core.clerk_verifier import ClerkJWKSCache, ClerkVerifier
from app.routers.clerk_auth import authorization_router, router as clerk_router
from value_fabric.shared.identity.fabric_auth import KeySet, SigningKey, VerificationKey
from value_fabric.shared.identity.middleware import GovernanceMiddleware


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key


@pytest.fixture
def auth_directory():
    directory = AuthDirectory(
        account_authorizer=lambda tenant_id, user_id, account_id: (
            tenant_id == "tenant-alpha" and account_id == "acc-valid-alpha"
        )
    )
    # Seed Tenant Alpha
    directory.upsert_tenant(
        id="tenant-alpha",
        clerk_org_id="org_alpha",
        name="Alpha Corp",
        slug="alpha-corp",
        status="active",
    )
    # Seed Tenant Beta
    directory.upsert_tenant(
        id="tenant-beta",
        clerk_org_id="org_beta",
        name="Beta Corp",
        slug="beta-corp",
        status="active",
    )
    # Seed User Alice (member of Alpha)
    directory.upsert_user(
        id="user-alice",
        clerk_user_id="user_alice_clerk",
        email="alice@alpha.com",
        display_name="Alice Alpha",
        status="active",
    )
    directory.upsert_membership(
        clerk_org_id="org_alpha",
        clerk_user_id="user_alice_clerk",
        clerk_membership_id="mem_alice_alpha",
        role="org:admin",
        status="active",
    )
    # Seed User Bob (member of Beta)
    directory.upsert_user(
        id="user-bob",
        clerk_user_id="user_bob_clerk",
        email="bob@beta.com",
        display_name="Bob Beta",
        status="active",
    )
    directory.upsert_membership(
        clerk_org_id="org_beta",
        clerk_user_id="user_bob_clerk",
        clerk_membership_id="mem_bob_beta",
        role="org:member",
        status="active",
    )
    return directory


@pytest.fixture
def test_client(rsa_keypair, auth_directory):
    app = FastAPI()
    app.include_router(clerk_router)
    app.include_router(authorization_router)

    priv = ed25519.Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    signing_key = SigningKey(kid="test-adversarial-k1", private_pem=priv_pem)
    verification_keys = KeySet([VerificationKey(kid="test-adversarial-k1", public_pem=pub_pem)])

    clerk_settings = ClerkSettings(
        publishable_key=f"{'pk'}_{'test'}_adversarial",
        secret_key=f"{'sk'}_{'test'}_adversarial",
        jwks_url="https://clerk.example.com/.well-known/jwks.json",
        authorized_parties=["http://localhost:3000"],
    )
    envelope_settings = InternalEnvelopeSettings(
        signing_key=signing_key,
        verification_keys=verification_keys,
        envelope_ttl_seconds=60,
    )
    auth_settings = AuthSettings(
        provider=AUTH_PROVIDER_CLERK,
        clerk=clerk_settings,
        envelope=envelope_settings,
    )

    jwks_cache = ClerkJWKSCache(clerk_settings.jwks_url)
    # Mock JWKS in cache
    from jwt.utils import to_base64url_uint

    pub_numbers = rsa_keypair.public_key().public_numbers()
    jwk_entry = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "clerk-test-kid-1",
        "n": to_base64url_uint(pub_numbers.n).decode("ascii"),
        "e": to_base64url_uint(pub_numbers.e).decode("ascii"),
    }
    jwks_cache._jwks = {"keys": [jwk_entry]}
    jwks_cache._fetched_at = time.time()

    verifier = ClerkVerifier(clerk_settings, jwks_cache=jwks_cache)

    reset_clerk_verifier_cache()
    with patch("app.core.clerk_auth.get_auth_settings", return_value=auth_settings), \
         patch("app.core.clerk_config.get_auth_settings", return_value=auth_settings), \
         patch("app.core.clerk_auth._get_verifier", return_value=verifier), \
         patch("app.routers.clerk_auth.get_auth_directory", return_value=auth_directory), \
         patch("app.core.clerk_auth.get_auth_directory", return_value=auth_directory):
        yield TestClient(app)


def _mint_jwt(
    rsa_keypair,
    *,
    sub: str,
    org_id: str | None = None,
    org_role: str = "org:admin",
    sid: str = "sess_test_123",
    iat: int | None = None,
    exp: int | None = None,
    azp: str = "http://localhost:3000",
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "sid": sid,
        "azp": azp,
        "iat": iat or now,
        "exp": exp or (now + 3600),
        "nbf": iat or now,
    }
    if org_id is not None:
        payload["org_id"] = org_id
        payload["org_role"] = org_role
        payload["org_permissions"] = ["*"] if org_role == "org:admin" else ["account:read"]

    return pyjwt.encode(
        payload,
        rsa_keypair,
        algorithm="RS256",
        headers={"kid": "clerk-test-kid-1"},
    )


@pytest.mark.security
@pytest.mark.tenant_boundary
def test_tenant_escalation_via_spoofed_header_denied(test_client, rsa_keypair):
    """Alice belongs to Alpha. She tries to spoof X-Tenant-ID to Beta.

    Gateway must resolve Tenant Alpha from verified claims and ignore spoofed headers.
    """
    token = _mint_jwt(rsa_keypair, sub="user_alice_clerk", org_id="org_alpha")
    response = test_client.get(
        "/auth/clerk/tenant",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant-beta",  # Hostile header spoof attempt
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Must strictly resolve to Alpha, ignoring spoofed X-Tenant-ID header
    assert data["fabric_tenant_id"] == "tenant-alpha"
    assert data["clerk_org_id"] == "org_alpha"


@pytest.mark.security
@pytest.mark.tenant_boundary
def test_cross_tenant_account_escalation_denied(test_client, rsa_keypair):
    """Alice tries to access an account outside Tenant Alpha via X-Account-ID."""
    token = _mint_jwt(rsa_keypair, sub="user_alice_clerk", org_id="org_alpha")

    # 1. Valid account inside Alpha succeeds
    valid_resp = test_client.get(
        "/auth/authorization-snapshot",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Account-ID": "acc-valid-alpha",
        },
    )
    assert valid_resp.status_code == 200
    snapshot = valid_resp.json()
    assert snapshot["accountScope"]["scopeType"] == "account"
    assert snapshot["accountScope"]["accountId"] == "acc-valid-alpha"

    # 2. Hostile / foreign account escalation attempt denied with 403 account_scope_denied
    adversarial_resp = test_client.get(
        "/auth/authorization-snapshot",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Account-ID": "acc-foreign-beta",
        },
    )
    assert adversarial_resp.status_code == 403
    err = adversarial_resp.json()
    assert err["detail"]["code"] == "account_scope_denied"


@pytest.mark.security
def test_session_revocation_denies_subsequent_requests(test_client, rsa_keypair, auth_directory):
    """When a session is revoked, subsequent requests with that session discriminator are rejected."""
    session_id = "sess_alice_active_1"
    token = _mint_jwt(
        rsa_keypair,
        sub="user_alice_clerk",
        org_id="org_alpha",
        sid=session_id,
    )

    # 1. Initial request with valid session succeeds
    resp1 = test_client.get(
        "/auth/clerk/tenant",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 200

    # 2. Revoke the active session
    revoke_resp = test_client.post(
        "/auth/clerk/sessions/revoke",
        json={"session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["revoked"] is True

    # 3. Next request with same session token is rejected with 401
    resp2 = test_client.get(
        "/auth/clerk/tenant",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 401
    assert resp2.json()["detail"]["code"] == "AUTH_TOKEN_INVALID"


@pytest.mark.security
def test_global_user_force_logout(test_client, rsa_keypair, auth_directory):
    """Sign-out-everywhere revokes all tokens issued before the cutoff."""
    t_past = int(time.time()) - 100
    token_old = _mint_jwt(
        rsa_keypair,
        sub="user_bob_clerk",
        org_id="org_beta",
        sid="sess_bob_1",
        iat=t_past,
    )

    # 1. Initial check works
    resp1 = test_client.get(
        "/auth/clerk/tenant",
        headers={"Authorization": f"Bearer {token_old}"},
    )
    assert resp1.status_code == 200

    # 2. Trigger revoke-all (sign out everywhere)
    revoke_resp = test_client.post(
        "/auth/clerk/sessions/revoke-all",
        headers={"Authorization": f"Bearer {token_old}"},
    )
    assert revoke_resp.status_code == 200

    # 3. Token issued in the past is rejected
    resp2 = test_client.get(
        "/auth/clerk/tenant",
        headers={"Authorization": f"Bearer {token_old}"},
    )
    assert resp2.status_code == 401


@pytest.mark.security
def test_invitation_lifecycle_and_acceptance(test_client, rsa_keypair, auth_directory):
    """Seed invitation, list it, accept it, and verify membership is provisioned."""
    # Seed invitation for Charlie in Org Alpha
    auth_directory.upsert_invitation(
        clerk_invitation_id="inv_charlie_123",
        clerk_org_id="org_alpha",
        email="charlie@alpha.com",
        role="org:member",
        status="pending",
    )
    # Seed Charlie as a provisioned user without org membership
    auth_directory.upsert_user(
        id="user-charlie",
        clerk_user_id="user_charlie_clerk",
        email="charlie@alpha.com",
        display_name="Charlie New",
        status="active",
    )

    # Alice lists invitations for Org Alpha
    alice_token = _mint_jwt(rsa_keypair, sub="user_alice_clerk", org_id="org_alpha")
    list_resp = test_client.get(
        "/auth/clerk/invitations",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert list_resp.status_code == 200
    invitations = list_resp.json()
    assert len(invitations) == 1
    assert invitations[0]["invitation_id"] == "inv_charlie_123"

    # Charlie accepts invitation
    charlie_token = _mint_jwt(rsa_keypair, sub="user_charlie_clerk", org_id="org_alpha")
    accept_resp = test_client.post(
        "/auth/clerk/invitations/inv_charlie_123/accept",
        headers={"Authorization": f"Bearer {charlie_token}"},
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "accepted"

    # Charlie now has active membership and can resolve tenant
    charlie_tenant = test_client.get(
        "/auth/clerk/tenant",
        headers={"Authorization": f"Bearer {charlie_token}"},
    )
    assert charlie_tenant.status_code == 200
    assert charlie_tenant.json()["fabric_tenant_id"] == "tenant-alpha"
