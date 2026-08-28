from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_subscription_created_coverage_exists() -> None:
    assert_pytest_coverage(
        ("services/layer4-agents/tests/test_billing_service.py",),
        label="subscription created coverage",
    )
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        ("test_webhook_subscription_created", "customer.subscription.created", "tenant_id"),
        label="subscription creation billing tests",
    )


def test_subscription_created_webhook_creates_tenant_scoped_subscription() -> None:
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        ("test_webhook_subscription_created", "customer.subscription.created", "tenant_abc123"),
        label="subscription created webhook coverage",
    )
    assert_contains_all(
        "services/layer4-agents/src/layer4_agents/services/billing_service.py",
        ("_handle_subscription_created", "tenant_id=customer.tenant_id", "stripe_subscription_id=stripe_sub_id"),
        label="subscription created handler",
    )
