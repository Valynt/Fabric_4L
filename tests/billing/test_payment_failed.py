from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_paths_exist, assert_readme_documents_gap


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


def test_payment_failed_marks_subscription_past_due_and_is_documented() -> None:
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        ("test_handle_payment_failed_updates_status", "_handle_payment_failed", "SubscriptionStatus.PAST_DUE"),
        label="payment failed lifecycle tests",
    )
    assert_contains_all(
        "services/layer4-agents/src/layer4_agents/services/billing_service.py",
        ("elif event_type == \"invoice.payment_failed\"", "_handle_payment_failed", "SubscriptionStatus.PAST_DUE"),
        label="payment failed handler",
    )
    assert_contains_all(
        "tests/billing/README.md",
        ("Failed payment webhooks mark the subscription `past_due`", "provider dunning/retry policy"),
        label="payment failed documentation",
    )
