"""
Tests for audit write monitor and admin guards.

Tests for admin-only write path guards for audit tables.
"""

import uuid

import pytest

from layer5_ground_truth.services.audit_write_monitor import (
    ADMIN_ROLES,
    AgentPermissionError,
    is_admin_user,
    record_audit_write_failure,
    require_admin_for_audit_write,
)


class MockTokenClaims:
    def __init__(self, user_id: str, tenant_id: uuid.UUID, roles: list[str]):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.roles = roles


class TestAuditWriteMonitor:
    def test_admin_roles_defined(self):
        """ADMIN_ROLES should include expected roles."""
        assert "admin" in ADMIN_ROLES
        assert "system" in ADMIN_ROLES
        assert "auditor" in ADMIN_ROLES

    def test_is_admin_user_with_admin_role(self):
        """Should return True for user with admin role."""
        claims = MockTokenClaims(
            user_id="admin@example.com",
            tenant_id=uuid.uuid4(),
            roles=["admin"],
        )
        assert is_admin_user(claims) is True

    def test_is_admin_user_with_system_role(self):
        """Should return True for user with system role."""
        claims = MockTokenClaims(
            user_id="system",
            tenant_id=uuid.uuid4(),
            roles=["system"],
        )
        assert is_admin_user(claims) is True

    def test_is_admin_user_with_auditor_role(self):
        """Should return True for user with auditor role."""
        claims = MockTokenClaims(
            user_id="auditor@example.com",
            tenant_id=uuid.uuid4(),
            roles=["auditor"],
        )
        assert is_admin_user(claims) is True

    def test_is_admin_user_with_no_roles(self):
        """Should return False for user with no roles."""
        claims = MockTokenClaims(
            user_id="user@example.com",
            tenant_id=uuid.uuid4(),
            roles=[],
        )
        assert is_admin_user(claims) is False

    def test_is_admin_user_with_non_admin_role(self):
        """Should return False for user with non-admin role."""
        claims = MockTokenClaims(
            user_id="user@example.com",
            tenant_id=uuid.uuid4(),
            roles=["user"],
        )
        assert is_admin_user(claims) is False

    def test_is_admin_user_with_none(self):
        """Should return False for None caller."""
        assert is_admin_user(None) is False

    def test_require_admin_for_audit_write_with_admin(self):
        """Should not raise for admin user."""
        claims = MockTokenClaims(
            user_id="admin@example.com",
            tenant_id=uuid.uuid4(),
            roles=["admin"],
        )
        # Should not raise
        require_admin_for_audit_write(claims, "test operation")

    def test_require_admin_for_audit_write_without_admin(self):
        """Should raise PermissionError for non-admin user."""
        claims = MockTokenClaims(
            user_id="user@example.com",
            tenant_id=uuid.uuid4(),
            roles=["user"],
        )
        with pytest.raises(PermissionError, match="Admin privileges required"):
            require_admin_for_audit_write(claims, "test operation")

    def test_require_admin_for_audit_write_with_none(self):
        """Should raise PermissionError for None caller."""
        with pytest.raises(PermissionError, match="Admin privileges required"):
            require_admin_for_audit_write(None, "test operation")

    def test_record_audit_write_failure(self):
        """Should increment failure counter."""
        from layer5_ground_truth.services.audit_write_monitor import get_audit_write_stats

        initial_stats = get_audit_write_stats()
        initial_failures = initial_stats.get("failures_total", 0)

        record_audit_write_failure()

        new_stats = get_audit_write_stats()
        assert new_stats.get("failures_total", 0) == initial_failures + 1

    def test_get_audit_write_stats(self):
        """Should return audit write statistics."""
        stats = get_audit_write_stats()
        assert "failures_total" in stats
        assert "admin_bypasses" in stats
        assert isinstance(stats["failures_total"], int)
        assert isinstance(stats["admin_bypasses"], int)
