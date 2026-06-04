from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage


pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_subscription_created_coverage_exists() -> None:
    assert_pytest_coverage(
        ("services/billing/tests/test_billing_service.py", "services/billing/tests/test_api.py"),
        label="subscription created coverage",
    )
    assert_contains_all(
        "services/billing/tests/test_billing_service.py",
        ("TestCreateSubscription", "test_creates_subscription", "tenant_id"),
        label="subscription creation billing tests",
    )

