"""Permission bypass security tests — P0 gap remediation.

Validates that permission checks cannot be bypassed via:
- Missing permission claims in JWT
- Injected all-permissions wildcard claims
- OR-logic abuse in require_any_permission
- Privilege escalation through role claim manipulation
- Permission scope checks on the canonical dependency functions

Production Invariant: Permission checks must fail closed — missing or
unrecognised permission claims must deny access, never grant it.
"""

from __future__ import annotations

import pytest
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    Role,
    get_role_permissions,
    role_has_permission,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(
    *,
    tenant_id: str = "tenant-a",
    roles: list[str] | None = None,
    permissions: frozenset[Permission] | None = None,
) -> RequestContext:
    """Build a minimal RequestContext for permission tests."""
    return RequestContext(
        tenant_id=tenant_id,
        user_id="user-test",
        roles=roles or [],
        permissions=permissions if permissions is not None else frozenset(),
        source="jwt_claim",
    )


# ---------------------------------------------------------------------------
# Role → permission mapping invariants
# ---------------------------------------------------------------------------

class TestRolePermissionMapping:
    """Verify the canonical ROLE_PERMISSIONS mapping is correct and complete."""

    def test_read_only_cannot_write(self):
        """READ_ONLY role must not have any write or admin permissions."""
        perms = get_role_permissions(Role.READ_ONLY)
        write_or_admin = {p for p in perms if p.value.startswith(("write:", "admin:"))}
        assert not write_or_admin, (
            f"READ_ONLY role has write/admin permissions: {write_or_admin}. "
            "P0: Privilege escalation via role assignment."
        )

    def test_analyst_cannot_admin(self):
        """ANALYST role must not have admin permissions."""
        perms = get_role_permissions(Role.ANALYST)
        admin_perms = {p for p in perms if p.value.startswith("admin:")}
        assert not admin_perms, (
            f"ANALYST role has admin permissions: {admin_perms}. "
            "P0: Analyst can perform admin operations."
        )

    def test_content_admin_cannot_admin_users_or_tenants(self):
        """CONTENT_ADMIN must not have user/tenant admin permissions."""
        perms = get_role_permissions(Role.CONTENT_ADMIN)
        forbidden = {Permission.ADMIN_USERS, Permission.ADMIN_TENANTS, Permission.ADMIN_SYSTEM}
        overlap = perms & forbidden
        assert not overlap, (
            f"CONTENT_ADMIN has user/tenant admin permissions: {overlap}. "
            "P0: Content admin can manage users or tenants."
        )

    def test_tenant_admin_cannot_admin_system(self):
        """TENANT_ADMIN must not have ADMIN_SYSTEM (platform-wide)."""
        perms = get_role_permissions(Role.TENANT_ADMIN)
        assert Permission.ADMIN_SYSTEM not in perms, (
            "TENANT_ADMIN has ADMIN_SYSTEM permission. "
            "P0: Tenant admin can perform platform-wide system operations."
        )

    def test_super_admin_has_all_permissions(self):
        """SUPER_ADMIN must have every defined permission."""
        super_perms = get_role_permissions(Role.SUPER_ADMIN)
        all_perms = frozenset(Permission)
        missing = all_perms - super_perms
        assert not missing, (
            f"SUPER_ADMIN is missing permissions: {missing}. "
            "SUPER_ADMIN must have all permissions."
        )

    def test_role_hierarchy_is_monotone(self):
        """Higher roles must have a superset of lower role permissions."""
        hierarchy = [
            Role.READ_ONLY,
            Role.ANALYST,
            Role.CONTENT_ADMIN,
            Role.TENANT_ADMIN,
            Role.SUPER_ADMIN,
        ]
        for i in range(len(hierarchy) - 1):
            lower = get_role_permissions(hierarchy[i])
            higher = get_role_permissions(hierarchy[i + 1])
            assert lower.issubset(higher), (
                f"{hierarchy[i + 1].value} is missing permissions held by "
                f"{hierarchy[i].value}: {lower - higher}. "
                "Role hierarchy must be monotone (higher ⊇ lower)."
            )

    def test_no_permission_enum_value_is_wildcard(self):
        """No permission value should be a wildcard ('*' or 'all')."""
        wildcards = [p for p in Permission if p.value in ("*", "all", "all:*", "*:*")]
        assert not wildcards, (
            f"Wildcard permission values found: {wildcards}. "
            "Wildcards bypass fine-grained access control."
        )


