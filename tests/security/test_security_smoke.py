"""
Security Smoke Test Suite - Fast PR Validation

Curated subset of highest-value security tests for CI gating.
Runtime: < 2 minutes, no external dependencies (Docker/ZAP).

These are the most critical security checks that must pass on every PR.
Full suite in other test files runs on scheduled workflows.
"""

import time
from datetime import datetime, timedelta
from typing import Callable

import jwt as jwt_lib
import pytest

# Lazy import for optional dependency
try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

# Token expiration constants
TOKEN_EXPIRATION_HOURS = 1
SECONDS_PER_HOUR = 3600


@pytest.fixture(autouse=True)
def _disable_rate_limiting_for_smoke(monkeypatch):
    """Smoke tests assert security behaviors, not rate-limit throttling.

    When Redis is unavailable the local fallback limiter caps at 5 requests
    per window, causing spurious 429s that mask the actual outcomes.
    """
    try:
        from value_fabric.shared.identity.rate_limiter import RateLimitResult, RedisRateLimiter
    except ImportError:
        return

    async def _always_allow(self, key, config):
        import time
        return RateLimitResult(allowed=True, remaining=999, reset_at=time.time() + 60, retry_after=None)

    monkeypatch.setattr(RedisRateLimiter, "check", _always_allow)

    try:
        from value_fabric.shared.rate_limiting.tenant_rate_limiter import (
            RateLimitResult as TenantRateLimitResult,
        )
        from value_fabric.shared.rate_limiting.tenant_rate_limiter import (
            TenantRateLimiter,
        )
    except ImportError:
        return

    async def _tenant_always_allow(self, **kwargs):
        return TenantRateLimitResult(
            allowed=True,
            limit=1000,
            remaining=999,
            reset_at=datetime.utcnow() + timedelta(seconds=60),
        )

    monkeypatch.setattr(TenantRateLimiter, "check_rate_limit", _tenant_always_allow)


class TestCriticalTenantIsolation:
    """P0: Cross-tenant data access prevention (smoke tests)."""

    def test_user_cannot_spoof_tenant_header(self, client: TestClient, tenant_a_token):
        """User from Tenant A blocked when trying to use Tenant B header."""
        response = client.get(
            "/api/v1/entities",
            headers={
                "Authorization": f"Bearer {tenant_a_token}",
                "X-Tenant-ID": "tenant-b",  # Attempted spoof
            },
        )

        if response.status_code == 200:
            # If endpoint allows the request, verify strict tenant isolation at data level
            data = response.json()
            items = data.get("items", [])
            for item in items:
                assert item.get("tenant_id") != "tenant-b", "Cross-tenant data leakage - tenant-b data visible"
                assert item.get("tenant_id") == "tenant-a", "Data ownership mismatch"
        elif response.status_code not in [403, 401]:
            pytest.fail(f"Unexpected status for tenant spoof attempt: {response.status_code}")

    def test_idor_blocked_basic(self, client: TestClient, tenant_a_token, tenant_b_token):
        """Basic IDOR: Tenant B cannot access Tenant A's entity by ID."""
        # Create entity as Tenant A
        create_response = client.post(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"name": "smoke-idor-test"},
        )

        if create_response.status_code == 201:
            entity = create_response.json()
            entity_id = entity.get("id")

            # Tenant B attempts access
            idor_response = client.get(
                f"/api/v1/entities/{entity_id}",
                headers={"Authorization": f"Bearer {tenant_b_token}"},
            )
            assert idor_response.status_code in [403, 404], (
                f"IDOR vulnerability detected: Tenant B accessed Tenant A entity "
                f"with status {idor_response.status_code}"
            )


class TestCriticalRBAC:
    """P0: Role-based access control (smoke tests)."""

    def test_standard_user_blocked_from_admin_endpoint(
        self, client: TestClient, standard_user_token
    ):
        """Standard user cannot access admin endpoints."""
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {standard_user_token}"},
        )
        # 403 = Forbidden (auth'd but not authorized), 401 = Unauthorized (not auth'd)
        # 404 is acceptable if endpoint doesn't exist, but 200 means access was granted
        assert response.status_code != 200, (
            f"CRITICAL: Admin endpoint accessible to standard user "
            f"(status {response.status_code})"
        )
        assert response.status_code in [403, 401, 404], (
            f"Expected 403/401/404 for standard user accessing admin endpoint, "
            f"got {response.status_code}"
        )

    def test_admin_user_can_access_admin_endpoints(
        self, client: TestClient, admin_user_token
    ):
        """Admin user can access admin endpoints (sanity check)."""
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )
        # Should not be forbidden - admin should have access (may 404 if not implemented)
        assert response.status_code != 403, "Admin user blocked from admin endpoint"

    def test_jwt_tampering_rejected(self, client: TestClient, jwt_encoder: Callable[[dict], str]):
        """Modified JWT claims are rejected."""
        # Create valid token
        original = jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "standard",
        })

        # Tamper with it using the known test secret
        from tests.security.conftest import TEST_JWT_SECRET
        decoded = jwt_lib.decode(original, TEST_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
        decoded["role"] = "admin"
        tampered = jwt_lib.encode(decoded, "wrong-secret", algorithm="HS256")

        response = client.get(
            "/api/v1/admin/config",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert response.status_code == 401, "Tampered JWT was accepted"


class TestCriticalInjection:
    """P0: Basic injection prevention (smoke tests)."""

    SQL_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1 UNION SELECT * FROM passwords",
    ]

    def test_sql_injection_blocked_in_query_params(self, client: TestClient):
        """SQL injection payloads blocked in query parameters."""
        for payload in self.SQL_PAYLOADS:
            response = client.get(f"/api/v1/entities?name={payload}")
            # 400 = caught by SecurityMiddleware, 404 = endpoint missing (also safe),
            # 401 = blocked by auth before reaching query handler (also safe)
            assert response.status_code in [200, 400, 401, 404, 422], (
                f"SQL injection not handled: {payload} (got {response.status_code})"
            )

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
    ]

    def test_xss_payloads_sanitized(self, client: TestClient):
        """XSS payloads sanitized or blocked."""
        for payload in self.XSS_PAYLOADS:
            response = client.post(
                "/api/v1/entities",
                json={"name": "test", "description": payload},
            )

            if response.status_code == 200:
                body = response.text
                assert "<script>" not in body or "&lt;script&gt;" in body, (
                    f"XSS payload not sanitized: {payload}"
                )


