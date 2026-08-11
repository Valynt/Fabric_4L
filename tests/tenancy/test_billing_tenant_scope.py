from __future__ import annotations

import pytest
from tests.tenancy._invariant_manifest import TenantInvariant, assert_tenancy_invariants

pytestmark = [pytest.mark.tenancy, pytest.mark.tenant_boundary, pytest.mark.production_readiness]


def test_billing_tenant_scope_coverage_exists() -> None:
    assert_tenancy_invariants(
        (
            "tests/security/test_billing_tenant_boundary.py",
            "tests/recovery/test_restore_billing_state.py",
            "services/layer4-agents/tests/test_billing_tenant_scoped_customer_keys.py",
            "services/layer4-agents/tests/test_billing_security_exceptions.py",
        ),
        label="billing tenant scope coverage",
        invariants=(
            TenantInvariant(
                key="billing_reads_are_tenant_filtered",
                description="billing usage, invoices, and state reads are filtered by tenant",
                evidence=(("tenant_a_cannot_read_tenant_b_usage", "tenant_id"),),
            ),
            TenantInvariant(
                key="cross_tenant_invoice_access_denied",
                description="cross-tenant invoice or usage access is denied",
                evidence=(("cross_tenant_invoice_access_blocked", "tenant boundary"),),
            ),
            TenantInvariant(
                key="read_only_role_cannot_mutate",
                description="read-only billing roles cannot mutate billing resources",
                evidence=(("read_only_role_cannot_mutate", "billing:read"),),
            ),
            TenantInvariant(
                key="write_role_positive_case",
                description="valid billing write role has a positive authorization path",
                evidence=(("write_role_can_mutate", "billing:write"),),
            ),
        ),
    )
