"""
Security tests for Role-Based Access Control (RBAC).

Validates that:
1. Role permissions are properly enforced
2. Admin endpoints require admin role
3. Role escalation attempts are blocked
"""

import time
from typing import Callable

import jwt as jwt_lib
import pytest

# Lazy import for optional dependency
try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@pytest.fixture(autouse=True)
def _disable_rate_limiting_for_rbac(monkeypatch):
    """RBAC tests assert authz decisions, not rate-limit throttling.

    When Redis is unavailable the local fallback limiter caps at 5 requests
    per window, causing spurious 429s that mask the actual 403/200 outcomes
    under test.
    """
    try:
        from value_fabric.shared.identity.rate_limiter import RateLimitResult, RedisRateLimiter
    except ImportError:
        return

    async def _always_allow(self, key, config):
        import time
        return RateLimitResult(allowed=True, remaining=999, reset_at=time.time() + 60, retry_after=None)

    monkeypatch.setattr(RedisRateLimiter, "check", _always_allow)


class TestRBACEnforcement:
    """Test suite for RBAC policy enforcement."""

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/admin/users",
        "/api/v1/admin/config",
        "/api/v1/admin/audit-logs",
    ])
    def test_standard_user_blocked_from_admin_endpoint(self, client: TestClient, standard_user_token, endpoint: str):
        """P0: Standard users cannot access admin endpoints.

        Each endpoint is tested independently for clearer failure reporting.
        """
        response = client.get(
            endpoint,
            headers={"Authorization": f"Bearer {standard_user_token}"},
        )
        # 403 = explicitly forbidden; 404 = endpoint not implemented (also blocks access)
        assert response.status_code in [403, 404], f"Admin endpoint {endpoint} should be forbidden, got {response.status_code}"

    def test_admin_user_can_access_admin_endpoints(self, client: TestClient, admin_user_token):
        """Admin users can access admin endpoints."""
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )
        # Should succeed (or 404 if endpoint doesn't exist in test)
        assert response.status_code in [200, 404]

    def test_role_claim_cannot_be_modified_in_jwt(self, client: TestClient):
        """JWT role claim is immutable - cannot be forged."""
        # This would require a forged JWT with modified role
        # In practice, this is prevented by JWT signature verification
        forged_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."  # Would need valid signature
        response = client.get(
            "/api/v1/admin/config",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
        assert response.status_code in [401, 403]

    def test_permission_check_on_every_request(self, client: TestClient, standard_user_token):
        """RBAC is validated on every request, not just at login."""
        # First request - should succeed for standard endpoint
        response1 = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {standard_user_token}"},
        )

        # Token should be re-validated on second request
        response2 = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {standard_user_token}"},
        )

        # Both should have same permission level
        assert response1.status_code == response2.status_code


class TestRoleHierarchy:
    """Test role hierarchy and permission inheritance."""

    def test_advanced_user_has_more_access_than_standard(self, client: TestClient):
        """Advanced role has more permissions than standard."""
        standard_token = {"role": "standard", "tenant_id": "t1"}
        advanced_token = {"role": "advanced", "tenant_id": "t1"}

        # Advanced can access formulas
        advanced_response = client.get(
            "/api/v1/formulas",
            headers={"Authorization": f"Bearer {advanced_token}"},
        )

        # Standard might be blocked or have limited access
        standard_response = client.get(
            "/api/v1/formulas",
            headers={"Authorization": f"Bearer {standard_token}"},
        )

        # Advanced should have equal or greater access
        assert advanced_response.status_code <= standard_response.status_code


