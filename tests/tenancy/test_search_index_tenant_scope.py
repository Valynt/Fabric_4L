from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.tenancy, pytest.mark.production_readiness]


def test_search_index_tenant_scope_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/layer3/test_endpoint_tenant_isolation.py",
            "tests/layer3/test_graph_repository_tenant_contracts.py",
            "services/layer3-knowledge/tests/test_vector_store_tenant_write_isolation.py",
            "services/layer3-knowledge/tests/test_tenant_read_isolation.py",
            "tests/security/test_layer3_similarity_roi_tenant_isolation.py",
        ),
        label="search index tenant scope coverage",
    )

