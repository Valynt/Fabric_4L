from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.tenancy, pytest.mark.production_readiness]


def test_api_tenant_scope_coverage_exists() -> None:
    assert_pytest_coverage(
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
    )

