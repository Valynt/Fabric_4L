from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage


pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_subscription_updated_webhook_coverage_exists() -> None:
    assert_pytest_coverage(
        ("services/billing/tests/test_billing_service.py",),
        label="subscription updated coverage",
    )
    assert_contains_all(
        "services/billing/tests/test_billing_service.py",
        ("test_subscription_updated_webhook", "customer.subscription.updated"),
        label="subscription update webhook tests",
    )

