from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from layer4_agents.models.billing import ChargeStatus, InvoiceStatus
from layer4_agents.services.invoice_service import InvoiceService

NOW = datetime(2026, 7, 1, tzinfo=UTC)
TENANT = "550e8400-e29b-41d4-a716-446655440000"


class Result:
    def __init__(self, *, scalar=None, scalars=None, row=None):
        self._scalar = scalar
        self._scalars = [] if scalars is None else scalars
        self._row = row

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return SimpleNamespace(all=lambda: self._scalars)

    def one(self):
        return self._row


class DB:
    def __init__(self, results=()):
        self.results = list(results)
        self.added = []
        self.flushes = 0
        self.queries = []

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flushes += 1

    async def execute(self, query):
        self.queries.append(query)
        return self.results.pop(0)


def service(results=(), tenant_id=TENANT):
    db = DB(results)
    return InvoiceService(db, tenant_id), db


@pytest.mark.asyncio
async def test_tenant_is_required_for_mutations_and_reads_fail_closed() -> None:
    svc, _ = service(tenant_id=None)
    with pytest.raises(ValueError, match="tenant_id is required"):
        await svc.create_invoice("customer", NOW, NOW + timedelta(days=30))
    with pytest.raises(ValueError, match="tenant_id is required"):
        await svc.add_invoice_item("invoice", "item", 100)
    with pytest.raises(ValueError, match="tenant_id is required"):
        await svc.finalize_invoice("invoice")
    with pytest.raises(ValueError, match="tenant_id is required"):
        await svc.mark_invoice_paid("invoice")
    with pytest.raises(ValueError, match="tenant_id is required"):
        await svc.void_invoice("invoice")
    with pytest.raises(ValueError, match="tenant_id is required"):
        await svc.record_charge("customer", 100)
    with pytest.raises(ValueError, match="tenant_id is required"):
        await svc.refund_charge("charge")
    assert await svc.get_invoice("invoice") is None
    assert await svc.get_invoice_by_number("INV") is None
    assert await svc.list_invoices() == []
    assert await svc.get_charge("charge") is None
    assert await svc.list_charges() == []
    assert (await svc.get_revenue_summary(NOW, NOW)).model_dump(exclude_none=True) == {}
    assert (await svc.get_customer_balance("customer")).model_dump(exclude_none=True) == {}


@pytest.mark.asyncio
async def test_create_invoice_generates_defaults_and_preserves_explicit_values() -> None:
    svc, db = service()
    generated = await svc.create_invoice("customer", NOW, NOW + timedelta(days=1))
    assert generated.tenant_id == TENANT
    assert generated.invoice_number.startswith("INV-550e8400-202")
    assert generated.status == InvoiceStatus.DRAFT
    assert generated.due_date == NOW + timedelta(days=31)
    assert generated.amount_due == generated.total == 0

    due = NOW + timedelta(days=10)
    explicit = await svc.create_invoice(
        "customer",
        NOW,
        NOW + timedelta(days=1),
        invoice_number="INV-EXPLICIT",
        subscription_id="sub",
        currency="EUR",
        description="Description",
        due_date=due,
    )
    assert explicit.invoice_number == "INV-EXPLICIT"
    assert explicit.subscription_id == "sub"
    assert explicit.currency == "EUR"
    assert explicit.description == "Description"
    assert explicit.due_date == due
    assert db.added == [generated, explicit]
    assert db.flushes == 2


@pytest.mark.asyncio
async def test_add_invoice_item_calculates_unit_amount_and_updates_invoice() -> None:
    invoice = SimpleNamespace(subtotal=200, tax=30, total=230, amount_paid=50, amount_due=180)
    svc, db = service([Result(scalar=invoice), Result(scalar=None)])
    item = await svc.add_invoice_item(
        "invoice",
        "Seats",
        600,
        quantity=3,
        item_type="subscription",
        period_start=NOW,
        period_end=NOW + timedelta(days=30),
        usage_quantity=3,
        usage_metric="seat",
        tax_amount=20,
        discount_amount=10,
        price_id="price",
        metadata={"source": "test"},
    )
    assert item.unit_amount == 200
    assert item.metadata == {"source": "test"}
    assert invoice.subtotal == 800
    assert invoice.total == 830
    assert invoice.amount_due == 780

    zero = await svc.add_invoice_item("missing", "Free", 0, quantity=0)
    assert zero.unit_amount == 0
    assert db.flushes == 2


