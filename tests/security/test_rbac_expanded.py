"""RBAC Expanded Security Tests — P1 Gap Remediation

Extends RBAC coverage to include the full CRUD permission matrix and the
require_any_permission OR logic. The existing test_rbac.py covers role
hierarchy and JWT tampering; this file covers the permission-level boundaries
that were absent.

Gap matrix refs:
  P1 gap 4 — Permission Check: missing permission bypass (expand to all CRUD)
  P1 gap 5 — Any Permission Check: OR permission logic bypass

Author: Platform Security Team
"""

from __future__ import annotations

import pytest

from value_fabric.shared.identity.context import (
    AUTH_SOURCE_JWT,
    RequestContext,
)
from value_fabric.shared.identity.permissions import Permission, Role

pytestmark = [
    pytest.mark.security,
    pytest.mark.rbac,
]

VALID_TENANT = "tenant-rbac-test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(*permissions: Permission | str, roles: list[str] | None = None) -> RequestContext:
    return RequestContext(
        tenant_id=VALID_TENANT,
        auth_source=AUTH_SOURCE_JWT,
        permissions=list(permissions),
        roles=roles or [],
    )


# ---------------------------------------------------------------------------
# Full CRUD Permission Matrix
# ---------------------------------------------------------------------------


class TestCRUDPermissionMatrix:
    """P1 gap 4: Every CRUD permission must be independently enforceable."""

    # ── Read permissions ───────────────────────────────────────────────────

    def test_read_ingestion_granted(self):
        """POSITIVE: Context with READ_INGESTION has the permission."""
        ctx = _ctx(Permission.READ_INGESTION)
        assert ctx.has_permission(Permission.READ_INGESTION)

    def test_read_ingestion_denied_without_permission(self):
        """NEGATIVE: Context without READ_INGESTION does not have it."""
        ctx = _ctx(Permission.WRITE_INGESTION)
        assert not ctx.has_permission(Permission.READ_INGESTION), (
            "WRITE_INGESTION must not grant READ_INGESTION."
        )

    def test_write_ingestion_granted(self):
        """POSITIVE: Context with WRITE_INGESTION has the permission."""
        ctx = _ctx(Permission.WRITE_INGESTION)
        assert ctx.has_permission(Permission.WRITE_INGESTION)

    def test_write_ingestion_denied_without_permission(self):
        """NEGATIVE: Context without WRITE_INGESTION does not have it."""
        ctx = _ctx(Permission.READ_INGESTION)
        assert not ctx.has_permission(Permission.WRITE_INGESTION), (
            "READ_INGESTION must not grant WRITE_INGESTION."
        )

    def test_write_extraction_granted(self):
        """POSITIVE: Context with WRITE_EXTRACTION has the permission."""
        ctx = _ctx(Permission.WRITE_EXTRACTION)
        assert ctx.has_permission(Permission.WRITE_EXTRACTION)

    def test_write_extraction_denied_without_permission(self):
        """NEGATIVE: Context without WRITE_EXTRACTION does not have it."""
        ctx = _ctx(Permission.READ_INGESTION)
        assert not ctx.has_permission(Permission.WRITE_EXTRACTION)

    def test_read_agents_granted(self):
        """POSITIVE: Context with READ_AGENTS has the permission."""
        ctx = _ctx(Permission.READ_AGENTS)
        assert ctx.has_permission(Permission.READ_AGENTS)

    def test_write_agents_denied_without_permission(self):
        """NEGATIVE: READ_AGENTS does not grant WRITE_AGENTS."""
        ctx = _ctx(Permission.READ_AGENTS)
        assert not ctx.has_permission(Permission.WRITE_AGENTS), (
            "READ_AGENTS must not grant WRITE_AGENTS."
        )

    def test_admin_api_keys_granted(self):
        """POSITIVE: Context with ADMIN_API_KEYS has the permission."""
        ctx = _ctx(Permission.ADMIN_API_KEYS)
        assert ctx.has_permission(Permission.ADMIN_API_KEYS)

    def test_admin_api_keys_denied_without_permission(self):
        """NEGATIVE: Write permissions do not grant ADMIN_API_KEYS."""
        ctx = _ctx(Permission.WRITE_INGESTION, Permission.WRITE_AGENTS)
        assert not ctx.has_permission(Permission.ADMIN_API_KEYS), (
            "Write permissions must not grant ADMIN_API_KEYS."
        )

    def test_admin_tenants_denied_without_permission(self):
        """NEGATIVE: Tenant admin role alone does not grant ADMIN_TENANTS permission."""
        ctx = _ctx(roles=[Role.TENANT_ADMIN.value])
        assert not ctx.has_permission(Permission.ADMIN_TENANTS), (
            "TENANT_ADMIN role alone must not grant ADMIN_TENANTS permission without explicit grant."
        )

    def test_resolved_all_permissions_grants_every_permission(self):
        """POSITIVE: Resolved all-permission set grants every permission check."""
        ctx = _ctx(*list(Permission))
        for perm in Permission:
            assert ctx.has_permission(perm), (
                f"Resolved all-permission set must grant {perm.value}."
            )

    def test_raw_all_permission_string_does_not_grant_wildcard(self):
        """NEGATIVE: Raw 'all' permission strings are not wildcard grants."""
        ctx = _ctx("all")
        for perm in Permission:
            assert not ctx.has_permission(perm), (
                f"Raw 'all' permission string must not grant {perm.value}."
            )

    def test_empty_permissions_denies_all(self):
        """NEGATIVE: Context with no permissions denies every permission check."""
        ctx = _ctx()
        for perm in [Permission.READ_INGESTION, Permission.WRITE_AGENTS, Permission.ADMIN_SYSTEM]:
            assert not ctx.has_permission(perm), (
                f"Empty permissions must deny {perm.value}."
            )

    def test_has_all_permissions_requires_every_permission(self):
        """NEGATIVE: has_all_permissions fails if any permission is missing."""
        ctx = _ctx(Permission.READ_INGESTION, Permission.READ_AGENTS)
        assert ctx.has_all_permissions(Permission.READ_INGESTION, Permission.READ_AGENTS)
        assert not ctx.has_all_permissions(
            Permission.READ_INGESTION, Permission.READ_AGENTS, Permission.WRITE_INGESTION
        ), "has_all_permissions must fail if any permission is absent."

    def test_permission_string_and_enum_equivalent(self):
        """POSITIVE: String and enum forms of the same permission are equivalent."""
        ctx = _ctx(Permission.READ_SEARCH)
        assert ctx.has_permission("read:search"), (
            "String form 'read:search' must match Permission.READ_SEARCH."
        )
        assert ctx.has_permission(Permission.READ_SEARCH), (
            "Enum form must also match."
        )


