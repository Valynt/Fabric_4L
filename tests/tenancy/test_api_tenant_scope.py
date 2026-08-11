from __future__ import annotations

import pytest
from tests.tenancy._invariant_manifest import TenantInvariant, assert_tenancy_invariants

pytestmark = [pytest.mark.tenancy, pytest.mark.tenant_boundary, pytest.mark.production_readiness]


def test_api_tenant_scope_coverage_exists() -> None:
    assert_tenancy_invariants(
        (
            "tests/security/test_tenant_isolation.py",
            "tests/security/test_cross_layer_tenant_isolation_matrix.py",
            "services/api/app/tests/test_tenant_isolation.py",
            "services/layer1-ingestion/tests/test_api_tenant_propagation.py",
            "services/layer2-extraction/tests/test_api_tenant_propagation.py",
            "services/layer4-agents/tests/test_api_tenant_propagation.py",
            "services/layer5-ground-truth/tests/test_api_tenant_propagation.py",
            "services/layer6-benchmarks/tests/test_api_tenant_propagation.py",
        ),
        label="API tenant scope coverage",
        invariants=(
            TenantInvariant(
                key="positive_authorized_case",
                description="own-tenant API access has a positive authorization path",
                evidence=(("assert beta_read.status_code == 200", "expected 10 tenant-a entities"),),
            ),
            TenantInvariant(
                key="cross_tenant_read_denied",
                description="cross-tenant API reads are denied or hidden",
                evidence=(("test_user_cannot_access_other_tenant_data", "test_tenant_a_cannot_read_tenant_b_row_even_with_tenant_b_in_payload", "READ-001"),),
            ),
            TenantInvariant(
                key="cross_tenant_write_denied",
                description="cross-tenant API writes are denied or stamped with the authenticated tenant",
                evidence=(("test_tenant_a_cannot_insert_row_for_tenant_b_from_payload", "test_tenant_a_cannot_update_tenant_b_row_even_with_tenant_b_in_payload", "WRITE-001"),),
            ),
            TenantInvariant(
                key="trusted_context_over_request_payload",
                description="body or header tenant spoofing cannot override authenticated context",
                evidence=(("attempted spoof", "forged body tenant_id", "jwt tenant claim"),),
            ),
        ),
    )