@pytest.mark.asyncio
async def test_invoice_queries_apply_options_filters_and_pagination() -> None:
    invoice = object()
    invoices = [object(), object()]
    svc, db = service(
        [
            Result(scalar=invoice),
            Result(scalar=invoice),
            Result(scalar=invoice),
            Result(scalars=invoices),
        ]
    )
    assert await svc.get_invoice("id", include_items=False, include_charges=False) is invoice
    assert await svc.get_invoice("id", include_items=True, include_charges=True) is invoice
    assert await svc.get_invoice_by_number("INV-1") is invoice
    assert (
        await svc.list_invoices(
            customer_id="customer",
            status=InvoiceStatus.OPEN,
            limit=12,
            offset=3,
            period_start_after=NOW,
            period_end_before=NOW + timedelta(days=30),
        )
        == invoices
    )
    rendered = [str(query) for query in db.queries]
    assert all("tenant_id" in query for query in rendered)
    assert "customer_id" in rendered[-1]
    assert "period_start" in rendered[-1] and "period_end" in rendered[-1]


@pytest.mark.asyncio
async def test_finalize_invoice_validates_state_and_recalculates_totals() -> None:
    svc, db = service()

    async def missing(*_args, **_kwargs):
        return None

    svc.get_invoice = missing
    with pytest.raises(ValueError, match="Invoice not found"):
        await svc.finalize_invoice("missing")

    wrong = SimpleNamespace(status=InvoiceStatus.OPEN)

    async def wrong_state(*_args, **_kwargs):
        return wrong

    svc.get_invoice = wrong_state
    with pytest.raises(ValueError, match="Cannot finalize"):
        await svc.finalize_invoice("open")

    invoice = SimpleNamespace(
        status=InvoiceStatus.DRAFT,
        items=[SimpleNamespace(amount=100), SimpleNamespace(amount=250)],
        tax=35,
        amount_paid=50,
        invoice_number="INV",
    )

    async def found(*_args, **_kwargs):
        return invoice

    svc.get_invoice = found
    assert await svc.finalize_invoice("draft") is invoice
    assert (invoice.subtotal, invoice.total, invoice.amount_due, invoice.balance) == (
        350,
        385,
        335,
        335,
    )
    assert invoice.status == InvoiceStatus.OPEN
    assert db.flushes == 1


@pytest.mark.asyncio
async def test_mark_paid_supports_partial_full_and_missing_invoice() -> None:
    svc, db = service()

    async def missing(*_args, **_kwargs):
        return None

    svc.get_invoice = missing
    with pytest.raises(ValueError, match="Invoice not found"):
        await svc.mark_invoice_paid("missing")

    invoice = SimpleNamespace(
        amount_due=1000,
        amount_paid=0,
        total=1000,
        balance=1000,
        status=InvoiceStatus.OPEN,
        invoice_number="INV",
        paid_at=None,
    )

    async def found(*_args, **_kwargs):
        return invoice

    svc.get_invoice = found
    await svc.mark_invoice_paid("invoice", 400)
    assert invoice.amount_paid == 400 and invoice.amount_due == 600
    assert invoice.status == InvoiceStatus.OPEN
    await svc.mark_invoice_paid("invoice")
    assert invoice.amount_paid == 1000 and invoice.amount_due == invoice.balance == 0
    assert invoice.status == InvoiceStatus.PAID and invoice.paid_at is not None
    assert db.flushes == 2


