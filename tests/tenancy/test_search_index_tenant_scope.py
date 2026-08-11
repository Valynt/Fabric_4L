from __future__ import annotations

import pytest
from tests.tenancy._invariant_manifest import TenantInvariant, assert_tenancy_invariants

pytestmark = [pytest.mark.tenancy, pytest.mark.tenant_boundary, pytest.mark.production_readiness]


def test_search_index_tenant_scope_coverage_exists() -> None:
    assert_tenancy_invariants(
        (
            "tests/layer3/test_endpoint_tenant_isolation.py",
            "tests/layer3/test_graph_repository_tenant_contracts.py",
            "services/layer3-knowledge/tests/test_vector_store_tenant_write_isolation.py",
            "services/layer3-knowledge/tests/test_tenant_read_isolation.py",
            "tests/security/test_layer3_similarity_roi_tenant_isolation.py",
        ),
        label="search index tenant scope coverage",
        invariants=(
            TenantInvariant(
                key="search_receives_authenticated_tenant",
                description="graph, vector, and hybrid search use the authenticated tenant id",
                evidence=(("forwards_authenticated_tenant_to_vector_store", "kwargs[\"tenant_id\"] == self.tenant_id", "tenant_id == self.tenant_id"),),
            ),
            TenantInvariant(
                key="forged_metadata_cannot_override_tenant",
                description="forged search/vector metadata cannot override tenant ownership",
                evidence=(("strips_forged_metadata", "hostile_metadata_override_cannot_cross_tenant"),),
            ),
            TenantInvariant(
                key="missing_tenant_fails_closed",
                description="search and graph paths fail closed without tenant context",
                evidence=(("missing_tenant_context_fails_closed", "requires tenant_id", "tenant_id is required"),),
            ),
            TenantInvariant(
                key="cross_tenant_read_write_denied",
                description="graph/search read and write helpers are tenant-scoped",
                evidence=(("cannot_read_other_tenant_entity_by_id", "only_updates_matching_tenant", "only_deletes_matching_tenant"),),
            ),
        ),
    )
