from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_paths_exist


pytestmark = [pytest.mark.reliability, pytest.mark.production_readiness]


def test_slo_policy_and_dashboards_exist() -> None:
    assert_paths_exist(
        (
            "config/production-readiness/slo_sla_policy.json",
            "docs/slo/performance-slo.v1.json",
            "monitoring/grafana/dashboards/slo-detailed.json",
            "monitoring/grafana/dashboards/slo-error-budget-burn-rate.json",
            "docs/troubleshooting/runbooks/application/slo-breach-response.md",
        ),
        label="SLO policy and dashboard evidence",
    )


def test_slo_policy_declares_enforcement_scope() -> None:
    assert_contains_all(
        "config/production-readiness/slo_sla_policy.json",
        ("slo", "sla", "production", "evidence"),
        label="SLO/SLA readiness policy",
    )

