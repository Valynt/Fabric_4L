"""Authentication Boundary Security Tests — P0 Critical Gap Remediation

Validates all authentication boundaries: missing auth, invalid/expired/malformed tokens,
role-based access control, and cross-user resource access.

Production Invariant: No unauthenticated or improperly authenticated access to protected resources.

Author: Autonomous Test Assurance Agent
Date: 2026-04-29
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

try:
    from fastapi.testclient import TestClient
    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False


pytestmark = [
    pytest.mark.skipif(not TESTCLIENT_AVAILABLE, reason="FastAPI TestClient not available"),
    pytest.mark.security,
    pytest.mark.auth_boundaries,
]


class TestMissingAuthentication:
    """NEGATIVE: Missing authentication is rejected with 401."""

    def test_no_auth_header_rejected(self, client: TestClient):
        """P0: Request without Authorization header gets 401."""
        response = client.get("/api/v1/entities")
        
        assert response.status_code == 401, (
            f"Missing auth should return 401, got {response.status_code}. "
            "P0: Unauthenticated access allowed."
        )
        
        data = response.json()
        assert data.get("error") == "authentication_required", (
            f"Expected 'authentication_required' error, got {data.get('error')}"
        )
        assert "WWW-Authenticate" in response.headers, (
            "401 response must include WWW-Authenticate header per RFC 7235"
        )

    def test_empty_auth_header_rejected(self, client: TestClient):
        """P0: Empty Authorization header gets 401."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": ""}
        )
        
        assert response.status_code == 401, (
            f"Empty auth header should return 401, got {response.status_code}"
        )

    def test_whitespace_auth_header_rejected(self, client: TestClient):
        """P0: Whitespace-only Authorization header gets 401."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": "   "}
        )
        
        assert response.status_code == 401, (
            f"Whitespace auth header should return 401, got {response.status_code}"
        )


class TestInvalidToken:
    """NEGATIVE: Invalid tokens are rejected with 401."""

    def test_invalid_token_format_rejected(self, client: TestClient):
        """P0: Malformed token gets 401."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": "Bearer invalid-token-format"}
        )
        
        assert response.status_code == 401, (
            f"Invalid token should return 401, got {response.status_code}. "
            "P0: Invalid token accepted."
        )

    def test_wrong_token_prefix_rejected(self, client: TestClient):
        """P0: Token without 'Bearer' prefix gets 401."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": "Basic dXNlcjpwYXNz"}  # Basic auth
        )
        
        assert response.status_code == 401, (
            f"Non-Bearer token should return 401, got {response.status_code}"
        )

    def test_gibberish_token_rejected(self, client: TestClient):
        """P0: Completely random string as token gets 401."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": "Bearer xyz123!@#notavalidtoken"}
        )
        
        assert response.status_code == 401, (
            f"Gibberish token should return 401, got {response.status_code}"
        )

    def test_sql_injection_in_token_blocked(self, client: TestClient):
        """P0: SQL injection attempt in token blocked."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": "Bearer ' OR '1'='1"}
        )
        
        assert response.status_code == 401, (
            f"SQL injection in token should return 401, got {response.status_code}"
        )

    def test_xss_in_token_sanitized(self, client: TestClient):
        """P0: XSS attempt in token sanitized."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": "Bearer <script>alert('xss')</script>"}
        )
        
        assert response.status_code == 401
        assert "<script>" not in response.text, (
            "XSS payload should not be reflected in response"
        )


