from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_contains_all, assert_readme_documents_gap

pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_trial_state_is_modeled_and_expiration_job_gap_is_documented() -> None:
    assert_contains_all(
        "services/billing/tests/test_models.py",
        ("SubscriptionStatus.TRIALING", "trialing"),
        label="trial status model tests",
    )
    assert_readme_documents_gap("tests/billing/README.md", "TRIAL_EXPIRATION_CLOCK_DRIVEN_JOB")


def test_trialing_status_is_treated_as_active_until_expiration() -> None:
    assert_contains_all(
        "services/billing/src/billing/service.py",
        ("active_statuses", "SubscriptionStatus.TRIALING.value", "get_active_subscription"),
        label="trial entitlement-active service behavior",
    )
    assert_contains_all(
        "services/billing/tests/test_billing_service.py",
        ("test_returns_trialing_subscription", "test_ignores_canceled_subscription"),
        label="trial lifecycle tests",
    )
