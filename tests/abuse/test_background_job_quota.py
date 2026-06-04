from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage


pytestmark = [pytest.mark.abuse, pytest.mark.production_readiness]


def test_background_job_quota_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/integration/test_celery_queue_topology.py",
            "services/layer4-agents/tests/test_tenant_rate_limits.py",
            "services/layer4-agents/tests/unit/test_task_scheduler.py",
        ),
        label="background job quota coverage",
    )
    assert_contains_all(
        "config/production-readiness/tenant_quota_policy.json",
        ("quotaExceededAuditEventRequired", "tenantOverrideRequiresApproval"),
        label="tenant quota policy",
    )