class TestExpiredToken:
    """NEGATIVE: Expired tokens are rejected with 401."""

    @pytest.fixture
    def expired_token(self, jwt_encoder) -> str:
        """Create an expired JWT token."""
        return jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "standard",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        })

    def test_expired_token_rejected(self, client: TestClient, expired_token: str):
        """P0: Expired JWT token gets 401."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401, (
            f"Expired token should return 401, got {response.status_code}. "
            "P0: Expired token accepted - SECURITY VULNERABILITY."
        )
        
        data = response.json()
        assert "expired" in data.get("detail", "").lower() or "token" in data.get("detail", "").lower(), (
            "Error message should indicate token issue"
        )

    def test_token_expired_24h_ago_rejected(self, client: TestClient, jwt_encoder):
        """P0: Token expired 24 hours ago is rejected."""
        old_token = jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "standard",
            "exp": datetime.now(timezone.utc) - timedelta(hours=24),
        })
        
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {old_token}"}
        )
        
        assert response.status_code == 401, (
            f"24h expired token should return 401, got {response.status_code}"
        )


class TestMalformedToken:
    """NEGATIVE: Malformed tokens are rejected with 401."""

    def test_truncated_token_rejected(self, client: TestClient):
        """P0: Truncated JWT (missing signature) gets 401."""
        # JWT with 2 parts instead of 3 (header.payload only)
        truncated = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyJ9"
        
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {truncated}"}
        )
        
        assert response.status_code == 401, (
            f"Truncated token should return 401, got {response.status_code}"
        )

    def test_extra_parts_token_rejected(self, client: TestClient):
        """P0: JWT with extra parts gets 401."""
        # JWT with 4 parts
        extra_parts = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn9.signature.extra"
        
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {extra_parts}"}
        )
        
        assert response.status_code == 401, (
            f"Extra-parts token should return 401, got {response.status_code}"
        )

    def test_invalid_base64_token_rejected(self, client: TestClient):
        """P0: Invalid base64 in JWT gets 401."""
        invalid_base64 = "not-valid-base64!!!.not-valid.not-valid"
        
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {invalid_base64}"}
        )
        
        assert response.status_code == 401, (
            f"Invalid base64 token should return 401, got {response.status_code}"
        )

    def test_empty_payload_token_rejected(self, client: TestClient):
        """P0: JWT with empty payload gets 401."""
        # header: {"alg":"none"} -> eyJhbGciOiJub25lIn0
        # payload: {} -> e30
        # signature: (empty)
        empty_payload = "eyJhbGciOiJub25lIn0.e30."
        
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {empty_payload}"}
        )
        
        assert response.status_code == 401, (
            f"Empty payload token should return 401, got {response.status_code}"
        )


class TestWrongRole:
    """NEGATIVE: Wrong role gets 403 Forbidden."""

    @pytest.fixture
    def standard_user_token(self, jwt_encoder) -> str:
        """JWT for standard user (non-admin)."""
        return jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "standard",
        })

    def test_standard_user_cannot_access_admin_endpoints(
        self, client: TestClient, standard_user_token: str
    ):
        """P0: Standard user accessing admin endpoint gets 403."""
        admin_endpoints = [
            "/api/admin/users",
            "/api/admin/config",
            "/api/admin/audit-logs",
            "/api/admin/tenants",
        ]
        
        for endpoint in admin_endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {standard_user_token}"}
            )
            
            assert response.status_code == 403, (
                f"Standard user should get 403 from {endpoint}, got {response.status_code}. "
                f"P0: Admin endpoint not protected."
            )

    def test_standard_user_cannot_delete_entities(
        self, client: TestClient, standard_user_token: str
    ):
        """P0: Standard user cannot delete (admin operation)."""
        response = client.delete(
            "/api/v1/entities/some-entity-id",
            headers={"Authorization": f"Bearer {standard_user_token}"}
        )
        
        assert response.status_code == 403, (
            f"Standard user delete should return 403, got {response.status_code}"
        )


class TestCrossUserAccess:
    """NEGATIVE: User cannot access another user's resources."""

    @pytest.fixture
    def user_a_token(self, jwt_encoder) -> str:
        """JWT for user A."""
        return jwt_encoder({
            "sub": "user-a",
            "tenant_id": "tenant-a",
            "role": "standard",
        })

    @pytest.fixture
    def user_b_token(self, jwt_encoder) -> str:
        """JWT for user B."""
        return jwt_encoder({
            "sub": "user-b",
            "tenant_id": "tenant-a",  # Same tenant
            "role": "standard",
        })

    def test_user_cannot_access_other_user_resource(
        self, client: TestClient, user_a_token: str
    ):
        """P0: User A cannot access User B's private resource (IDOR)."""
        # Attempt to access resource owned by user-b
        response = client.get(
            "/api/v1/user/user-b/private-data",
            headers={"Authorization": f"Bearer {user_a_token}"}
        )
        
        # Should be 403 or 404, never 200 with data
        assert response.status_code in [403, 404], (
            f"Cross-user access should be blocked, got {response.status_code}. "
            "P0: IDOR vulnerability - users can access each other's data."
        )


