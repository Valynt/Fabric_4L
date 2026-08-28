from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_subscription_cancelled_coverage_exists() -> None:
    assert_pytest_coverage(
        ("services/layer4-agents/tests/test_billing_service.py",),
        label="subscription cancellation coverage",
    )
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        ("test_cancel_subscription_at_period_end", "test_cancel_subscription_immediately_downgrades_to_free", "test_webhook_subscription_deleted_downgrades_to_free"),
        label="subscription cancellation billing tests",
    )


def test_cancellation_and_grace_period_behavior_is_locked() -> None:
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        (
            "test_cancel_subscription_at_period_end",
            "test_cancel_subscription_immediately_downgrades_to_free",
            "test_webhook_subscription_deleted_downgrades_to_free",
            "cancel_at_period_end",
        ),
        label="cancellation and grace-period coverage",
    )
    assert_contains_all(
        "tests/billing/README.md",
        ("Cancellation at period end is the grace-period path", "CANCELLATION_GRACE_PERIOD_PROVIDER_CLOCK"),
        label="cancellation grace-period documentation",
    )
