from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.reliability, pytest.mark.production_readiness]


def test_error_budget_policy_has_dashboard_and_ci_coverage() -> None:
    assert_contains_all(
        "monitoring/grafana/dashboards/slo-error-budget-burn-rate.json",
        ("error", "budget", "burn"),
        label="error budget burn dashboard",
    )
    assert_pytest_coverage(
        ("tests/ci/test_perf_slo_baseline.py",),
        label="error budget regression coverage",
    )

