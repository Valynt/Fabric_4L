"""
Cross-Tenant JWT Security Regression Tests

Validates the canonical tenant-isolation invariant:
  **Signed JWT claims are the sole authority for tenant/org/workspace identity.**

No header, query parameter, body field, or route parameter can override or
spoof the tenant that is cryptographically bound inside a valid JWT.

These tests use a lightweight FastAPI app wired with the real
GovernanceMiddleware (no dev bypass, no mocked validation) so that every
assertion exercises the actual production resolution and consistency logic.
"""

from __future__ import annotations

import os
import time
from typing import Generator
from uuid import UUID

import jwt as pyjwt
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from value_fabric.shared.identity.jwt import encode_jwt
from value_fabric.shared.identity.middleware import GovernanceMiddleware

# ---------------------------------------------------------------------------
# Deterministic tenant identifiers
# ---------------------------------------------------------------------------
TENANT_A_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_ID = "user-alpha-001"
USER_B_ID = "user-bravo-002"

# A strong secret that satisfies HS256 minimum length and matches
# decode_jwt expectations when JWT_SECRET is patched in fixtures.
_TEST_JWT_SECRET = "cross-tenant-test-secret-32bytes!!"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def jwt_secret_monkeypatch() -> Generator[None, None, None]:
    """Ensure JWT_SECRET is set to a known value for the test module."""
    original = os.environ.get("JWT_SECRET")
    os.environ["JWT_SECRET"] = _TEST_JWT_SECRET
    os.environ["JWT_ALGORITHM"] = "HS256"
    yield
    if original is None:
        os.environ.pop("JWT_SECRET", None)
    else:
        os.environ["JWT_SECRET"] = original


@pytest.fixture
def test_app(jwt_secret_monkeypatch) -> FastAPI:
    """Minimal FastAPI app with production GovernanceMiddleware."""
    app = FastAPI()
    app.add_middleware(GovernanceMiddleware, rate_limiter=None)

    @app.get("/protected")
    def protected(request: Request):
        ctx = getattr(request.state, "governance_context", None)
        if ctx is None:
            return {"error": "no context"}
        return {
            "tenant_id": str(ctx.tenant_id),
            "user_id": ctx.user_id,
            "roles": list(ctx.roles),
            "source": ctx.source,
        }

    @app.post("/protected")
    def protected_post(request: Request):
        ctx = getattr(request.state, "governance_context", None)
        if ctx is None:
            return {"error": "no context"}
        return {
            "tenant_id": str(ctx.tenant_id),
            "user_id": ctx.user_id,
            "roles": list(ctx.roles),
            "source": ctx.source,
        }

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)


@pytest.fixture
def tenant_a_token() -> str:
    return encode_jwt(
        TENANT_A_ID,
        user_id=USER_A_ID,
        roles=["analyst"],
        expires_in_seconds=3600,
    )


@pytest.fixture
def tenant_b_token() -> str:
    return encode_jwt(
        TENANT_B_ID,
        user_id=USER_B_ID,
        roles=["analyst"],
        expires_in_seconds=3600,
    )


@pytest.fixture
def expired_tenant_a_token() -> str:
    return encode_jwt(
        TENANT_A_ID,
        user_id=USER_A_ID,
        roles=["analyst"],
        expires_in_seconds=-3600,
    )


@pytest.fixture
def forged_tenant_b_token() -> str:
    """Token with tenant B claims but signed with the wrong secret."""
    now = int(time.time())
    payload = {
        "tenant_id": str(TENANT_B_ID),
        "sub": USER_B_ID,
        "roles": ["analyst"],
        "iat": now,
        "exp": now + 3600,
    }
    return pyjwt.encode(payload, "wrong-secret-12345", algorithm="HS256")