@pytest.mark.asyncio
async def test_void_invoice_rejects_paid_and_records_reason() -> None:
    svc, db = service()

    async def missing(*_args, **_kwargs):
        return None

    svc.get_invoice = missing
    with pytest.raises(ValueError, match="Invoice not found"):
        await svc.void_invoice("missing")

    paid = SimpleNamespace(status=InvoiceStatus.PAID)

    async def paid_invoice(*_args, **_kwargs):
        return paid

    svc.get_invoice = paid_invoice
    with pytest.raises(ValueError, match="Cannot void"):
        await svc.void_invoice("paid")

    invoice = SimpleNamespace(
        status=InvoiceStatus.OPEN,
        metadata=None,
        voided_at=None,
        invoice_number="INV",
    )

    async def open_invoice(*_args, **_kwargs):
        return invoice

    svc.get_invoice = open_invoice
    assert await svc.void_invoice("open", "duplicate") is invoice
    assert invoice.status == InvoiceStatus.VOID
    assert invoice.metadata == {"void_reason": "duplicate"}
    assert invoice.voided_at is not None and db.flushes == 1


@pytest.mark.asyncio
async def test_charge_crud_linked_payment_filters_and_refunds() -> None:
    charge = SimpleNamespace(net_amount=700, amount_refunded=0, metadata=None, refunded_at=None)
    charges = [charge]
    svc, db = service([Result(scalar=charge), Result(scalars=charges)])
    payments = []

    async def paid(invoice_id, amount):
        payments.append((invoice_id, amount))

    svc.mark_invoice_paid = paid
    succeeded = await svc.record_charge(
        "customer",
        700,
        invoice_id="invoice",
        stripe_charge_id="ch",
        payment_method_id="pm",
        payment_method_type="card",
        receipt_url="https://example.test/receipt",
        description="Payment",
        metadata={"key": "value"},
    )
    assert succeeded.captured_at is not None
    assert payments == [("invoice", 700)]
    failed = await svc.record_charge(
        "customer",
        100,
        status=ChargeStatus.FAILED,
        failure_code="declined",
        failure_message="Declined",
    )
    assert failed.captured_at is None
    assert await svc.get_charge("charge") is charge
    assert (
        await svc.list_charges(
            customer_id="customer",
            invoice_id="invoice",
            status=ChargeStatus.SUCCEEDED,
            limit=5,
            offset=2,
        )
        == charges
    )
    assert "customer_id" in str(db.queries[-1]) and "invoice_id" in str(db.queries[-1])

    async def found(_charge_id):
        return charge

    svc.get_charge = found
    with pytest.raises(ValueError, match="exceeds net amount"):
        await svc.refund_charge("charge", 701)
    await svc.refund_charge("charge", 200, "requested")
    assert charge.amount_refunded == 200
    assert charge.metadata == {"refund_reason": "requested"}
    assert charge.refunded_at is not None

    charge.net_amount = 500
    await svc.refund_charge("charge")
    assert charge.amount_refunded == 700

    async def missing(_charge_id):
        return None

    svc.get_charge = missing
    with pytest.raises(ValueError, match="Charge not found"):
        await svc.refund_charge("missing")


@pytest.mark.asyncio
async def test_reporting_normalizes_null_aggregates_and_currency_values() -> None:
    invoice_row = SimpleNamespace(count=2, total=12345, paid=10000, due=2345)
    charge_row = SimpleNamespace(count=3, total=15000, refunded=1000)
    open_row = SimpleNamespace(count=2, total_due=2345)
    paid_row = SimpleNamespace(total_paid=14000)
    svc, _ = service(
        [
            Result(row=invoice_row),
            Result(row=charge_row),
            Result(row=open_row),
            Result(row=paid_row),
        ]
    )
    summary = await svc.get_revenue_summary(NOW, NOW + timedelta(days=30))
    assert summary.invoices["total_dollars"] == 123.45
    assert summary.charges["refunded_cents"] == 1000
    balance = await svc.get_customer_balance("customer")
    assert balance.customer_id == "customer"
    assert balance.open_invoices["amount_due_dollars"] == 23.45
    assert balance.lifetime_paid_cents == 14000
    assert balance.lifetime_paid_dollars == 140.0
