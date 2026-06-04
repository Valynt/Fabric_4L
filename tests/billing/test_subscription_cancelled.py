from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage


pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_subscription_cancelled_coverage_exists() -> None:
    assert_pytest_coverage(
        ("services/billing/tests/test_billing_service.py", "services/billing/tests/test_api.py"),
        label="subscription cancellation coverage",
    )
    assert_contains_all(
        "services/billing/tests/test_billing_service.py",
        ("TestCancelSubscription", "test_cancel_wrong_tenant_raises", "test_subscription_deleted_webhook"),
        label="subscription cancellation billing tests",
    )

