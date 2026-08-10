from __future__ import annotations

import pytest
from tests.tenancy._invariant_manifest import TenantInvariant, assert_tenancy_invariants

pytestmark = [pytest.mark.tenancy, pytest.mark.tenant_boundary, pytest.mark.production_readiness]


def test_database_tenant_scope_coverage_exists() -> None:
    assert_tenancy_invariants(
        (
            "tests/production_readiness/test_postgres_production_invariants.py",
            "tests/security/test_rls_enforcement.py",
            "tests/security/test_tenant_repository_filter_presence.py",
            "services/api/app/tests/test_database_tenant_boundary.py",
            "services/layer4-agents/tests/test_database_session_tenant_enforcement.py",
            "services/layer5-ground-truth/tests/test_database_optional_tenant_security.py",
        ),
        label="database tenant scope coverage",
        invariants=(
            TenantInvariant(
                key="rls_or_repository_filter",
                description="database access is protected by RLS or explicit repository tenant filters",
                evidence=(("rls", "repository filter", "tenant_id"),),
            ),
            TenantInvariant(
                key="missing_tenant_fails_closed",
                description="unscoped tenant-owned database access fails closed",
                evidence=(("fails_closed", "fail closed", "denies_unscoped_reads_and_writes"),),
            ),
            TenantInvariant(
                key="cross_tenant_read_denied",
                description="tenant-scoped database reads do not expose another tenant",
                evidence=(("cross-tenant", "other tenant", "tenant b"), ("read", "select", "query")),
            ),
            TenantInvariant(
                key="cross_tenant_write_denied",
                description="tenant-scoped database writes do not mutate another tenant",
                evidence=(("write", "update", "insert", "mutate"), ("tenant",)),
            ),
        ),
    )