# ---------------------------------------------------------------------------
# require_any_permission OR Logic
# ---------------------------------------------------------------------------


class TestRequireAnyPermissionOrLogic:
    """P1 gap 5: has_any_permission must return True when ANY one permission matches."""

    def test_any_permission_true_when_first_matches(self):
        """POSITIVE: has_any_permission returns True when the first permission matches."""
        ctx = _ctx(Permission.READ_INGESTION)
        assert ctx.has_any_permission(Permission.READ_INGESTION, Permission.WRITE_INGESTION), (
            "has_any_permission must return True when the first permission is present."
        )

    def test_any_permission_true_when_second_matches(self):
        """POSITIVE: has_any_permission returns True when only the second permission matches."""
        ctx = _ctx(Permission.WRITE_INGESTION)
        assert ctx.has_any_permission(Permission.READ_INGESTION, Permission.WRITE_INGESTION), (
            "has_any_permission must return True when the second permission is present."
        )

    def test_any_permission_true_when_last_matches(self):
        """POSITIVE: has_any_permission returns True when only the last of many matches."""
        ctx = _ctx(Permission.ADMIN_SYSTEM)
        assert ctx.has_any_permission(
            Permission.READ_INGESTION,
            Permission.WRITE_INGESTION,
            Permission.READ_AGENTS,
            Permission.ADMIN_SYSTEM,
        ), "has_any_permission must return True when any permission in the list matches."

    def test_any_permission_false_when_none_match(self):
        """NEGATIVE: has_any_permission returns False when no permission matches."""
        ctx = _ctx(Permission.READ_HEALTH)
        assert not ctx.has_any_permission(
            Permission.WRITE_INGESTION, Permission.ADMIN_API_KEYS
        ), "has_any_permission must return False when no listed permission is present."

    def test_any_permission_false_for_empty_context(self):
        """NEGATIVE: has_any_permission returns False for a context with no permissions."""
        ctx = _ctx()
        assert not ctx.has_any_permission(Permission.READ_INGESTION, Permission.WRITE_AGENTS), (
            "has_any_permission must return False for a context with no permissions."
        )

    def test_any_permission_with_single_candidate(self):
        """POSITIVE: has_any_permission with a single candidate behaves like has_permission."""
        ctx = _ctx(Permission.READ_METRICS)
        assert ctx.has_any_permission(Permission.READ_METRICS)
        assert not ctx.has_any_permission(Permission.WRITE_AGENTS)

    def test_any_permission_not_confused_by_prefix_similarity(self):
        """ADVERSARIAL: 'read:ingestion' must not satisfy 'read:ingestion_admin'."""
        ctx = _ctx(Permission.READ_INGESTION)
        # Simulate a hypothetical permission that shares a prefix
        assert not ctx.has_any_permission("read:ingestion_admin"), (
            "Prefix-similar permission strings must not be confused."
        )

    def test_any_permission_with_resolved_all_permission_grant(self):
        """POSITIVE: Resolved all-permission set satisfies has_any_permission."""
        ctx = _ctx(*list(Permission))
        assert ctx.has_any_permission(Permission.ADMIN_SYSTEM, Permission.WRITE_EXTRACTION), (
            "Resolved all-permission set must satisfy has_any_permission for any combination."
        )

    def test_any_permission_string_and_enum_interchangeable(self):
        """POSITIVE: String and enum forms are interchangeable in has_any_permission."""
        ctx = _ctx(Permission.READ_GRAPHRAG)
        assert ctx.has_any_permission("read:graphrag", Permission.WRITE_AGENTS), (
            "String form must be accepted in has_any_permission."
        )
