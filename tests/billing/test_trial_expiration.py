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

