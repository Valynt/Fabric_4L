from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_billing_webhook_idempotency_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "services/layer4-agents/tests/test_billing_service.py",
            "tests/integration/billing_entitlements/test_billing_entitlements_regression.py",
            "tests/unit/l7/test_webhook_security.py",
        ),
        label="billing webhook idempotency coverage",
    )
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        ("test_webhook_replay_idempotency_explicit", "test_process_webhook_event_duplicate_ignored"),
        label="billing webhook idempotency tests",
    )


def test_webhook_replay_does_not_duplicate_side_effects() -> None:
    assert_contains_all(
        "services/layer4-agents/tests/test_billing_service.py",
        (
            "test_webhook_replay_idempotency_explicit",
            "test_process_webhook_event_duplicate_ignored",
            "mock_db.add.assert_not_called",
            "test_ingest_usage_event_duplicate_returns_existing",
        ),
        label="webhook replay side-effect coverage",
    )
    assert_contains_all(
        "services/layer4-agents/src/layer4_agents/models/billing.py",
        ("Duplicate event detection", "UniqueConstraint", "event_id"),
        label="billing webhook idempotency model",
    )
    assert_contains_all(
        "tests/billing/README.md",
        ("must not duplicate processed event rows", "invoice/credit side effects", "entitlement grants"),
        label="webhook replay documentation",
    )


def test_billing_state_changes_emit_structured_audit_evidence() -> None:
    assert_contains_all(
        "services/layer4-agents/src/layer4_agents/services/billing_service.py",
        (
            "billing.webhook.duplicate_processed",
            "_emit_webhook_metric",
            "billing.webhook.terminal_failure",
        ),
        label="billing structured state-change logs",
    )
    assert_contains_all(
        "tests/audit/test_billing_changes_logged.py",
        ("test_billing_change_audit_gap_is_documented_with_related_coverage", "BILLING_AUDIT_EVENT_FIXTURE"),
        label="billing audit readiness coverage",
    )
    assert_contains_all(
        "tests/billing/README.md",
        ("Billing state changes must emit structured audit/log evidence", "BILLING_AUDIT_EVENT_FIXTURE"),
        label="billing audit documentation",
    )