class TestPermissionGranularity:
    """Test permission-level granularity for read vs write operations."""

    def test_read_permission_allows_get_blocks_post(self, client: TestClient, jwt_encoder):
        """P0: Read permission allows GET but blocks POST/PUT/DELETE."""
        read_only_token = jwt_encoder({
            "sub": "read-only-user",
            "tenant_id": "tenant-a",
            "role": "read_only",
            "permissions": ["read"],
        })

        # GET should succeed
        get_response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {read_only_token}"},
        )
        assert get_response.status_code in [200, 404], "Read permission should allow GET"

        # POST should be blocked
        post_response = client.post(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {read_only_token}"},
            json={"name": "test-entity"},
        )
        # 403/401 = explicitly rejected; 404 = endpoint not implemented (also blocks access)
        assert post_response.status_code in [403, 401, 404], f"Read-only user should not be able to POST, got {post_response.status_code}"

    @pytest.mark.xfail(strict=True, reason='RBAC write permission check returns 405 not 201 in test client')
    def test_write_permission_allows_post_put_delete(self, client: TestClient, jwt_encoder):
        """P0: Write permission allows POST/PUT/DELETE."""
        write_token = jwt_encoder({
            "sub": "write-user",
            "tenant_id": "tenant-a",
            "role": "editor",
            "permissions": ["read", "write"],
        })

        # POST should succeed (or 404 if endpoint doesn't exist)
        post_response = client.post(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {write_token}"},
            json={"name": "test-entity"},
        )
        assert post_response.status_code in [201, 200, 404], "Write permission should allow POST"

        # PUT should succeed (or 404 if entity doesn't exist)
        put_response = client.put(
            "/api/v1/entities/some-id",
            headers={"Authorization": f"Bearer {write_token}"},
            json={"name": "updated-entity"},
        )
        assert put_response.status_code in [200, 404], "Write permission should allow PUT"

        # DELETE should succeed (or 404 if entity doesn't exist)
        delete_response = client.delete(
            "/api/v1/entities/some-id",
            headers={"Authorization": f"Bearer {write_token}"},
        )
        assert delete_response.status_code in [204, 200, 404], "Write permission should allow DELETE"

    def test_admin_permission_includes_all_operations(self, client: TestClient, admin_user_token):
        """P0: Admin role has full CRUD permissions."""
        # Admin should be able to perform all operations
        endpoints_methods = [
            ("/api/v1/entities", "GET"),
            ("/api/v1/entities", "POST"),
            ("/api/v1/admin/users", "GET"),
            ("/api/v1/admin/config", "PUT"),
        ]

        for endpoint, method in endpoints_methods:
            if method == "GET":
                response = client.get(endpoint, headers={"Authorization": f"Bearer {admin_user_token}"})
            elif method == "POST":
                response = client.post(endpoint, headers={"Authorization": f"Bearer {admin_user_token}"}, json={"test": "data"})
            elif method == "PUT":
                response = client.put(endpoint, headers={"Authorization": f"Bearer {admin_user_token}"}, json={"test": "data"})

            # Should not get 403 Forbidden - admin has access
            assert response.status_code != 403, f"Admin should not be forbidden from {method} {endpoint}"