@pytest.fixture
def tampered_payload_token() -> str:
    """
    A token whose payload claims tenant B but was signed while the payload
    still claimed tenant A (simulates a naive cut-and-paste attack on the
    base64 payload without re-signing).

    We construct this by taking a valid token for tenant A, decoding without
    verification, mutating the tenant claim, and re-encoding with the *same*
    header and signature segments — i.e. an unsigned tampered token.
    """
    valid = encode_jwt(
        TENANT_A_ID,
        user_id=USER_A_ID,
        roles=["analyst"],
        expires_in_seconds=3600,
    )
    # Split into parts
    parts = valid.split(".")
    # Decode payload, mutate tenant, re-encode payload
    payload_bytes = pyjwt.api_jws.base64url_decode(parts[1])
    import json
    payload = json.loads(payload_bytes)
    payload["tenant_id"] = str(TENANT_B_ID)
    new_payload_b64 = pyjwt.api_jws.base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    # Re-assemble with ORIGINAL signature — signature is now invalid
    return f"{parts[0]}.{new_payload_b64}.{parts[2]}"


@pytest.fixture
def malformed_tenant_token() -> str:
    """Valid signature but tenant_id is not a UUID."""
    now = int(time.time())
    payload = {
        "tenant_id": "not-a-valid-uuid",
        "sub": USER_A_ID,
        "roles": ["analyst"],
        "iat": now,
        "exp": now + 3600,
    }
    return pyjwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


# ---------------------------------------------------------------------------
# 1–3: Bearer JWT + basic tenant access
# ---------------------------------------------------------------------------

class TestBearerJWTTenantAuthority:
    """JWT claim is the canonical tenant authority."""

    def test_valid_jwt_can_access_own_tenant_resource(self, client: TestClient, tenant_a_token: str):
        """Valid tenant A JWT → protected route → 200, context shows tenant A."""
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == str(TENANT_A_ID)
        assert data["user_id"] == USER_A_ID
        assert "analyst" in data["roles"]

    def test_valid_jwt_with_matching_header_allowed(self, client: TestClient, tenant_a_token: str):
        """JWT tenant A + X-Tenant-ID matching tenant A → 200."""
        resp = client.get(
            "/protected",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": str(TENANT_A_ID),
            },
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == str(TENANT_A_ID)

    def test_valid_jwt_with_conflicting_header_rejected(self, client: TestClient, tenant_a_token: str):
        """JWT tenant A + X-Tenant-ID tenant B → 403 (conflict)."""
        resp = client.get(
            "/protected",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": str(TENANT_B_ID),
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 4–6: Session cookie resolution
# ---------------------------------------------------------------------------

class TestSessionCookieTenantAuthority:
    """vf_session cookie is treated with the same authority as Bearer JWT."""

    def test_session_cookie_can_access_own_tenant_resource(self, client: TestClient, tenant_a_token: str):
        """Session cookie tenant A → protected route → 200."""
        resp = client.get(
            "/protected",
            cookies={"vf_session": tenant_a_token},
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == str(TENANT_A_ID)

    def test_session_cookie_with_matching_header_allowed(self, client: TestClient, tenant_a_token: str):
        """Cookie tenant A + X-Tenant-ID matching tenant A → 200."""
        resp = client.get(
            "/protected",
            cookies={"vf_session": tenant_a_token},
            headers={"X-Tenant-ID": str(TENANT_A_ID)},
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == str(TENANT_A_ID)

    def test_session_cookie_with_conflicting_header_rejected(self, client: TestClient, tenant_a_token: str):
        """Cookie tenant A + X-Tenant-ID tenant B → 403."""
        resp = client.get(
            "/protected",
            cookies={"vf_session": tenant_a_token},
            headers={"X-Tenant-ID": str(TENANT_B_ID)},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 7–9: Token integrity failures
# ---------------------------------------------------------------------------

class TestTokenIntegrityFailures:
    """Any tampering with the token must result in rejection."""

    def test_expired_jwt_rejected(self, client: TestClient, expired_tenant_a_token: str):
        """Expired JWT → 401."""
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {expired_tenant_a_token}"},
        )
        assert resp.status_code == 401

    def test_forged_jwt_wrong_secret_rejected(self, client: TestClient, forged_tenant_b_token: str):
        """JWT signed with wrong secret → 401."""
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {forged_tenant_b_token}"},
        )
        assert resp.status_code == 401

    def test_tampered_payload_invalid_signature_rejected(self, client: TestClient, tampered_payload_token: str):
        """Payload mutated without re-signing → signature invalid → 401."""
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {tampered_payload_token}"},
        )
        assert resp.status_code == 401

    def test_malformed_tenant_claim_rejected(self, client: TestClient, malformed_tenant_token: str):
        """Valid signature but tenant_id is not a UUID → rejected during extraction."""
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {malformed_tenant_token}"},
        )
        # The middleware extracts context from JWT and then validates the tenant_id
        # as a UUID. A non-UUID tenant_id causes ValueError → 403.
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 10–12: Query / body / header spoofing cannot override JWT
# ---------------------------------------------------------------------------

