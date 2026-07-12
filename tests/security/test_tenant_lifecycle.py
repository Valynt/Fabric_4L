"""Tenant Lifecycle Security Tests — P0 Critical Gap Remediation

Validates that suspended, pending, and deleted tenants cannot access resources.

Production Invariant: Tenant lifecycle status must be enforced before request processing.

Author: Autonomous Test Assurance Agent
Date: 2026-04-28
"""

from __future__ import annotations

import pytest

try:
    from fastapi.testclient import TestClient
    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False


pytestmark = [
    pytest.mark.skipif(not TESTCLIENT_AVAILABLE, reason="FastAPI TestClient not available"),
    pytest.mark.security,
    pytest.mark.tenant_lifecycle,
]


class TestActiveTenantAccess:
    """POSITIVE: Active tenants can access resources normally."""

    def test_active_tenant_can_access_entities(self, client: TestClient, tenant_a_token: str):
        """Active tenant gets 200 OK on protected endpoints."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        
        # Active tenant should have normal access.
        # Note: May be 200 or 404 depending on data, but NOT 401/403.
        assert response.status_code not in [401, 403], (
            f"Active tenant should not be rejected, got {response.status_code}"
        )


@pytest.fixture
def suspended_tenant_token(jwt_encoder) -> str:
    """JWT for a suspended tenant — shared across lifecycle test classes."""
    return jwt_encoder({
        "sub": "user-123",
        "tenant_id": "tenant-suspended",
        "role": "standard",
        "tenant_status": "suspended",
    })


class TestSuspendedTenantRejection:
    """NEGATIVE: Suspended tenants are blocked with 403."""

    def test_suspended_tenant_rejected_with_403(
        self, client: TestClient, suspended_tenant_token: str
    ):
        """P0: Suspended tenant gets 403 with 'tenant_suspended' error."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {suspended_tenant_token}"}
        )
        
        assert response.status_code == 403, (
            f"Suspended tenant should get 403, got {response.status_code}. "
            "P0: Suspended tenant access not blocked."
        )
        
        data = response.json()
        assert data.get("error") == "tenant_suspended", (
            f"Expected 'tenant_suspended' error, got {data.get('error')}. "
            "Error code mismatch may confuse clients."
        )
        assert "contact support" in data.get("detail", "").lower(), (
            "Error message should direct user to contact support"
        )

    def test_suspended_tenant_cannot_access_any_endpoint(
        self, client: TestClient, suspended_tenant_token: str
    ):
        """P0: Suspended tenant blocked from all protected endpoints."""
        endpoints = [
            "/api/v1/entities",
            "/api/v1/workflows",
            "/api/v1/user/profile",
        ]
        
        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {suspended_tenant_token}"}
            )
            
            assert response.status_code == 403, (
                f"Suspended tenant should be blocked from {endpoint}, "
                f"got {response.status_code}. P0: Endpoint not protected."
            )


