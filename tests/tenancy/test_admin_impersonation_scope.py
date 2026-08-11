from __future__ import annotations

import pytest
from tests.tenancy._invariant_manifest import TenantInvariant, assert_tenancy_invariants

pytestmark = [pytest.mark.tenancy, pytest.mark.tenant_boundary, pytest.mark.production_readiness]


def test_admin_impersonation_scope_coverage_exists() -> None:
    assert_tenancy_invariants(
        (
            "services/api/app/tests/test_impersonation_security.py",
            "tests/security/test_privileged_audit.py",
            "tests/integration/test_admin_audit_journey.py",
        ),
        label="admin impersonation tenant scope coverage",
        invariants=(
            TenantInvariant(
                key="privileged_permission_required",
                description="admin or support impersonation requires privileged permission",
                evidence=(("require", "permission", "super_admin", "support"),),
            ),
            TenantInvariant(
                key="impersonation_tenant_scoped",
                description="impersonation remains scoped to the target tenant and cannot widen access",
                evidence=(("impersonat",), ("tenant",)),
            ),
            TenantInvariant(
                key="impersonation_audited",
                description="admin/support access is audited with actor, target, reason, and denial coverage",
                evidence=(("audit",), ("reason", "denied", "target", "actor")),
            ),
        ),
    )