class TestSpoofingCannotOverrideJWT:
    """Untrusted channels (query, body, headers) must not override the JWT claim."""

    def test_query_param_cannot_override_jwt_tenant(self, client: TestClient, tenant_a_token: str):
        """?tenant_id=<tenant_b> with valid tenant A JWT → JWT wins → 200 tenant A."""
        resp = client.get(
            f"/protected?tenant_id={TENANT_B_ID}",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == str(TENANT_A_ID)

    def test_body_field_cannot_override_jwt_tenant(self, client: TestClient, tenant_a_token: str):
        """POST body containing tenant_id=<tenant_b> with valid tenant A JWT → JWT wins."""
        resp = client.post(
            "/protected",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"tenant_id": str(TENANT_B_ID)},
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == str(TENANT_A_ID)

    def test_x_tenant_id_header_alone_without_service_auth_rejected(self, client: TestClient):
        """X-Tenant-ID without any auth and without SERVICE_AUTH_SECRET → 401."""
        # Ensure SERVICE_AUTH_SECRET is not set for this test
        original = os.environ.pop("SERVICE_AUTH_SECRET", None)
        try:
            resp = client.get(
                "/protected",
                headers={"X-Tenant-ID": str(TENANT_A_ID)},
            )
            # No JWT, no cookie, no API key, and no service auth secret configured → 401
            assert resp.status_code == 401
        finally:
            if original is not None:
                os.environ["SERVICE_AUTH_SECRET"] = original


# ---------------------------------------------------------------------------
# 13–14: Service-to-service header auth
# ---------------------------------------------------------------------------

class TestServiceToServiceHeaderAuth:
    """X-Tenant-ID + X-Service-Auth is allowed only when the shared secret is valid."""

    def test_service_auth_with_valid_secret_allowed(self, client: TestClient, monkeypatch):
        """X-Tenant-ID + correct X-Service-Auth → service context → 200."""
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "valid-service-secret-that-is-32-bytes!!")
        resp = client.get(
            "/protected",
            headers={
                "X-Tenant-ID": str(TENANT_A_ID),
                "X-Service-Auth": "valid-service-secret-that-is-32-bytes!!",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == str(TENANT_A_ID)
        assert "system" in data["roles"]
        assert data["source"] == "service_account"

    def test_service_auth_with_invalid_secret_rejected(self, client: TestClient, monkeypatch):
        """X-Tenant-ID + wrong X-Service-Auth → 401/403."""
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "valid-service-secret-that-is-32-bytes!!")
        resp = client.get(
            "/protected",
            headers={
                "X-Tenant-ID": str(TENANT_A_ID),
                "X-Service-Auth": "wrong-secret",
            },
        )
        # Invalid service auth → middleware returns None → 401
        assert resp.status_code == 401

    def test_service_auth_without_x_service_auth_header_rejected(self, client: TestClient, monkeypatch):
        """X-Tenant-ID without X-Service-Auth header → 401."""
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "valid-service-secret-that-is-32-bytes!!")
        resp = client.get(
            "/protected",
            headers={"X-Tenant-ID": str(TENANT_A_ID)},
        )
        assert resp.status_code == 401

    def test_service_auth_with_too_short_secret_rejected(self, client: TestClient, monkeypatch):
        """SERVICE_AUTH_SECRET below minimum length → 401."""
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "short")
        resp = client.get(
            "/protected",
            headers={
                "X-Tenant-ID": str(TENANT_A_ID),
                "X-Service-Auth": "short",
            },
        )
        assert resp.status_code == 401
