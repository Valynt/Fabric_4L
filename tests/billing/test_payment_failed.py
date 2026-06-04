from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_paths_exist, assert_readme_documents_gap


pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_payment_failed_provider_gap_is_documented() -> None:
    assert_paths_exist(
        (
            "config/production-readiness/billing_metering_policy.json",
            "k8s/monitoring/billing-alert-rules.yaml",
            "monitoring/grafana/dashboards/billing-revenue.json",
        ),
        label="payment failure policy and monitoring references",
    )
    assert_readme_documents_gap("tests/billing/README.md", "PAYMENT_FAILURE_PROVIDER_EVENT")

