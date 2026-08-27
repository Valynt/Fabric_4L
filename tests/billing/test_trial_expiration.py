from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_contains_all, assert_readme_documents_gap

pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_trial_state_is_modeled_and_expiration_job_gap_is_documented() -> None:
    assert_contains_all(
        "services/layer4-agents/src/layer4_agents/models/billing.py",
        ("SubscriptionStatus.TRIALING", "trialing"),
        label="trial status model tests",
    )
    assert_readme_documents_gap("tests/billing/README.md", "TRIAL_EXPIRATION_CLOCK_DRIVEN_JOB")


def test_trialing_status_is_treated_as_active_until_expiration() -> None:
    assert_contains_all(
        "services/layer4-agents/src/layer4_agents/services/billing_service.py",
        ("get_active_subscription", "SubscriptionStatus.ACTIVE", "SubscriptionStatus.TRIALING"),
        label="trial entitlement-active service behavior",
    )
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        ("test_subscription_is_active_property", "SubscriptionStatus.TRIALING"),
        label="trial lifecycle tests",
    )
