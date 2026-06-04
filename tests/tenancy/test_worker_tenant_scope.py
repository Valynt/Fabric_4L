from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.tenancy, pytest.mark.production_readiness]


def test_worker_tenant_scope_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/integration/test_celery_queue_topology.py",
            "services/layer1-ingestion/tests/security/test_celery_tenant_isolation_postgres.py",
            "services/layer4-agents/tests/test_workflow_tenant_isolation.py",
            "services/layer4-agents/tests/test_workflow_start_tenant_invariant.py",
        ),
        label="worker tenant scope coverage",
    )

