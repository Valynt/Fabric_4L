from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage


pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_billing_webhook_idempotency_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "services/billing/tests/test_billing_service.py",
            "services/billing/tests/test_api.py",
            "tests/integration/billing_entitlements/test_billing_entitlements_regression.py",
            "tests/unit/l7/test_webhook_security.py",
        ),
        label="billing webhook idempotency coverage",
    )
    assert_contains_all(
        "services/billing/tests/test_billing_service.py",
        ("test_duplicate_event_returns_false", "process_webhook"),
        label="billing webhook idempotency tests",
    )