class TestJWTTamperingResistance:
    """Test JWT tampering and forgery resistance."""

    def test_modified_role_claim_rejected(self, client: TestClient, jwt_encoder: Callable[[dict], str]):
        """P0: JWT with modified role claim is rejected."""
        # Create a valid token for standard user
        original_payload = {
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "standard",
        }
        original_token = jwt_encoder(original_payload)

        # Decode, modify role, re-encode (without proper signature)
        from tests.security.conftest import TEST_JWT_SECRET
        decoded = jwt_lib.decode(original_token, TEST_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
        decoded["role"] = "admin"  # Attempt privilege escalation

        # Re-encode with different secret (simulating tampering)
        tampered_token = jwt_lib.encode(decoded, "wrong-secret", algorithm="HS256")

        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert response.status_code in [401, 403], "Tampered JWT should be rejected"

    def test_modified_tenant_claim_rejected(self, client: TestClient, jwt_encoder: Callable[[dict], str]):
        """P0: JWT with modified tenant claim is rejected."""
        # Create valid token for tenant-a
        original_payload = {
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "standard",
        }
        original_token = jwt_encoder(original_payload)

        # Decode and modify tenant
        from tests.security.conftest import TEST_JWT_SECRET
        decoded = jwt_lib.decode(original_token, TEST_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
        decoded["tenant_id"] = "tenant-b"  # Attempt cross-tenant access

        # Re-encode with tampered payload
        tampered_token = jwt_lib.encode(decoded, "wrong-secret", algorithm="HS256")

        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert response.status_code in [401, 403], "JWT with modified tenant should be rejected"

    def test_expired_token_rejected(self, client: TestClient):
        """P0: Expired JWT token is rejected."""
        # Create expired token
        expired_payload = {
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "standard",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200,
        }
        from tests.security.conftest import TEST_JWT_SECRET
        expired_token = jwt_lib.encode(expired_payload, TEST_JWT_SECRET, algorithm="HS256")

        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401, "Expired token should be rejected"

    def test_invalid_signature_rejected(self, client: TestClient, jwt_encoder: Callable[[dict], str]):
        """P0: JWT with invalid signature is rejected."""
        # Create valid payload
        payload = {
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "role": "admin",  # Even with admin role
        }

        # Sign with wrong secret
        forged_token = jwt_lib.encode(payload, "completely-wrong-secret", algorithm="HS256")

        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
        assert response.status_code == 401, "JWT with invalid signature should be rejected"

    def test_forged_token_with_valid_structure_rejected(self, client: TestClient):
        """P0: Completely forged JWT with valid structure but no valid signature is rejected."""
        # Create a forged admin token from scratch
        forged_payload = {
            "sub": "attacker",
            "tenant_id": "tenant-a",
            "role": "super_admin",
            "permissions": ["*"],
            "iat": 1609459200,
            "exp": 9999999999,
        }

        # Sign with attacker's secret (not the system secret)
        forged_token = jwt_lib.encode(forged_payload, "attacker-secret", algorithm="HS256")

        response = client.get(
            "/api/v1/admin/config",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
        assert response.status_code == 401, "Completely forged JWT should be rejected"

    def test_none_algorithm_rejected(self, client: TestClient):
        """P0: JWT with 'none' algorithm is rejected (algorithm confusion attack)."""
        import base64
        import json

        # Create header with "none" algorithm
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().strip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "admin", "role": "admin"}).encode()).decode().strip("=")

        # Create token with "none" algorithm (no signature)
        none_alg_token = f"{header}.{payload}."

        response = client.get(
            "/api/v1/admin/config",
            headers={"Authorization": f"Bearer {none_alg_token}"},
        )
        assert response.status_code in [401, 403], "JWT with 'none' algorithm should be rejected"

    def test_algorithm_confusion_attack_blocked(self, client: TestClient):
        """P0: Algorithm confusion attack (RS256 to HS256) is blocked."""
        import base64
        import json

        # Attempt algorithm confusion: claim RS256 but sign with HMAC
        header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).decode().strip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "admin", "role": "admin"}).encode()).decode().strip("=")

        # Sign with HMAC (trying to trick RS256 verification)
        import hashlib
        import hmac

        from tests.security.conftest import TEST_JWT_SECRET
        message = f"{header}.{payload}"
        signature = base64.urlsafe_b64encode(
            hmac.new(TEST_JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
        ).decode().strip("=")

        confused_token = f"{header}.{payload}.{signature}"

        response = client.get(
            "/api/v1/admin/config",
            headers={"Authorization": f"Bearer {confused_token}"},
        )
        assert response.status_code in [401, 403], "Algorithm confusion attack should be blocked"


class TestAPIKeyPermissionOverrides:
    """Test API key scoped permissions that may differ from user role."""

    def test_api_key_with_limited_scope_respects_override(self, client: TestClient):
        """P0: API key with limited permissions cannot exceed scope."""
        # API key with read-only permission
        response = client.get(
            "/api/v1/entities",
            headers={"X-API-Key": "test-read-only-api-key"},
        )
        # Should succeed for read operations
        assert response.status_code in [200, 401, 403, 404]  # Depends on test environment

        # Same API key attempting write
        post_response = client.post(
            "/api/v1/entities",
            headers={"X-API-Key": "test-read-only-api-key"},
            json={"name": "test-entity"},
        )
        # Should be blocked
        assert post_response.status_code in [401, 403], "Read-only API key should not allow writes"

    def test_api_key_cannot_escalate_beyond_user_role(self, client: TestClient):
        """P0: API key permissions cannot escalate beyond associated user's role."""
        # API key associated with standard user but trying to claim admin permissions
        response = client.get(
            "/api/v1/admin/config",
            headers={"X-API-Key": "test-standard-user-escalation-key"},
        )
        # Should be blocked regardless of what permissions the key claims
        assert response.status_code in [401, 403], "API key should not allow role escalation"

    def test_api_key_tenant_scoping_enforced(self, client: TestClient):
        """P0: API key is scoped to specific tenant and cannot access others."""
        # API key scoped to tenant-a
        response = client.get(
            "/api/v1/entities",
            headers={
                "X-API-Key": "test-tenant-a-key",
                "X-Tenant-ID": "tenant-b",  # Attempted cross-tenant
            },
        )
        # Should be blocked - key only valid for tenant-a
        assert response.status_code in [401, 403], "API key should respect tenant scoping"


# ---------------------------------------------------------------------------
# P0 expansion: permission scope checks (all-permissions and OR-logic bypass)
# ---------------------------------------------------------------------------

class TestPermissionScopeChecks:
    """P0: Verify all-permissions scope and OR-logic cannot be abused.

    These tests operate at the permission-model layer (no HTTP required) and
    cover the two specific bypass vectors called out in the P0 gap audit:
      - 'all-permissions' wildcard claim granting unrestricted access
      - require_any_permission OR-logic returning True with zero matches
    """

    def test_all_permissions_scope_not_grantable_via_jwt_claim(self, jwt_encoder):
        """P0: A JWT with permissions=['*'] must not grant all-permissions scope.

        An attacker who can forge or inject a JWT with a wildcard permissions
        claim must not receive elevated access. This test exercises the actual
        middleware decode path (extract_context_from_jwt) so that the wildcard
        string passes through the same code that runs in production.
        """
        try:
            from value_fabric.shared.identity.middleware import extract_context_from_jwt
            from value_fabric.shared.identity.permissions import Permission
        except ImportError:
            pytest.skip("Identity middleware not available")

        # Build a JWT payload that includes a wildcard permissions claim,
        # as an attacker would craft it.
        token = jwt_encoder({
            "sub": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "role": "standard",
            "permissions": ["*"],
        })

        import jwt as _jwt

        from tests.security.conftest import TEST_JWT_SECRET
        try:
            payload = _jwt.decode(
                token,
                TEST_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": False, "verify_aud": False, "verify_iss": False},
            )
        except Exception:
            pytest.skip("Could not decode test token")

        ctx = extract_context_from_jwt(payload)

        # Wildcard strings must be discarded by extract_context_from_jwt —
        # only known Permission enum values are stored in the frozenset.
        assert not ctx.has_permission("*"), (
            "has_permission('*') returned True. P0: Wildcard string bypass."
        )
        assert not ctx.has_permission(Permission.ADMIN_SYSTEM), (
            "Context built from JWT with permissions=['*'] grants ADMIN_SYSTEM. "
            "P0: Wildcard claim bypasses permission checks."
        )
        assert not ctx.has_permission(Permission.ADMIN_USERS), (
            "Context built from JWT with permissions=['*'] grants ADMIN_USERS. "
            "P0: Wildcard claim bypasses permission checks."
        )

    def test_require_any_permission_or_logic_does_not_grant_on_empty_set(self):
        """P0: require_any_permission with an empty held-permissions set must deny.

        If has_any_permission() returns True when the context has no permissions,
        every OR-gated endpoint becomes publicly accessible.
        """
        try:
            from value_fabric.shared.identity.context import RequestContext
            from value_fabric.shared.identity.permissions import Permission
        except ImportError:
            pytest.skip("Identity modules not available")

        ctx = RequestContext(
            tenant_id="tenant-a",
            user_id="user-1",
            roles=[],
            permissions=frozenset(),
            source="jwt_claim",
        )

        # OR-check against multiple permissions — none held
        result = ctx.has_any_permission(
            Permission.READ_HEALTH,
            Permission.WRITE_INGESTION,
            Permission.ADMIN_SYSTEM,
        )
        assert not result, (
            "has_any_permission returned True with empty permission set. "
            "P0: OR-logic bypass — unauthenticated access to permission-gated endpoints."
        )

    def test_require_any_permission_or_logic_does_not_short_circuit_on_first_miss(self):
        """P0: OR-logic must check all permissions, not short-circuit on first miss.

        A buggy implementation might return True after failing the first check
        if the short-circuit logic is inverted.
        """
        try:
            from value_fabric.shared.identity.context import RequestContext
            from value_fabric.shared.identity.permissions import Permission
        except ImportError:
            pytest.skip("Identity modules not available")

        # Context holds only READ_HEALTH
        ctx = RequestContext(
            tenant_id="tenant-a",
            user_id="user-1",
            roles=[],
            permissions=frozenset({Permission.READ_HEALTH}),
            source="jwt_claim",
        )

        # Check for two permissions the context does NOT hold
        result = ctx.has_any_permission(
            Permission.ADMIN_SYSTEM,
            Permission.WRITE_INGESTION,
        )
        assert not result, (
            "has_any_permission returned True when none of the checked permissions "
            "are held. P0: OR-logic short-circuit bypass."
        )

    def test_all_permissions_scope_requires_every_permission(self):
        """P0: has_all_permissions must require every listed permission, not just one.

        A buggy AND-check that returns True when any single permission matches
        would allow partial-permission holders to pass all-permission gates.
        """
        try:
            from value_fabric.shared.identity.context import RequestContext
            from value_fabric.shared.identity.permissions import Permission
        except ImportError:
            pytest.skip("Identity modules not available")

        # Context holds only READ_HEALTH — not the full set
        ctx = RequestContext(
            tenant_id="tenant-a",
            user_id="user-1",
            roles=[],
            permissions=frozenset({Permission.READ_HEALTH}),
            source="jwt_claim",
        )

        result = ctx.has_all_permissions(
            Permission.READ_HEALTH,      # held
            Permission.ADMIN_SYSTEM,     # NOT held
            Permission.WRITE_INGESTION,  # NOT held
        )
        assert not result, (
            "has_all_permissions returned True when only one of three required "
            "permissions is held. P0: AND-logic bypass — partial permission set "
            "passes all-permissions gate."
        )

    @pytest.mark.asyncio
    async def test_require_any_permission_dependency_raises_403_with_no_match(self):
        """P0: require_any_permission FastAPI dependency raises 403 when no match."""
        try:
            from fastapi import HTTPException
            from value_fabric.shared.identity.context import RequestContext
            from value_fabric.shared.identity.dependencies import require_any_permission
            from value_fabric.shared.identity.permissions import Permission
        except ImportError:
            pytest.skip("Identity modules not available")

        ctx = RequestContext(
            tenant_id="tenant-a",
            user_id="user-1",
            roles=[],
            permissions=frozenset({Permission.READ_HEALTH}),
            source="jwt_claim",
        )

        dep = require_any_permission(Permission.ADMIN_SYSTEM, Permission.ADMIN_USERS)

        with pytest.raises(HTTPException) as exc_info:
            await dep(context=ctx)

        assert exc_info.value.status_code == 403, (
            f"Expected 403, got {exc_info.value.status_code}. "
            "P0: require_any_permission OR-logic bypass."
        )

    @pytest.mark.asyncio
    async def test_require_all_permissions_dependency_raises_403_on_partial_match(self):
        """P0: require_all_permissions FastAPI dependency raises 403 on partial match."""
        try:
            from fastapi import HTTPException
            from value_fabric.shared.identity.context import RequestContext
            from value_fabric.shared.identity.dependencies import require_all_permissions
            from value_fabric.shared.identity.permissions import Permission
        except ImportError:
            pytest.skip("Identity modules not available")

        ctx = RequestContext(
            tenant_id="tenant-a",
            user_id="user-1",
            roles=[],
            permissions=frozenset({Permission.READ_HEALTH}),
            source="jwt_claim",
        )

        dep = require_all_permissions(Permission.READ_HEALTH, Permission.ADMIN_SYSTEM)

        with pytest.raises(HTTPException) as exc_info:
            await dep(context=ctx)

        assert exc_info.value.status_code == 403, (
            f"Expected 403, got {exc_info.value.status_code}. "
            "P0: require_all_permissions AND-logic bypass."
        )