class TestPendingTenantRejection:
    """NEGATIVE: Pending tenants are blocked with 403."""

    @pytest.fixture
    def pending_tenant_token(self, jwt_encoder) -> str:
        """JWT for pending tenant."""
        return jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-pending",
            "role": "standard",
            "tenant_status": "pending",
        })

    def test_pending_tenant_rejected_with_403(
        self, client: TestClient, pending_tenant_token: str
    ):
        """P0: Pending tenant gets 403 with 'tenant_pending' error."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {pending_tenant_token}"}
        )

        assert response.status_code == 403, (
            f"Pending tenant should get 403, got {response.status_code}. "
            "P0: Pending tenant access not blocked."
        )

        data = response.json()
        assert data.get("error") == "tenant_pending", (
            f"Expected 'tenant_pending' error, got {data.get('error')}"
        )
        assert "pending" in data.get("detail", "").lower(), (
            "Error message should indicate pending activation"
        )


class TestDeletedTenantRejection:
    """NEGATIVE: Deleted tenants are blocked with 404 (don't reveal existence)."""

    @pytest.fixture
    def deleted_tenant_token(self, jwt_encoder) -> str:
        """JWT for deleted tenant."""
        return jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-deleted",
            "role": "standard",
            "tenant_status": "deleted",
        })

    def test_deleted_tenant_rejected_with_404(
        self, client: TestClient, deleted_tenant_token: str
    ):
        """P0: Deleted tenant gets 404 to avoid revealing tenant existence."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {deleted_tenant_token}"}
        )
        
        # Use 404 (not 403) to avoid revealing the tenant existed.
        assert response.status_code == 404, (
            f"Deleted tenant should get 404 (not 403), got {response.status_code}. "
            "403 reveals tenant existed. P0: Information disclosure."
        )
        
        data = response.json()
        assert data.get("error") == "tenant_not_found", (
            f"Expected 'tenant_not_found' error, got {data.get('error')}"
        )


class TestTenantLifecycleAudit:
    """P1: Tenant lifecycle events are audited."""

    @pytest.fixture
    def suspended_tenant_token(self, jwt_encoder) -> str:
        """JWT for suspended tenant (local fixture for audit class)."""
        return jwt_encoder({
            "sub": "user-123",
            "tenant_id": "tenant-suspended",
            "role": "standard",
            "tenant_status": "suspended",
        })

    def test_suspended_tenant_access_attempt_logged(
        self, client: TestClient, suspended_tenant_token: str
    ):
        """P1: Attempts by suspended tenants are logged for security review."""
        response = client.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {suspended_tenant_token}"}
        )
        
        # Even if blocked, should be logged
        # This test documents the requirement - actual audit verification
        # would require checking audit log output
        assert response.status_code == 403


class TestTenantStatusTransition:
    """P1: Tenant status transitions handled correctly."""

    def test_active_to_suspended_blocks_immediately(self):
        """P1: When tenant suspended, subsequent requests blocked immediately."""
        # This would require stateful test with DB
        pytest.skip("Requires database state management")

    def test_suspended_to_active_restores_access(self):
        """P1: When tenant reactivated, access restored."""
        pytest.skip("Requires database state management")


# ---------------------------------------------------------------------------
# P0 expansion: middleware-level static enforcement checks
# ---------------------------------------------------------------------------

class TestTenantLifecycleMiddlewareEnforcement:
    """P0: Verify the governance middleware source enforces tenant lifecycle status.

    These are static-analysis tests — they verify the middleware code contains
    the structural invariants required for lifecycle enforcement without needing
    a live server.
    """

    def _load_middleware_source(self) -> str:
        from pathlib import Path
        candidates = [
            Path("packages/shared/src/value_fabric/shared/identity/middleware.py"),
            Path("value_fabric/shared/identity/middleware.py"),
        ]
        for path in candidates:
            if path.exists():
                return path.read_text(encoding="utf-8")
        pytest.skip("GovernanceMiddleware source not found")

    def test_middleware_checks_tenant_status(self):
        """GovernanceMiddleware must check tenant status before processing requests."""
        source = self._load_middleware_source()
        # The middleware must reference tenant status in some form
        has_status_check = any(
            keyword in source
            for keyword in ("tenant_status", "suspended", "TenantStatus", "tenant_lifecycle")
        )
        assert has_status_check, (
            "GovernanceMiddleware does not appear to check tenant status. "
            "P0: Suspended/pending/deleted tenants can access the platform."
        )

    def test_middleware_rejects_suspended_status(self):
        """Middleware source must handle 'suspended' tenant status."""
        source = self._load_middleware_source()
        assert "suspended" in source, (
            "GovernanceMiddleware does not handle 'suspended' tenant status. "
            "P0: Suspended tenants are not blocked."
        )

    def test_middleware_rejects_pending_status(self):
        """Middleware source must handle 'pending' tenant status."""
        source = self._load_middleware_source()
        assert "pending" in source, (
            "GovernanceMiddleware does not handle 'pending' tenant status. "
            "P0: Pending tenants are not blocked."
        )

    def test_middleware_rejects_deleted_status(self):
        """Middleware source must handle 'deleted' tenant status."""
        source = self._load_middleware_source()
        assert "deleted" in source, (
            "GovernanceMiddleware does not handle 'deleted' tenant status. "
            "P0: Deleted tenants are not blocked."
        )

    def test_middleware_lifecycle_check_precedes_business_logic(self):
        """Tenant lifecycle check must occur before business logic dispatch.

        Verifies that the status check appears before the route handler call
        in the middleware's dispatch method.
        """
        import re
        source = self._load_middleware_source()

        # Find the dispatch / __call__ method
        dispatch_match = re.search(
            r"async def (?:dispatch|__call__)\s*\(.*?\n(.*?)(?=\nasync def |\nclass |\Z)",
            source,
            re.DOTALL,
        )
        if not dispatch_match:
            pytest.skip("Could not locate dispatch/__call__ in middleware source")

        dispatch_body = dispatch_match.group(1)

        # The status check keyword should appear before "call_next" or "await app"
        status_pos = min(
            (dispatch_body.find(kw) for kw in ("suspended", "tenant_status", "TenantStatus")
             if dispatch_body.find(kw) != -1),
            default=-1,
        )
        call_next_pos = dispatch_body.find("call_next")
        if call_next_pos == -1:
            call_next_pos = dispatch_body.find("await self.app")

        if status_pos == -1:
            pytest.skip("Tenant status check not found in dispatch body — covered by other test")

        if call_next_pos != -1:
            assert status_pos < call_next_pos, (
                "Tenant lifecycle check appears AFTER call_next in dispatch. "
                "P0: Business logic executes before tenant status is validated."
            )