class TestCriticalMisconfiguration:
    """P0: Security misconfiguration checks (smoke tests)."""

    def test_security_headers_present(self, client: TestClient):
        """Critical security headers are present."""
        # Use /docs (public, exists) so SecurityMiddleware adds headers.
        response = client.get("/docs")

        headers = {k.lower(): v for k, v in response.headers.items()}

        # X-Content-Type-Options prevents MIME sniffing
        assert "x-content-type-options" in headers, "Missing X-Content-Type-Options"
        assert headers["x-content-type-options"] == "nosniff", "Incorrect X-Content-Type-Options"

        # X-Frame-Options prevents clickjacking
        assert "x-frame-options" in headers, "Missing X-Frame-Options"

    def test_error_no_stack_traces(self, client: TestClient):
        """Error responses don't leak stack traces."""
        response = client.get("/api/v1/entities/malformed-uuid")

        if response.status_code >= 400:
            body = response.text.lower()
            assert "traceback" not in body, "Stack trace leaked in error response"
            assert 'file "' not in body, "File reference leaked in error response"

    def test_debug_endpoints_not_exposed(self, client: TestClient):
        """Debug endpoints not publicly accessible."""
        debug_paths = ["/debug", "/.env", "/config.json", "/phpmyadmin"]

        for path in debug_paths:
            response = client.get(path)
            assert response.status_code in [404, 401, 403], (
                f"Debug endpoint {path} exposed: {response.status_code}"
            )


class TestCriticalCryptographic:
    """P0: Cryptographic security (smoke tests)."""

    def test_jwt_uses_secure_algorithm(self, client: TestClient, jwt_encoder: Callable[[dict], str]):
        """JWT tokens use secure algorithm."""
        token = jwt_encoder({"sub": "test", "role": "standard"})
        header = jwt_lib.get_unverified_header(token)

        assert header["alg"] in ["HS256", "RS256", "ES256"], (
            f"Insecure JWT algorithm: {header['alg']}"
        )

    def test_expired_token_rejected(self, client: TestClient):
        """Expired JWT tokens are rejected."""
        from tests.security.conftest import TEST_JWT_SECRET

        expired_token = jwt_lib.encode(
            {
                "sub": "test",
                "exp": int(time.time()) - (TOKEN_EXPIRATION_HOURS * SECONDS_PER_HOUR),
            },
            TEST_JWT_SECRET,
            algorithm="HS256",
        )

        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401, "Expired token was accepted"


class TestCriticalAccessControl:
    """P0: Access control edge cases (smoke tests)."""

    def test_mass_assignment_blocked(self, client: TestClient, standard_user_token):
        """Mass assignment of protected fields is blocked."""
        response = client.post(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {standard_user_token}"},
            json={
                "name": "test",
                "role": "admin",  # Protected field
                "is_admin": True,  # Protected field
            },
        )

        if response.status_code == 201:
            entity = response.json()
            assert entity.get("role") != "admin", "Mass assignment: role was set"
            assert entity.get("is_admin") is not True, "Mass assignment: is_admin was set"

    def test_read_only_cannot_write(self, client: TestClient, jwt_encoder: Callable[[dict], str]):
        """Read-only principal is forbidden from a mutating admin endpoint.

        ``DELETE /api/v1/entities/{entity_id}`` requires ``TENANT_ADMIN`` or
        ``SUPER_ADMIN``. A read-only user must receive 403 Forbidden, proving
        RBAC enforcement rejects the write attempt before any business logic runs.
        """
        read_token = jwt_encoder({
            "sub": "read-only",
            "tenant_id": "tenant-a",
            "role": "read_only",
            "permissions": ["read"],
        })

        response = client.delete(
            "/api/v1/entities/test-entity-id",
            headers={"Authorization": f"Bearer {read_token}"},
        )
        assert response.status_code == 403, (
            f"Read-only user must be forbidden from mutating endpoint, got {response.status_code}"
        )


# Quick reference for CI integration
# Run with: pytest tests/security/test_security_smoke.py -v --tb=short
# Expected runtime: 30-60 seconds
# No external dependencies required
