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

# Canonical UUID tenant identifiers. GovernanceMiddleware validates that
# X-Tenant-ID headers are well-formed UUIDs before comparing them to the JWT
# tenant claim, so tests must use UUIDs (not legacy "tenant-a" strings) when
# exercising the header-vs-JWT consistency path.
_TENANT_A_UUID = "11111111-1111-1111-1111-111111111111"
_TENANT_B_UUID = "22222222-2222-2222-2222-222222222222"


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
            "tenant_id": _TENANT_A_UUID,
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
                "X-Tenant-ID": _TENANT_B_UUID,  # Attempted spoof
            },
        )

        # Should reject the mismatch
        assert response.status_code == 403, (
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
                "X-Tenant-ID": _TENANT_A_UUID,  # Matches JWT
            },
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
                "X-Tenant-ID": "../../../etc/passwd",  # Path traversal attempt
            },
        )

        # Malformed X-Tenant-ID fails identity resolution before the JWT is used.
        assert response.status_code == 401, (
            f"Invalid tenant header format should be rejected, got {response.status_code}"
        )

    def test_sql_injection_in_tenant_header_blocked(self, client: TestClient, tenant_a_token: str):
        """SQL injection in X-Tenant-ID blocked."""
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": "tenant-a' OR '1'='1",
            },
        )

        # Non-UUID header is rejected as unauthenticated.
        assert response.status_code == 401, (
            "SQL injection in tenant header should be blocked"
        )

    def test_xss_in_tenant_header_sanitized(self, client: TestClient, tenant_a_token: str):
        """XSS attempt in X-Tenant-ID sanitized."""
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": "<script>alert('xss')</script>",
            },
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
                "X-Tenant-ID": _TENANT_B_UUID,
            },
        )

        # Mismatched header is rejected; JWT claim remains authoritative.
        assert response.status_code == 403, (
            f"Expected 403 for header/JWT mismatch, got {response.status_code}"
        )


class TestKillSwitchFailSafe:
    """GovernanceMiddleware Redis-unavailable fail-safe behavior."""

    def test_redis_unavailable_returns_503(
        self, client: TestClient, tenant_a_token: str, monkeypatch
    ):
        """P0: When Redis is unavailable, kill switch returns 503 (fail-safe)."""
        from value_fabric.shared.tenant_kill_switch import (
            TenantKillSwitch,
            TenantSuspensionStatus,
        )

        # The shared security conftest intentionally treats UNKNOWN as ACTIVE for
        # auth/RBAC smoke tests. For this kill-switch-specific test we need the
        # real UNKNOWN -> 503 mapping, so override check_status locally.
        async def _unknown_status(_self, _tenant_id: str) -> TenantSuspensionStatus:
            return TenantSuspensionStatus.UNKNOWN

        monkeypatch.setattr(TenantKillSwitch, "check_status", _unknown_status)

        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        # The _mismatch_app fixture has rate_limiter=None, so Redis is unreachable.
        # The middleware MUST fail safe with 503 rather than allow the request.
        assert response.status_code == 503, (
            f"Expected 503 when Redis is unavailable, got {response.status_code}. "
            "Fail-open would be a security vulnerability."
        )
        data = response.json()
        assert data.get("error") == "tenant_status_unavailable", (
            f"Expected error code 'tenant_status_unavailable', got {data.get('error')}"
        )

    def test_redis_available_allows_active_tenant(self, tenant_a_token: str):
        """P0: When Redis reports ACTIVE, the request proceeds."""
        from value_fabric.shared.identity.middleware import GovernanceMiddleware
        from value_fabric.shared.identity.rate_limiter import RateLimitResult

        class _FakeRedisClient:
            async def sismember(self, key: str, member: str) -> bool:
                return False  # tenant is not in the suspended set -> ACTIVE

        class _FakeRateLimiter:
            redis_client = _FakeRedisClient()

            async def check(self, key: str, config: object) -> RateLimitResult:
                return RateLimitResult(
                    allowed=True, remaining=100, reset_at=0.0, retry_after=None
                )

        app = FastAPI()
        app.add_middleware(GovernanceMiddleware, rate_limiter=_FakeRateLimiter())

        @app.get("/api/v1/entities")
        def entities(request: Request):
            ctx = getattr(request.state, "governance_context", None)
            if ctx is None:
                raise HTTPException(status_code=401, detail="Unauthenticated")
            return {"items": [], "tenant_id": str(ctx.tenant_id)}

        with TestClient(app, raise_server_exceptions=False) as active_client:
            response = active_client.get(
                "/api/v1/entities",
                headers={"Authorization": f"Bearer {tenant_a_token}"},
            )

        assert response.status_code == 200, (
            f"Expected 200 for active tenant when Redis is available, got {response.status_code}"
        )
        data = response.json()
        assert data.get("tenant_id") == _TENANT_A_UUID, (
            f"Expected {_TENANT_A_UUID}, got {data.get('tenant_id')}"
        )