class TestAdminOnlyActions:
    """POSITIVE + NEGATIVE: Admin-only actions require admin role."""

    @pytest.fixture
    def admin_token(self, jwt_encoder) -> str:
        """JWT for admin user."""
        return jwt_encoder({
            "sub": "admin-123",
            "tenant_id": "tenant-a",
            "role": "admin",
        })

    def test_admin_can_access_admin_endpoints(self, client: TestClient, admin_token: str):
        """POSITIVE: Admin can access admin endpoints."""
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should succeed (or 404 if endpoint doesn't exist, but not 401/403)
        assert response.status_code not in [401, 403], (
            f"Admin should access admin endpoint, got {response.status_code}"
        )

    def test_admin_can_delete_entities(self, client: TestClient, admin_token: str):
        """POSITIVE: Admin can perform delete operations."""
        # This is a positive test - it may fail if entity doesn't exist
        # but it should NOT fail with 403
        response = client.delete(
            "/api/v1/entities/non-existent-id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should be 404 (not found) or 204 (deleted), NOT 403
        assert response.status_code != 403, (
            "Admin should not get 403 on delete operation"
        )


class TestValidAuthentication:
    """POSITIVE: Valid authentication succeeds."""

    def test_valid_token_succeeds(self, client: TestClient, tenant_a_token: str):
        """POSITIVE: Valid JWT token allows access."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        
        # Should not be 401 or 403
        assert response.status_code not in [401, 403], (
            f"Valid token should not get auth error, got {response.status_code}"
        )

    def test_valid_token_with_correct_tenant(self, client: TestClient, tenant_a_token: str):
        """POSITIVE: Token with correct tenant claim works."""
        response = client.get(
            "/api/v1/user/profile",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("tenant_id") == "tenant-a", (
                "Response should contain correct tenant"
            )


class TestJWTExpirationEdgeCases:
    """NEGATIVE: JWT expiration and clock skew edge cases are rejected."""

    def test_expired_jwt_rejected(self, client: TestClient, jwt_encoder):
        """P1: JWT with exp in the past is rejected with 401."""
        import time
        now = int(time.time())
        expired_token = jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "standard",
            "iat": now - 7200,
            "exp": now - 3600,
        })
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401, (
            f"Expired JWT should return 401, got {response.status_code}. "
            "P1: Expired token accepted."
        )

    def test_future_issued_jwt_rejected(self, client: TestClient, jwt_encoder):
        """P1: JWT with iat in the future is rejected with 401."""
        import time
        now = int(time.time())
        future_token = jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "standard",
            "iat": now + 3600,
            "exp": now + 7200,
        })
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {future_token}"}
        )
        assert response.status_code == 401, (
            f"Future-issued JWT should return 401, got {response.status_code}. "
            "P1: Future token accepted (clock skew vulnerability)."
        )

    @pytest.mark.service_required
    def test_jwt_missing_sub_claim_rejected(self, client: TestClient, jwt_encoder):
        """P1: JWT without required 'sub' claim is rejected.

        NOTE: This test documents the invariant that tokens missing the 'sub' claim
        must be rejected. If the test app does not enforce this at the middleware layer,
        the route dependency (e.g. get_current_user) must reject it. Re-run against
        the live L4 service to verify production enforcement.
        """
        import time
        now = int(time.time())
        no_sub_token = jwt_encoder({
            "tenant_id": "tenant-a",
            "role": "standard",
            "iat": now,
            "exp": now + 3600,
        })
        response = client.get(
            "/api/v1/user/profile",
            headers={"Authorization": f"Bearer {no_sub_token}"}
        )
        assert response.status_code in [401, 403], (
            f"JWT missing sub should return 401/403, got {response.status_code}. "
            "P1: Token with missing claims accepted."
        )
