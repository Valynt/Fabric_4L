"""Data Quality and Trust tests for billing models.

Validates that every important billing data object has:
- Provenance (source_system, stripe IDs)
- Validation (reconciliation, integrity checks)
- Freshness (updated_at timestamps)
- Ownership (tenant_id, customer_id)
- Confidence indicators (status, sync_state)
- Error handling (last_error, failure fields)
- Reconciliation paths (reconcile methods)
- Auditability (created_at, timestamps)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from layer4_agents.models.billing import (
    BillingCharge,
    BillingCustomer,
    BillingInvoice,
    BillingInvoiceItem,
    BillingSubscription,
    BillingUsageEvent,
    BillingWebhookEvent,
    ChargeStatus,
    InvoiceStatus,
    PlanId,
    SubscriptionStatus,
    UsageEventStatus,
)


class TestProvenance:
    """Data origin must be traceable."""

    def test_usage_event_has_source_system(self):
        event = BillingUsageEvent(
            id="evt_1",
            tenant_id="t1",
            customer_id="c1",
            event_id="e1",
            event_name="api_call",
            metric_name="tokens",
            quantity=100.0,
            source_system="api",
        )
        assert event.source_system == "api"

    def test_customer_tracks_stripe_sync_provenance(self):
        customer = BillingCustomer(
            id="cust_1",
            tenant_id="t1",
            email="a@b.com",
            stripe_customer_id="cus_stripe_1",
            stripe_sync_status="synced",
            stripe_sync_attempted_at=datetime.now(UTC),
        )
        assert customer.stripe_sync_status == "synced"
        assert customer.stripe_customer_id is not None

    def test_subscription_tracks_stripe_source(self):
        sub = BillingSubscription(
            id="sub_1",
            tenant_id="t1",
            customer_id="cust_1",
            stripe_subscription_id="sub_stripe_1",
            plan_id=PlanId.PRO,
            status=SubscriptionStatus.ACTIVE,
        )
        assert sub.stripe_subscription_id == "sub_stripe_1"

    def test_invoice_tracks_stripe_source(self):
        inv = BillingInvoice(
            id="inv_1",
            tenant_id="t1",
            customer_id="cust_1",
            invoice_number="INV-001",
            stripe_invoice_id="in_stripe_1",
            status=InvoiceStatus.OPEN,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )
        assert inv.stripe_invoice_id == "in_stripe_1"

    def test_charge_tracks_stripe_source(self):
        charge = BillingCharge(
            id="ch_1",
            tenant_id="t1",
            customer_id="cust_1",
            stripe_charge_id="ch_stripe_1",
            stripe_payment_intent_id="pi_1",
            status=ChargeStatus.SUCCEEDED,
            amount=1000,
        )
        assert charge.stripe_charge_id == "ch_stripe_1"


class TestFreshness:
    """Data must have clear freshness indicators."""

    def test_webhook_event_has_updated_at(self):
        now = datetime.now(UTC)
        event = BillingWebhookEvent(
            id="evt_1",
            type="test",
            status="pending",
            updated_at=now,
        )
        assert event.updated_at == now

    def test_customer_has_created_and_updated_at(self):
        now = datetime.now(UTC)
        customer = BillingCustomer(
            id="cust_1",
            tenant_id="t1",
            email="a@b.com",
            created_at=now,
            updated_at=now,
        )
        assert customer.created_at == now
        assert customer.updated_at == now

    def test_subscription_has_period_freshness(self):
        start = datetime.now(UTC)
        end = start + timedelta(days=30)
        sub = BillingSubscription(
            id="sub_1",
            tenant_id="t1",
            customer_id="cust_1",
            plan_id=PlanId.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=start,
            current_period_end=end,
        )
        assert sub.current_period_start == start
        assert sub.current_period_end == end

    def test_usage_event_has_processing_freshness(self):
        now = datetime.now(UTC)
        event = BillingUsageEvent(
            id="evt_1",
            tenant_id="t1",
            customer_id="c1",
            event_id="e1",
            event_name="api_call",
            metric_name="tokens",
            quantity=100.0,
            created_at=now,
            processed_at=now,
        )
        assert event.created_at == now
        assert event.processed_at == now


class TestOwnership:
    """Every record must declare its tenant and customer owner."""

    def test_all_models_have_tenant_id(self):
        models = [
            BillingCustomer(id="c1", tenant_id="t1", email="a@b.com"),
            BillingSubscription(id="s1", tenant_id="t1", customer_id="c1", plan_id=PlanId.FREE),
            BillingUsageEvent(id="e1", tenant_id="t1", customer_id="c1", event_id="ev1", event_name="n", metric_name="m", quantity=1.0),
            BillingInvoice(id="i1", tenant_id="t1", customer_id="c1", invoice_number="001", period_start=datetime.now(UTC), period_end=datetime.now(UTC)),
            BillingInvoiceItem(id="ii1", tenant_id="t1", invoice_id="i1", type="metered", description="d", unit_amount=100, amount=100),
            BillingCharge(id="ch1", tenant_id="t1", customer_id="c1", status=ChargeStatus.PENDING, amount=100),
            BillingWebhookEvent(id="wh1", tenant_id="t1", type="test"),
        ]
        for model in models:
            assert getattr(model, "tenant_id", None) is not None, f"{type(model).__name__} missing tenant_id"


class TestReconciliation:
    """Invoice totals must be internally consistent."""

    def test_valid_invoice_reconciles_cleanly(self):
        inv = BillingInvoice(
            id="inv_1",
            tenant_id="t1",
            customer_id="c1",
            invoice_number="001",
            status=InvoiceStatus.OPEN,
            subtotal=10000,
            tax=500,
            total=10500,
            amount_paid=0,
            amount_due=10500,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )
        report = inv.reconcile()
        assert report["valid"] is True
        assert report["discrepancy_cents"] == 0
        assert report["checks"] == []

    def test_invoice_detects_total_mismatch(self):
        inv = BillingInvoice(
            id="inv_1",
            tenant_id="t1",
            customer_id="c1",
            invoice_number="001",
            status=InvoiceStatus.OPEN,
            subtotal=10000,
            tax=500,
            total=99999,  # Wrong
            amount_paid=0,
            amount_due=99999,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )
        report = inv.reconcile()
        assert report["valid"] is False
        assert any("total mismatch" in c for c in report["checks"])
        assert report["discrepancy_cents"] > 0

    def test_invoice_detects_amount_due_mismatch(self):
        inv = BillingInvoice(
            id="inv_1",
            tenant_id="t1",
            customer_id="c1",
            invoice_number="001",
            status=InvoiceStatus.OPEN,
            subtotal=10000,
            tax=500,
            total=10500,
            amount_paid=5000,
            amount_due=10000,  # Wrong: should be 5500
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )
        report = inv.reconcile()
        assert report["valid"] is False
        assert any("amount_due mismatch" in c for c in report["checks"])

    def test_invoice_reconciles_line_items(self):
        inv = BillingInvoice(
            id="inv_1",
            tenant_id="t1",
            customer_id="c1",
            invoice_number="001",
            status=InvoiceStatus.OPEN,
            subtotal=10000,
            tax=500,
            total=10500,
            amount_paid=0,
            amount_due=10500,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )
        # Simulate loaded items (ORM relationship)
        inv.items = [
            BillingInvoiceItem(
                id="ii1", tenant_id="t1", invoice_id="inv_1",
                type="subscription", description="Pro plan",
                unit_amount=10000, amount=10000,
            ),
            BillingInvoiceItem(
                id="ii2", tenant_id="t1", invoice_id="inv_1",
                type="tax", description="Tax",
                unit_amount=500, amount=500,
            ),
        ]
        report = inv.reconcile()
        assert report["valid"] is True
        assert report["discrepancy_cents"] == 0

    def test_invoice_detects_line_item_mismatch(self):
        inv = BillingInvoice(
            id="inv_1",
            tenant_id="t1",
            customer_id="c1",
            invoice_number="001",
            status=InvoiceStatus.OPEN,
            subtotal=10000,
            tax=500,
            total=10500,
            amount_paid=0,
            amount_due=10500,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )
        inv.items = [
            BillingInvoiceItem(
                id="ii1", tenant_id="t1", invoice_id="inv_1",
                type="subscription", description="Pro plan",
                unit_amount=8000, amount=8000,  # Under by 2500
            ),
        ]
        report = inv.reconcile()
        assert report["valid"] is False
        assert any("line items total mismatch" in c for c in report["checks"])


class TestErrorHandlingAndConfidence:
    """Records must expose error state and confidence clearly."""

    def test_webhook_event_tracks_retry_errors(self):
        event = BillingWebhookEvent(
            id="evt_1",
            type="test",
            status="failed",
            attempt_count=3,
            last_error="Connection timeout",
        )
        assert event.attempt_count == 3
        assert event.last_error == "Connection timeout"

    def test_charge_tracks_failure_details(self):
        charge = BillingCharge(
            id="ch1",
            tenant_id="t1",
            customer_id="c1",
            status=ChargeStatus.FAILED,
            amount=1000,
            failure_code="card_declined",
            failure_message="Your card was declined.",
            decline_code="insufficient_funds",
        )
        assert charge.failure_code == "card_declined"
        assert charge.decline_code == "insufficient_funds"

    def test_customer_tracks_sync_error(self):
        customer = BillingCustomer(
            id="cust_1",
            tenant_id="t1",
            email="a@b.com",
            stripe_sync_status="failed",
            stripe_sync_error="Invalid API key",
        )
        assert customer.stripe_sync_error == "Invalid API key"

    def test_usage_event_has_processing_status(self):
        event = BillingUsageEvent(
            id="evt_1",
            tenant_id="t1",
            customer_id="c1",
            event_id="e1",
            event_name="api_call",
            metric_name="tokens",
            quantity=100.0,
            status=UsageEventStatus.PROCESSED,
        )
        assert event.status == UsageEventStatus.PROCESSED


class TestAuditability:
    """Records must be auditable via timestamps and identifiers."""

    def test_invoice_has_full_lifecycle_timestamps(self):
        now = datetime.now(UTC)
        inv = BillingInvoice(
            id="inv_1",
            tenant_id="t1",
            customer_id="c1",
            invoice_number="001",
            status=InvoiceStatus.PAID,
            period_start=now,
            period_end=now,
            created_at=now,
            due_date=now + timedelta(days=30),
            paid_at=now,
        )
        assert inv.created_at == now
        assert inv.paid_at == now
        assert inv.due_date is not None

    def test_charge_has_lifecycle_timestamps(self):
        now = datetime.now(UTC)
        charge = BillingCharge(
            id="ch1",
            tenant_id="t1",
            customer_id="c1",
            status=ChargeStatus.SUCCEEDED,
            amount=1000,
            created_at=now,
            captured_at=now,
        )
        assert charge.created_at == now
        assert charge.captured_at == now
