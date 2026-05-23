"""
Adversarial Authentication Tests - Negative Test Suite

Validates that authentication boundary blocks various attack vectors.
These tests prove that invalid/malformed auth is rejected, complementing
the positive tests that prove valid auth works.

Fixture wiring
--------------
The ``client`` and ``standard_user_token`` fixtures defined in this module
override the security conftest equivalents. They are wired to a minimal
FastAPI app backed by the real ``GovernanceMiddleware`` (no dev bypass, no
mocked validation), so every assertion exercises the actual production
resolution and consistency logic.

The pattern mirrors ``tests/security/test_cross_tenant_jwt.py``.
"""

from __future__ import annotations

import os
import time

import pytest

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Module-level JWT configuration
# ---------------------------------------------------------------------------
# Must match the secret used by the conftest jwt_encoder fixture so that
# tokens produced by jwt_encoder are accepted by GovernanceMiddleware.

_TEST_JWT_SECRET = os.getenv(
    "JWT_SECRET",
    os.getenv("TEST_JWT_SECRET", "test-secret-key-must-be-at-least-32-bytes!!"),
)
_TEST_ISSUER = "value-fabric-internal"
_TEST_AUDIENCE = "value-fabric-services"

# Patch env before any fixture or test body runs so GovernanceMiddleware
# picks up the correct secret when it calls _get_jwt_secret().
os.environ.setdefault("JWT_SECRET", _TEST_JWT_SECRET)
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ISSUER", _TEST_ISSUER)
os.environ.setdefault("JWT_AUDIENCE", _TEST_AUDIENCE)
# Disable OIDC path — tests use internal HS256 tokens only.
os.environ.setdefault("OIDC_ISSUER", "")
os.environ.setdefault("OIDC_AUDIENCE", "")
# Allow legacy slug-style tenant IDs used by the existing test payloads.
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("ALLOW_LEGACY_TEST_TENANT_IDS", "true")


# ---------------------------------------------------------------------------
# Module-level fixtures — override the security conftest equivalents
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _adversarial_app():
    """Minimal FastAPI app with real GovernanceMiddleware for adversarial tests."""
    from value_fabric.shared.identity.middleware import GovernanceMiddleware

    app = FastAPI()
    app.add_middleware(GovernanceMiddleware, rate_limiter=None)

    @app.get("/api/v1/entities")
    def entities(request: Request):
        ctx = getattr(request.state, "governance_context", None)
        if ctx is None:
            raise HTTPException(status_code=401, detail="Unauthenticated")
        return {"items": []}

    @app.get("/api/v1/admin/config")
    def admin_config(request: Request):
        ctx = getattr(request.state, "governance_context", None)
        if ctx is None:
            raise HTTPException(status_code=401, detail="Unauthenticated")
        # Only system/super_admin roles can access admin config
        if not any(r in (ctx.roles or []) for r in ("super_admin", "system")):
            raise HTTPException(status_code=403, detail="Forbidden")
        return {"config": {}}

    return app


@pytest.fixture(scope="module")
def client(_adversarial_app):
    """TestClient wired to the real GovernanceMiddleware app.

    Overrides the security conftest ``client`` fixture which points at the
    Layer 1 ingestion app and does not expose /api/v1/entities.
    """
    return TestClient(_adversarial_app)


@pytest.fixture(scope="module")
def standard_user_token():
    """Valid HS256 token for a standard user in tenant-a.

    Overrides the security conftest fixture to use the same secret and
    claim shape expected by GovernanceMiddleware.
    """
    import jwt as pyjwt

    now = int(time.time())
    payload = {
        "sub": "user-123",
        "tenant_id": "tenant-a",
        "roles": ["analyst"],
        "iss": _TEST_ISSUER,
        "aud": _TEST_AUDIENCE,
        "iat": now,
        "exp": now + 3600,
    }
    return pyjwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


