"""Tests for FabricAuthMiddleware (used by L1\u2013L6 services).

Covers the Phase 1 security invariants:
- Missing envelope -> 401 (enforce mode).
- Tampered envelope -> 401.
- Browser-controlled X-Tenant-ID hints are ignored for tenant scoping.
- Raw Clerk-style JWT in X-Fabric-Auth (signed with a different key) -> 401.
- Public paths bypass auth.
- Observe mode never blocks but does not populate request.state.auth on failure.
"""
from __future__ import annotations

import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from value_fabric.shared.identity.fabric_auth import (
    AuthContext,
    FabricAuthMiddleware,
    KeySet,
    SigningKey,
    VerificationKey,
    sign_envelope,
)
from value_fabric.shared.identity.context import get_request_context


def _generate_keypair(kid: str) -> tuple[SigningKey, VerificationKey]:
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
    return SigningKey(kid=kid, private_pem=private_pem), VerificationKey(
        kid=kid, public_pem=public_pem
    )


def _make_app(*, vk: VerificationKey, mode: str = "enforce") -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        FabricAuthMiddleware,
        key_set=KeySet([vk]),
        mode=mode,
    )

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/api/echo")
    def echo(request: Request):
        auth: AuthContext | None = getattr(request.state, "auth", None)
        governance_context = getattr(request.state, "governance_context", None)
        shared_context = get_request_context()
        return {
            "tenant_id": auth.tenant_id if auth else None,
            "user_id": auth.user_id if auth else None,
            "context_tenant_id": str(governance_context.tenant_id) if governance_context else None,
            "context_user_id": str(governance_context.user_id) if governance_context else None,
            "shared_context_tenant_id": str(shared_context.tenant_id) if shared_context else None,
            "shared_context_user_id": str(shared_context.user_id) if shared_context else None,
        }

    return app


def _make_auth(kid: str = "k1", **overrides) -> AuthContext:
    now = int(time.time())
    base = dict(
        clerk_user_id="user_abc",
        clerk_org_id="org_xyz",
        user_id="u1",
        tenant_id="t1",
        request_id="req_1",
        iat=now,
        exp=now + 60,
        nbf=now,
        kid=kid,
    )
    base.update(overrides)
    return AuthContext(**base)


def test_health_path_bypasses_auth():
    _, vk = _generate_keypair("k1")
    client = TestClient(_make_app(vk=vk))
    response = client.get("/health")
    assert response.status_code == 200


def test_missing_envelope_rejected_in_enforce_mode():
    _, vk = _generate_keypair("k1")
    client = TestClient(_make_app(vk=vk))
    response = client.get("/api/echo")
    assert response.status_code == 401
    assert response.json()["code"] == "auth.envelope_missing"


def test_valid_envelope_populates_request_state():
    sk, vk = _generate_keypair("k1")
    auth = _make_auth(kid="k1")
    token = sign_envelope(auth, signing_key=sk)
    client = TestClient(_make_app(vk=vk))
    response = client.get("/api/echo", headers={"X-Fabric-Auth": token})
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "t1"
    assert body["user_id"] == "u1"
    assert body["context_tenant_id"] == "t1"
    assert body["context_user_id"] == "u1"
    assert body["shared_context_tenant_id"] == "t1"
    assert body["shared_context_user_id"] == "u1"


def test_tampered_envelope_rejected():
    sk, vk = _generate_keypair("k1")
    token = sign_envelope(_make_auth(kid="k1"), signing_key=sk)
    header, payload, signature = token.split(".")
    tampered = ".".join([header, payload[:-2] + "AA", signature])
    client = TestClient(_make_app(vk=vk))
    response = client.get("/api/echo", headers={"X-Fabric-Auth": tampered})
    assert response.status_code == 401
    assert response.json()["code"] == "auth.envelope_invalid"


def test_tenant_id_header_hint_does_not_override_envelope_context():
    sk, vk = _generate_keypair("k1")
    token = sign_envelope(_make_auth(kid="k1", tenant_id="t1"), signing_key=sk)
    client = TestClient(_make_app(vk=vk))
    response = client.get(
        "/api/echo",
        headers={"X-Fabric-Auth": token, "X-Tenant-ID": "t-evil"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "t1"
    assert body["context_tenant_id"] == "t1"
    assert body["shared_context_tenant_id"] == "t1"


def test_raw_clerk_jwt_in_envelope_header_is_rejected():
    """A raw Clerk JWT (signed with a non-Fabric key) must NOT be accepted.

    L1\u2013L6 only trust the gateway-signed Ed25519 envelope.
    """
    import jwt as pyjwt

    _, vk = _generate_keypair("k1")
    # Simulate a Clerk-issued HS256 token that an attacker tries to replay
    # against a downstream service.
    forged = pyjwt.encode(
        {
            "iss": "https://clerk.example.com",
            "aud": "fabric4l-internal",
            "sub": "user_abc",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        },
        "shared-secret",
        algorithm="HS256",
        headers={"kid": "k1"},
    )
    client = TestClient(_make_app(vk=vk))
    response = client.get("/api/echo", headers={"X-Fabric-Auth": forged})
    assert response.status_code == 401
    assert response.json()["code"] == "auth.envelope_invalid"


def test_observe_mode_does_not_block_missing_envelope():
    _, vk = _generate_keypair("k1")
    client = TestClient(_make_app(vk=vk, mode="observe"))
    response = client.get("/api/echo")
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] is None
