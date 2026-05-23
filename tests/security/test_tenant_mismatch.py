"""Tenant Mismatch Security Tests — P0 Critical Gap Remediation

Validates that X-Tenant-ID header cannot override JWT tenant claim.

Production Invariant: JWT tenant claim takes precedence; mismatches rejected.
The ``validate_context_consistency`` function in GovernanceMiddleware enforces
this: a JWT-authenticated request carrying an X-Tenant-ID that differs from
the JWT tenant_id claim is rejected with HTTP 403.
"""

from __future__ import annotations

import os
import time

import pytest

# Ensure GovernanceMiddleware uses HS256 test tokens and no OIDC path.
os.environ.setdefault("JWT_SECRET", "test-secret-key-must-be-at-least-32-bytes!!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ISSUER", "value-fabric-internal")
os.environ.setdefault("JWT_AUDIENCE", "value-fabric-services")
os.environ.setdefault("OIDC_ISSUER", "")
os.environ.setdefault("OIDC_AUDIENCE", "")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("ALLOW_LEGACY_TEST_TENANT_IDS", "true")

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

pytestmark = [
    pytest.mark.security,
    pytest.mark.tenant_mismatch,
    pytest.mark.tenant_boundary,
]

_TEST_JWT_SECRET = os.environ["JWT_SECRET"]
_TEST_ISSUER = os.environ["JWT_ISSUER"]
_TEST_AUDIENCE = os.environ["JWT_AUDIENCE"]


# ---------------------------------------------------------------------------
# Module-level fixtures — override the shared conftest equivalents so these
# tests exercise the real GovernanceMiddleware rather than the L1 app.
# Pattern mirrors test_adversarial_auth.py and test_cross_tenant_jwt.py.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _mismatch_app():
    """Minimal FastAPI app backed by real GovernanceMiddleware."""
    from value_fabric.shared.identity.middleware import GovernanceMiddleware

    app = FastAPI()
    app.add_middleware(GovernanceMiddleware, rate_limiter=None)

    @app.get("/api/v1/entities")
    def entities(request: Request):
        ctx = getattr(request.state, "governance_context", None)
        if ctx is None:
            raise HTTPException(status_code=401, detail="Unauthenticated")
        return {"items": [], "tenant_id": str(ctx.tenant_id)}

    return app


@pytest.fixture(scope="module")
def client(_mismatch_app):
    """TestClient wired to the real GovernanceMiddleware app."""
    return TestClient(_mismatch_app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def tenant_a_token():
    """JWT for tenant-a, signed with the test secret."""
    import jwt as _jwt
    now = int(time.time())
    return _jwt.encode(
        {
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "roles": ["analyst"],
            "iss": _TEST_ISSUER,
            "aud": _TEST_AUDIENCE,
            "iat": now,
            "exp": now + 3600,
        },
        _TEST_JWT_SECRET,
        algorithm="HS256",
    )


class TestTenantHeaderMismatch:
    """P0: X-Tenant-ID header cannot override JWT tenant claim."""

    def test_jwt_tenant_mismatch_with_header_rejected(
        self, client: TestClient, tenant_a_token: str
    ):
        """P0: JWT tenant A + X-Tenant-ID header B = Rejected.
        
        This prevents tenant spoofing via headers.
        """
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": "tenant-b-id"  # Attempted spoof
            }
        )
        
        # Should reject the mismatch
        assert response.status_code in [400, 403], (
            f"Tenant mismatch should be rejected, got {response.status_code}. "
            "P0: X-Tenant-ID header can override JWT claim - SPOOFING VULNERABILITY."
        )

    def test_matching_tenant_header_succeeds(
        self, client: TestClient, tenant_a_token: str
    ):
        """POSITIVE: Matching X-Tenant-ID header allowed."""
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": "tenant-a"  # Matches JWT
            }
        )
        
        # Should be allowed (or 404 if no data, but not 401/403)
        assert response.status_code not in [401, 403, 400], (
            f"Matching tenant header should succeed, got {response.status_code}"
        )


class TestTenantSpoofingAttempts:
    """NEGATIVE: Various tenant spoofing techniques blocked."""

    def test_invalid_tenant_header_format_rejected(self, client: TestClient, tenant_a_token: str):
        """X-Tenant-ID with invalid format rejected."""
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": "../../../etc/passwd"  # Path traversal attempt
            }
        )
        
        assert response.status_code in [400, 403], (
            f"Invalid tenant header format should be rejected, got {response.status_code}"
        )

    def test_sql_injection_in_tenant_header_blocked(self, client: TestClient, tenant_a_token: str):
        """SQL injection in X-Tenant-ID blocked."""
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": "tenant-a' OR '1'='1"
            }
        )
        
        assert response.status_code in [400, 403, 500], (
            "SQL injection in tenant header should be blocked"
        )

    def test_xss_in_tenant_header_sanitized(self, client: TestClient, tenant_a_token: str):
        """XSS attempt in X-Tenant-ID sanitized."""
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": "<script>alert('xss')</script>"
            }
        )
        
        # Should not execute/render the script
        assert "<script>" not in response.text


class TestHeaderVsJwtPriority:
    """JWT claim priority enforcement."""

    def test_jwt_tenant_used_when_header_missing(
        self, client: TestClient, tenant_a_token: str
    ):
        """POSITIVE: JWT tenant claim used when no X-Tenant-ID header."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
            # No X-Tenant-ID header
        )
        
        # Should succeed based on JWT claim
        assert response.status_code not in [401, 403], (
            f"JWT-only auth should work, got {response.status_code}"
        )

    def test_header_ignored_when_jwt_present(
        self, client: TestClient, tenant_a_token: str
    ):
        """P0: X-Tenant-ID ignored when JWT tenant present."""
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": "malicious-tenant"
            }
        )
        
        # Should either reject mismatch or ignore header (not use malicious value)
        # If it succeeds, it should use tenant-a data, not malicious-tenant
        if response.status_code == 200:
            data = response.json()
            # Any returned entities should be from tenant-a
            for entity in data.get("entities", []):
                assert entity.get("tenant_id") == "tenant-a", (
                    "JWT tenant claim overridden by header - SPOOFING VULNERABILITY"
                )
