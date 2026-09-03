from __future__ import annotations

from .conftest import assert_contains_all, read_text

EXPECTED_BILLING_TABLES = {
    "l7_billing_plans",
    "l7_billing_usage_events",
    "l7_billing_usage_aggregates",
    "l7_billing_invoices",
    "l7_billing_payment_states",
    "billing_customers",
    "billing_subscriptions",
    "billing_webhook_events",
    "billing_plan_versions",
    "billing_usage_events",
    "billing_invoices",
    "billing_invoice_items",
    "billing_charges",
}


def test_billing_state_restore_is_part_of_dry_run_evidence(restore_dry_run_evidence: dict) -> None:
    billing = restore_dry_run_evidence["restore_validations"]["billing_state"]
    assert EXPECTED_BILLING_TABLES.issubset(set(billing["tables"]))
    assert billing["tenant_scoped_validation_required"] is True
    assert billing["idempotency_validation_required"] is True


def test_billing_restore_scope_matches_billing_models_and_runbook() -> None:
    l7_models = read_text("services/layer7-billing/src/layer7_billing/models.py")
    billing_models = read_text("services/layer4-agents/src/layer4_agents/models/billing.py")
    runbook = read_text("docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md")
    assert_contains_all(
        l7_models,
        [
            "l7_billing_usage_events",
            "l7_billing_usage_aggregates",
            "l7_billing_invoices",
            "l7_billing_payment_states",
            "tenant_id",
        ],
        label="Layer 7 billing models",
    )
    assert_contains_all(
        billing_models,
        [
            "billing_customers",
            "billing_subscriptions",
            "billing_webhook_events",
            "tenant_id",
        ],
        label="billing service models",
    )
    assert_contains_all(
        runbook,
        [
            "Billing State Restore",
            "usage events",
            "aggregates",
            "invoices",
            "payment state",
            "webhook idempotency",
        ],
        label="billing restore runbook",
    )
