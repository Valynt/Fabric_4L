from __future__ import annotations

import pytest
from tests.tenancy._invariant_manifest import TenantInvariant, assert_tenancy_invariants

pytestmark = [pytest.mark.tenancy, pytest.mark.tenant_boundary, pytest.mark.production_readiness]


def test_worker_tenant_scope_coverage_exists() -> None:
    assert_tenancy_invariants(
        (
            "tests/integration/test_celery_queue_topology.py",
            "services/layer1-ingestion/tests/security/test_celery_tenant_isolation_postgres.py",
            "services/layer4-agents/tests/test_workflow_tenant_isolation.py",
            "services/layer4-agents/tests/test_workflow_start_tenant_invariant.py",
        ),
        label="worker tenant scope coverage",
        invariants=(
            TenantInvariant(
                key="job_signature_carries_tenant",
                description="background job and workflow entrypoints carry tenant_id",
                evidence=(("signature includes tenant_id", "must accept tenant_id", "requires tenant_id"),),
            ),
            TenantInvariant(
                key="missing_tenant_fails_closed",
                description="worker paths touching tenant-owned data fail closed without tenant context",
                evidence=(("without tenant_id fails", "rejects missing tenant", "tenant_id is required"),),
            ),
            TenantInvariant(
                key="own_tenant_positive_case",
                description="worker paths can process the owning tenant data",
                evidence=(("can query tenant's own data", "accepts valid tenant", "uses tenant context"),),
            ),
            TenantInvariant(
                key="wrong_tenant_denied",
                description="background jobs cannot process or query another tenant's records",
                evidence=(("cannot query other tenant", "other_job.id not in job_ids", "cross-tenant access is blocked"),),
            ),
        ),
    )