# ---------------------------------------------------------------------------
# RequestContext.has_permission — fail-closed behaviour
# ---------------------------------------------------------------------------

class TestRequestContextPermissionChecks:
    """Verify RequestContext.has_permission fails closed on edge cases."""

    def test_empty_permissions_denies_all(self):
        """Context with no permissions denies every permission check."""
        ctx = _ctx(permissions=frozenset())
        for perm in Permission:
            assert not ctx.has_permission(perm), (
                f"Empty permissions context granted {perm}. "
                "P0: Permission check fails open."
            )

    def test_wildcard_string_not_granted(self):
        """A '*' string in permissions must not grant all permissions."""
        ctx = _ctx(permissions=frozenset())
        # Simulate an attacker injecting a wildcard string
        assert not ctx.has_permission("*"), (
            "Wildcard '*' string granted permission. P0: Bypass via wildcard."
        )
        assert not ctx.has_permission("all"), (
            "'all' string granted permission. P0: Bypass via wildcard."
        )

    def test_unrecognised_permission_string_denied(self):
        """Unknown permission strings must be denied, not granted."""
        ctx = _ctx(permissions=frozenset())
        assert not ctx.has_permission("nonexistent:permission"), (
            "Unknown permission string was granted. P0: Fail-open on unknown permissions."
        )

    def test_has_any_permission_requires_at_least_one_match(self):
        """has_any_permission returns False when none of the listed perms are held."""
        ctx = _ctx(permissions=frozenset({Permission.READ_HEALTH}))
        assert not ctx.has_any_permission(
            Permission.ADMIN_SYSTEM, Permission.ADMIN_USERS
        ), (
            "has_any_permission returned True with no matching permissions. "
            "P0: OR-logic bypass."
        )

    def test_has_any_permission_returns_true_on_single_match(self):
        """has_any_permission returns True when at least one permission matches."""
        ctx = _ctx(permissions=frozenset({Permission.READ_HEALTH}))
        assert ctx.has_any_permission(
            Permission.READ_HEALTH, Permission.ADMIN_SYSTEM
        ), "has_any_permission should return True when one permission matches."

    def test_has_all_permissions_requires_every_permission(self):
        """has_all_permissions returns False when any required permission is missing."""
        ctx = _ctx(permissions=frozenset({Permission.READ_HEALTH}))
        assert not ctx.has_all_permissions(
            Permission.READ_HEALTH, Permission.WRITE_INGESTION
        ), (
            "has_all_permissions returned True with a missing permission. "
            "P0: AND-logic bypass."
        )

    def test_has_all_permissions_returns_true_when_all_held(self):
        """has_all_permissions returns True only when every permission is held."""
        ctx = _ctx(
            permissions=frozenset({Permission.READ_HEALTH, Permission.WRITE_INGESTION})
        )
        assert ctx.has_all_permissions(
            Permission.READ_HEALTH, Permission.WRITE_INGESTION
        ), "has_all_permissions should return True when all permissions are held."

    def test_permission_check_is_exact_match_not_prefix(self):
        """'read:health' must not grant 'read:healthier' or 'read:health:extra'."""
        ctx = _ctx(permissions=frozenset({Permission.READ_HEALTH}))
        assert not ctx.has_permission("read:health:extra"), (
            "Prefix match granted a more-specific permission. "
            "P0: Permission scope creep."
        )
        assert not ctx.has_permission("read:healthier"), (
            "Substring match granted a different permission. "
            "P0: Permission scope creep."
        )


# ---------------------------------------------------------------------------
# require_permission dependency — async behaviour
# ---------------------------------------------------------------------------

