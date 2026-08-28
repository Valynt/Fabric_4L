from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_subscription_updated_webhook_coverage_exists() -> None:
    assert_pytest_coverage(
        ("services/layer4-agents/tests/test_billing_service.py",),
        label="subscription updated coverage",
    )
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        ("test_webhook_subscription_updated_plan_change", "customer.subscription.updated"),
        label="subscription update webhook tests",
    )


def test_subscription_updated_recomputes_plan_and_period_state() -> None:
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        (
            "test_webhook_subscription_updated_plan_change",
            "price_enterprise",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
        ),
        label="subscription update plan and period coverage",
    )
    assert_contains_all(
        "services/layer4-agents/src/layer4_agents/services/billing_service.py",
        ("subscription.plan_id = plan_id", "subscription.cancel_at_period_end", "SubscriptionStatus(status)"),
        label="subscription update handler",
    )
