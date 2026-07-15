from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_entitlement_sync_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/contract/test_billing_contracts.py",
            "tests/integration/billing_entitlements/test_billing_entitlements_regression.py",
            "services/layer4-agents/tests/test_plan_version_billing.py",
        ),
        label="entitlement sync coverage",
    )


def test_entitlements_follow_subscription_state_changes() -> None:
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        (
            "test_check_entitlement_pro_has_advanced_models",
            "test_check_entitlement_free_no_advanced_models",
            "test_cancel_subscription_immediately_downgrades_to_free",
            "test_webhook_subscription_deleted_downgrades_to_free",
        ),
        label="entitlement subscription-state coverage",
    )
    assert_contains_all(
        "tests/integration/billing_entitlements/test_billing_entitlements_regression.py",
        ("test_upgrade_recomputes_available_quota", "test_downgrade_can_trigger_overage"),
        label="entitlement recomputation coverage",
    )
