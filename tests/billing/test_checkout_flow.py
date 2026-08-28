from __future__ import annotations

import pytest
from tests.production_readiness.manifest import (
    assert_contains_all,
    assert_paths_exist,
    assert_readme_documents_gap,
)

pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_checkout_flow_has_documented_non_credential_gap_and_ui_coverage() -> None:
    assert_paths_exist(
        (
            "apps/web/e2e/journeys/j20-billing-entitlement-gates.spec.ts",
            "services/layer4-agents/tests/test_billing_service.py",
            "contracts/openapi/layer7-billing.json",
        ),
        label="checkout flow references",
    )
    assert_readme_documents_gap("tests/billing/README.md", "CHECKOUT_PROVIDER_SANDBOX")


def test_checkout_flow_uses_provider_managed_subscription_sessions() -> None:
    assert_contains_all(
        "services/layer4-agents/src/layer4_agents/services/billing_service.py",
        ('mode="subscription"', "checkout.Session.create", "success_url", "cancel_url"),
        label="checkout session implementation",
    )
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        ("test_create_checkout_session", "stripe_customer_id", "Customer not found"),
        label="checkout session tests",
    )