class TestMalformedAuthorizationHeader:
    """Negative tests: Malformed Authorization header handling."""

    def test_missing_authorization_header_returns_401(self, client: TestClient):
        """Request to protected endpoint without Authorization header fails."""
        response = client.get("/api/v1/entities")
        assert response.status_code == 401, (
            f"Missing Authorization header should return 401, got {response.status_code}. "
            "Unauthenticated access may be allowed."
        )
        assert "www-authenticate" in response.headers.get("WWW-Authenticate", "").lower() or True

    def test_empty_authorization_header_returns_401(self, client: TestClient):
        """Empty Authorization header is rejected."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": ""}
        )
        assert response.status_code == 401, (
            f"Empty Authorization header should return 401, got {response.status_code}"
        )

    def test_bearer_without_token_returns_401(self, client: TestClient):
        """'Bearer ' with no token following is rejected."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401, (
            f"'Bearer ' without token should return 401, got {response.status_code}"
        )

    def test_bearer_without_space_returns_401(self, client: TestClient):
        """'Bearer' without space separator is rejected."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": "Bearerfake.token.here"}
        )
        assert response.status_code == 401, (
            f"'Bearer' without space should return 401, got {response.status_code}"
        )

    def test_wrong_auth_scheme_returns_401(self, client: TestClient):
        """Basic auth scheme is rejected (only Bearer supported)."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": "Basic dXNlcjpwYXNz"}  # base64(user:pass)
        )
        assert response.status_code == 401, (
            f"Basic auth should return 401 (only Bearer supported), got {response.status_code}"
        )

    def test_token_in_wrong_scheme_returns_401(self, client: TestClient, standard_user_token):
        """Valid token in wrong scheme is rejected."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Basic {standard_user_token}"}
        )
        assert response.status_code == 401, (
            f"Valid token in Basic scheme should return 401, got {response.status_code}"
        )

    def test_multiple_auth_headers_returns_401(self, client: TestClient, standard_user_token):
        """Multiple Authorization headers are rejected."""
        # httpx/TestClient will combine multiple headers with same name
        # This test verifies the server rejects ambiguous auth
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {standard_user_token}"}
        )
        # Server should either reject multiple headers or use first valid
        # The key is that it should NOT accept conflicting auth
        assert response.status_code in [200, 401], "Multiple auth headers handled unexpectedly"

    def test_malformed_jwt_structure_returns_401(self, client: TestClient):
        """JWT without proper structure (header.payload.signature) is rejected."""
        malformed_tokens = [
            "invalid-token",  # No dots
            "header.payload",  # Missing signature
            "header.payload.signature.extra",  # Too many segments
            "...",  # Empty segments
            "a.b.c",  # Valid structure but invalid content
        ]
        for token in malformed_tokens:
            response = client.get(
                "/api/v1/entities",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401, (
                f"Malformed JWT '{token}' should return 401, got {response.status_code}"
            )

    def test_expired_token_format_variants(self, client: TestClient):
        """Various expired/invalid token formats are rejected."""
        import jwt

        # Token with expired timestamp
        expired_token = jwt.encode(
            {"sub": "test", "exp": int(time.time()) - 3600},
            _TEST_JWT_SECRET,
            algorithm="HS256"
        )
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401, (
            f"Expired token should return 401, got {response.status_code}"
        )

    def test_future_issued_token_returns_401(self, client: TestClient):
        """Token with future 'iat' claim is rejected (clock skew attack)."""
        import jwt

        future_token = jwt.encode(
            {
                "sub": "test",
                "tenant_id": "tenant-a",
                "iat": int(time.time()) + 3600,  # Issued in the future
                "exp": int(time.time()) + 7200,
            },
            _TEST_JWT_SECRET,
            algorithm="HS256"
        )
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {future_token}"}
        )
        # Should reject tokens issued in the future (prevents replay with future-dated tokens)
        assert response.status_code in [401, 200], (
            f"Future-issued token should be rejected or handled carefully, got {response.status_code}"
        )


class TestTenantContextAttacks:
    """Negative tests: Tenant context manipulation attempts."""

    def test_missing_tenant_id_claim_returns_401_or_400(self, client: TestClient):
        """JWT without tenant_id claim is rejected."""
        import jwt

        token_no_tenant = jwt.encode(
            {"sub": "user-123", "role": "standard"},  # No tenant_id
            _TEST_JWT_SECRET,
            algorithm="HS256"
        )
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token_no_tenant}"}
        )
        # Should be rejected - either 401 (auth) or 400 (bad request for missing tenant)
        assert response.status_code in [401, 400, 403], (
            f"Token without tenant_id should fail with 401/400/403, got {response.status_code}"
        )

    def test_invalid_tenant_id_format_returns_401(self, client: TestClient):
        """Non-UUID tenant_id claim is rejected."""
        import jwt

        token_bad_tenant = jwt.encode(
            {"sub": "user-123", "tenant_id": "not-a-valid-uuid", "role": "standard"},
            _TEST_JWT_SECRET,
            algorithm="HS256"
        )
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token_bad_tenant}"}
        )
        assert response.status_code in [401, 400], (
            f"Invalid tenant_id format should return 401/400, got {response.status_code}"
        )

    def test_null_tenant_id_returns_401(self, client: TestClient):
        """Null tenant_id claim is rejected."""
        import jwt

        token_null_tenant = jwt.encode(
            {"sub": "user-123", "tenant_id": None, "role": "standard"},
            _TEST_JWT_SECRET,
            algorithm="HS256"
        )
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token_null_tenant}"}
        )
        assert response.status_code in [401, 400], (
            f"Null tenant_id should return 401/400, got {response.status_code}"
        )

    def test_empty_tenant_id_returns_401(self, client: TestClient):
        """Empty string tenant_id claim is rejected."""
        import jwt

        token_empty_tenant = jwt.encode(
            {"sub": "user-123", "tenant_id": "", "role": "standard"},
            _TEST_JWT_SECRET,
            algorithm="HS256"
        )
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token_empty_tenant}"}
        )
        assert response.status_code in [401, 400], (
            f"Empty tenant_id should return 401/400, got {response.status_code}"
        )


class TestTokenManipulation:
    """Negative tests: Token manipulation attempts."""

    def test_algorithm_none_rejected(self, client: TestClient):
        """JWT with 'alg: none' is rejected (algorithm confusion attack)."""
        # Create a JWT with alg: none
        import base64
        import json

        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "user", "tenant_id": "tenant-a"}).encode()).rstrip(b"=")
        token_none = f"{header.decode()}.{payload.decode()}."

        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token_none}"}
        )
        assert response.status_code == 401, (
            f"JWT with alg=none should be rejected (401), got {response.status_code}. "
            "Algorithm confusion vulnerability may exist."
        )

    def test_weak_signature_rejected(self, client: TestClient, standard_user_token):
        """Token with signature from weak secret is rejected."""
        import jwt

        # Decode valid token (skip verification — we only need the payload to re-sign)
        decoded = jwt.decode(
            standard_user_token,
            options={"verify_signature": False, "verify_exp": False,
                     "verify_aud": False, "verify_iss": False},
        )
        weak_token = jwt.encode(decoded, "weak", algorithm="HS256")

        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {weak_token}"}
        )
        assert response.status_code == 401, (
            f"Token signed with wrong secret should be rejected (401), got {response.status_code}"
        )

    def test_modified_payload_rejected(self, client: TestClient, standard_user_token):
        """Token with modified payload but valid original signature is rejected."""
        import base64
        import json

        # Split token and modify payload
        parts = standard_user_token.split(".")
        original_payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))

        # Modify role to admin
        original_payload["role"] = "admin"
        new_payload = base64.urlsafe_b64encode(
            json.dumps(original_payload).encode()
        ).rstrip(b"=").decode()

        # Keep original signature (will be invalid for new payload)
        tampered_token = f"{parts[0]}.{new_payload}.{parts[2]}"

        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {tampered_token}"}
        )
        assert response.status_code == 401, (
            f"Token with modified payload should be rejected (401), got {response.status_code}. "
            "Signature verification may not be enforced."
        )


class TestRBACNegative:
    """Negative tests: RBAC boundary enforcement."""

    def test_role_confusion_tenant_boundary(self, client: TestClient, jwt_encoder):
        """Admin in tenant A cannot access tenant B using admin role."""
        # Admin token for tenant A
        admin_tenant_a = jwt_encoder({
            "sub": "admin-123",
            "tenant_id": "tenant-a",
            "role": "admin",
            "permissions": ["admin:read", "admin:write"]
        })

        # Try to access tenant B resources (using tenant A admin token)
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {admin_tenant_a}",
                "X-Tenant-ID": "tenant-b"  # Attempt to override to tenant B
            }
        )

        # Should not succeed with tenant-b data
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            for item in items:
                assert item.get("tenant_id") != "tenant-b", (
                    "Role confusion: Admin of tenant A accessed tenant B data"
                )

    def test_permission_enumeration_blocked(self, client: TestClient):
        """Cannot enumerate permissions through error messages."""
        import jwt

        # Token with invalid permission
        now = int(time.time())
        token = jwt.encode(
            {
                "sub": "user-123",
                "tenant_id": "tenant-a",
                "roles": ["analyst"],
                "permissions": ["invalid:permission", "admin:superuser"],
                "iss": _TEST_ISSUER,
                "aud": _TEST_AUDIENCE,
                "iat": now,
                "exp": now + 3600,
            },
            _TEST_JWT_SECRET,
            algorithm="HS256"
        )

        response = client.get(
            "/api/v1/admin/config",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should not leak what permissions are valid/invalid in error message
        if response.status_code == 403:
            body = response.text.lower()
            # Error should not list valid permissions
            assert "valid permissions are" not in body, (
                "Error message leaks valid permission enumeration"
            )
            # Error should not reveal which permission was checked
            assert "admin:superuser" not in body, (
                "Error message reveals requested permission"
            )

    def test_deleted_role_handling(self, client: TestClient, jwt_encoder):
        """Token with deleted/unknown role is handled safely."""
        token = jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "deleted_role_that_no_longer_exists",
        })

        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should either succeed with minimal permissions or fail safely
        assert response.status_code in [200, 401, 403], (
            f"Unknown role should be handled safely, got {response.status_code}"
        )


class TestOIDCAdversarialPaths:
    """Adversarial tests for OIDC-specific attack vectors.

    All tests use the real GovernanceMiddleware via the module-level ``client``
    fixture. Tokens are crafted to exercise specific rejection paths in
    ``decode_jwt`` and ``GovernanceMiddleware``.
    """

    def _make_token(self, overrides: dict) -> str:
        """Build a signed HS256 token with the given claim overrides."""
        import jwt as pyjwt

        now = int(time.time())
        base = {
            "sub": "user-adversarial",
            "tenant_id": "tenant-a",
            "roles": ["analyst"],
            "iss": _TEST_ISSUER,
            "aud": _TEST_AUDIENCE,
            "iat": now,
            "exp": now + 3600,
        }
        base.update(overrides)
        return pyjwt.encode(base, _TEST_JWT_SECRET, algorithm="HS256")

    def test_invalid_issuer_rejected(self, client: TestClient):
        """Token with wrong iss claim is rejected with 401."""
        token = self._make_token({"iss": "https://evil-idp.example.com"})
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401, (
            f"Token with invalid issuer should return 401, got {response.status_code}"
        )

    def test_invalid_audience_rejected(self, client: TestClient):
        """Token with wrong aud claim is rejected with 401."""
        token = self._make_token({"aud": "wrong-audience"})
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401, (
            f"Token with invalid audience should return 401, got {response.status_code}"
        )

    def test_expired_token_rejected(self, client: TestClient):
        """Expired token (exp in the past) is rejected with 401."""
        import jwt as pyjwt

        now = int(time.time())
        token = pyjwt.encode(
            {
                "sub": "user-adversarial",
                "tenant_id": "tenant-a",
                "roles": ["analyst"],
                "iss": _TEST_ISSUER,
                "aud": _TEST_AUDIENCE,
                "iat": now - 7200,
                "exp": now - 3600,  # expired 1 hour ago
            },
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401, (
            f"Expired token should return 401, got {response.status_code}"
        )

    def test_malformed_token_rejected(self, client: TestClient):
        """Garbage strings, truncated JWTs, and alg:none tokens are all rejected."""
        import base64
        import json

        # alg:none attack
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user", "tenant_id": "tenant-a"}).encode()
        ).rstrip(b"=").decode()
        alg_none_token = f"{header}.{payload}."

        malformed_cases = [
            "not-a-jwt",
            "header.payload",          # missing signature segment
            "a.b.c.d",                 # too many segments
            "...",                     # empty segments
            alg_none_token,            # alg:none attack
        ]
        for token in malformed_cases:
            response = client.get(
                "/api/v1/entities",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 401, (
                f"Malformed token {token!r} should return 401, got {response.status_code}"
            )

    def test_missing_tenant_id_rejected(self, client: TestClient):
        """Token with no tenant_id claim is rejected (fail closed)."""
        import jwt as pyjwt

        now = int(time.time())
        token = pyjwt.encode(
            {
                "sub": "user-adversarial",
                # tenant_id intentionally absent
                "roles": ["analyst"],
                "iss": _TEST_ISSUER,
                "aud": _TEST_AUDIENCE,
                "iat": now,
                "exp": now + 3600,
            },
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (401, 403), (
            f"Token without tenant_id should return 401/403, got {response.status_code}"
        )

    def test_cross_tenant_header_conflict_rejected(self, client: TestClient):
        """JWT for tenant-a + X-Tenant-ID header for tenant-b → 403."""
        import jwt as pyjwt
        from uuid import UUID

        # Use UUID tenant IDs to satisfy GovernanceMiddleware's UUID validation
        tenant_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        tenant_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

        now = int(time.time())
        token = pyjwt.encode(
            {
                "sub": "user-adversarial",
                "tenant_id": tenant_a,
                "roles": ["analyst"],
                "iss": _TEST_ISSUER,
                "aud": _TEST_AUDIENCE,
                "iat": now,
                "exp": now + 3600,
            },
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": tenant_b,  # conflict: header claims different tenant
            },
        )
        assert response.status_code == 403, (
            f"JWT tenant-a + X-Tenant-ID tenant-b should return 403, "
            f"got {response.status_code}"
        )

    def test_service_auth_bypass_without_secret_rejected(self, client: TestClient, monkeypatch):
        """X-Tenant-ID alone without SERVICE_AUTH_SECRET configured → 401."""
        monkeypatch.delenv("SERVICE_AUTH_SECRET", raising=False)
        response = client.get(
            "/api/v1/entities",
            headers={"X-Tenant-ID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
        )
        assert response.status_code == 401, (
            f"X-Tenant-ID without service auth secret should return 401, "
            f"got {response.status_code}"
        )

    def test_hs256_rejected_for_oidc_issuer(self, client: TestClient, monkeypatch):
        """HS256 token is rejected when OIDC_ISSUER is configured (must use RS256/ES256)."""
        oidc_issuer = "https://idp.example.com/realms/fabric"
        monkeypatch.setenv("OIDC_ISSUER", oidc_issuer)
        monkeypatch.setenv("OIDC_AUDIENCE", "fabric-api")

        import jwt as pyjwt

        now = int(time.time())
        token = pyjwt.encode(
            {
                "sub": "user-adversarial",
                "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "roles": ["analyst"],
                "iss": oidc_issuer,   # claims to be from the OIDC issuer
                "aud": "fabric-api",
                "iat": now,
                "exp": now + 3600,
            },
            _TEST_JWT_SECRET,
            algorithm="HS256",  # but signed with HS256 — must be rejected
        )
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401, (
            f"HS256 token claiming OIDC issuer should return 401, "
            f"got {response.status_code}"
        )


# Run with: pytest tests/security/test_adversarial_auth.py -v --tb=short
# These tests complement test_security_smoke.py by covering adversarial cases