class TestRequirePermissionDependency:
    """Verify the FastAPI dependency functions raise correctly."""

    @pytest.mark.asyncio
    async def test_require_permission_raises_403_when_missing(self):
        """require_permission raises HTTP 403 when the permission is absent."""
        from fastapi import HTTPException
        from value_fabric.shared.identity.dependencies import require_permission

        ctx = _ctx(permissions=frozenset({Permission.READ_HEALTH}))
        dep = require_permission(Permission.ADMIN_SYSTEM)

        with pytest.raises(HTTPException) as exc_info:
            await dep(context=ctx)
        assert exc_info.value.status_code == 403, (
            f"Expected 403, got {exc_info.value.status_code}. "
            "P0: Missing permission did not raise 403."
        )

    @pytest.mark.asyncio
    async def test_require_permission_passes_when_held(self):
        """require_permission returns context when the permission is present."""
        from value_fabric.shared.identity.dependencies import require_permission

        ctx = _ctx(permissions=frozenset({Permission.ADMIN_SYSTEM}))
        dep = require_permission(Permission.ADMIN_SYSTEM)
        result = await dep(context=ctx)
        assert result is ctx

    @pytest.mark.asyncio
    async def test_require_any_permission_raises_403_when_none_match(self):
        """require_any_permission raises 403 when none of the permissions are held."""
        from fastapi import HTTPException
        from value_fabric.shared.identity.dependencies import require_any_permission

        ctx = _ctx(permissions=frozenset({Permission.READ_HEALTH}))
        dep = require_any_permission(Permission.ADMIN_SYSTEM, Permission.ADMIN_USERS)

        with pytest.raises(HTTPException) as exc_info:
            await dep(context=ctx)
        assert exc_info.value.status_code == 403, (
            f"Expected 403, got {exc_info.value.status_code}. "
            "P0: OR-logic bypass — no matching permission should deny."
        )

    @pytest.mark.asyncio
    async def test_require_all_permissions_raises_403_when_any_missing(self):
        """require_all_permissions raises 403 when any required permission is absent."""
        from fastapi import HTTPException
        from value_fabric.shared.identity.dependencies import require_all_permissions

        ctx = _ctx(permissions=frozenset({Permission.READ_HEALTH}))
        dep = require_all_permissions(Permission.READ_HEALTH, Permission.WRITE_INGESTION)

        with pytest.raises(HTTPException) as exc_info:
            await dep(context=ctx)
        assert exc_info.value.status_code == 403, (
            f"Expected 403, got {exc_info.value.status_code}. "
            "P0: AND-logic bypass — partial permission set should deny."
        )

    @pytest.mark.asyncio
    async def test_require_permission_raises_401_for_unauthenticated(self):
        """require_permission raises HTTP 401 when context is None (unauthenticated)."""
        from fastapi import HTTPException
        from value_fabric.shared.identity.dependencies import require_permission

        dep = require_permission(Permission.READ_HEALTH)

        with pytest.raises(HTTPException) as exc_info:
            await dep(context=None)
        assert exc_info.value.status_code == 401, (
            f"Expected 401 for unauthenticated request, got {exc_info.value.status_code}. "
            "P0: Unauthenticated request must not reach permission check."
        )


# ---------------------------------------------------------------------------
# role_has_permission helper — boundary checks
# ---------------------------------------------------------------------------

class TestRoleHasPermissionHelper:
    """Verify the role_has_permission helper is consistent with ROLE_PERMISSIONS."""

    def test_read_only_denied_write_ingestion(self):
        assert not role_has_permission(Role.READ_ONLY, Permission.WRITE_INGESTION), (
            "READ_ONLY should not have WRITE_INGESTION."
        )

    def test_analyst_denied_admin_users(self):
        assert not role_has_permission(Role.ANALYST, Permission.ADMIN_USERS), (
            "ANALYST should not have ADMIN_USERS."
        )

    def test_super_admin_has_admin_system(self):
        assert role_has_permission(Role.SUPER_ADMIN, Permission.ADMIN_SYSTEM), (
            "SUPER_ADMIN must have ADMIN_SYSTEM."
        )

    def test_tenant_admin_has_admin_api_keys(self):
        assert role_has_permission(Role.TENANT_ADMIN, Permission.ADMIN_API_KEYS), (
            "TENANT_ADMIN must be able to manage API keys."
        )

    def test_system_role_has_all_permissions(self):
        """SYSTEM role (service-to-service) must have every permission."""
        for perm in Permission:
            assert role_has_permission(Role.SYSTEM, perm), (
                f"SYSTEM role missing {perm}. Service accounts need full access."
            )
