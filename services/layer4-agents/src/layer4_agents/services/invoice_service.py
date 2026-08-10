from __future__ import annotations

"""Invoice and charge management service.

Handles invoice generation, retrieval, payment tracking, and charge records.
Integrates with Stripe for invoice synchronization and payment processing.
"""


import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..models.billing import (
    BillingCharge,
    BillingInvoice,
    BillingInvoiceItem,
    ChargeStatus,
    InvoiceStatus,
)


class InvoiceService_get_revenue_summaryResult(TypedDictModel):
    charges: dict[str, Any] | None = None
    invoices: dict[str, Any] | None = None
    period: dict[str, Any] | None = None

class InvoiceService_get_customer_balanceResult(TypedDictModel):
    customer_id: Any | None = None
    lifetime_paid_cents: bool | None = None
    lifetime_paid_dollars: Any | None = None
    open_invoices: dict[str, Any] | None = None

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for invoice and charge management."""

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    # ====================================================================================
    # Invoice CRUD Operations
    # ====================================================================================

    async def create_invoice(
        self,
        customer_id: str,
        period_start: datetime,
        period_end: datetime,
        invoice_number: str | None = None,
        subscription_id: str | None = None,
        currency: str = "USD",
        description: str | None = None,
        due_date: datetime | None = None,
    ) -> BillingInvoice:
        """Create a new invoice.

        Args:
            customer_id: Customer being invoiced
            period_start: Billing period start
            period_end: Billing period end
            invoice_number: Optional invoice number (generated if not provided)
            subscription_id: Optional subscription link
            currency: Currency code (default USD)
            description: Invoice description
            due_date: Due date (defaults to period_end + 30 days)

        Returns:
            Created invoice
        """
        if not self.tenant_id:
            raise ValueError("tenant_id is required")

        if not invoice_number:
            # Generate invoice number: INV-{tenant_short}-{YYYYMMDD}-{random}
            date_str = datetime.now(UTC).strftime("%Y%m%d")
            tenant_short = self.tenant_id[:8]
            random_suffix = str(uuid.uuid4())[:8].upper()
            invoice_number = f"INV-{tenant_short}-{date_str}-{random_suffix}"

        if not due_date:
            due_date = period_end + timedelta(days=30)

        invoice = BillingInvoice(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            subscription_id=subscription_id,
            status=InvoiceStatus.DRAFT,
            currency=currency,
            period_start=period_start,
            period_end=period_end,
            description=description,
            due_date=due_date,
            subtotal=0,
            tax=0,
            total=0,
            amount_paid=0,
            amount_due=0,
            balance=0,
        )

        self.db.add(invoice)
        await self.db.flush()
        logger.info(f"Created invoice {invoice_number} for customer {customer_id}")
        return invoice

    async def add_invoice_item(
        self,
        invoice_id: str,
        description: str,
        amount: int,  # cents
        quantity: float = 1.0,
        unit_amount: int | None = None,
        item_type: str = "one_time",
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        usage_quantity: float | None = None,
        usage_metric: str | None = None,
        tax_amount: int = 0,
        discount_amount: int = 0,
        price_id: str | None = None,
        metadata: dict | None = None,
    ) -> BillingInvoiceItem:
        """Add a line item to an invoice.

        Args:
            invoice_id: Parent invoice ID
            description: Line item description
            amount: Total amount in cents
            quantity: Quantity
            unit_amount: Price per unit in cents (calculated if not provided)
            item_type: Item type (subscription, metered, one_time, proration)
            period_start: Period start (for subscription items)
            period_end: Period end (for subscription items)
            usage_quantity: Usage quantity (for metered items)
            usage_metric: Usage metric name (for metered items)
            tax_amount: Tax amount in cents
            discount_amount: Discount amount in cents
            price_id: Stripe price ID
            metadata: Additional metadata

        Returns:
            Created invoice item
        """
        if not self.tenant_id:
            raise ValueError("tenant_id is required")

        if unit_amount is None and quantity != 0:
            unit_amount = int(amount / quantity)
        elif unit_amount is None:
            unit_amount = 0

        item = BillingInvoiceItem(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            invoice_id=invoice_id,
            type=item_type,
            description=description,
            quantity=quantity,
            unit_amount=unit_amount,
            amount=amount,
            period_start=period_start,
            period_end=period_end,
            usage_quantity=usage_quantity,
            usage_metric=usage_metric,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            price_id=price_id,
            metadata=metadata or {},
        )

        self.db.add(item)

        # Update invoice totals
        invoice_result = await self.db.execute(
            select(BillingInvoice).where(
                BillingInvoice.tenant_id == self.tenant_id,
                BillingInvoice.id == invoice_id,
            )
        )
        invoice = invoice_result.scalar_one_or_none()
        if invoice:
            invoice.subtotal += amount
            invoice.total = invoice.subtotal + invoice.tax
            invoice.amount_due = invoice.total - invoice.amount_paid

        await self.db.flush()
        logger.debug(f"Added invoice item: {description} = {amount} cents")
        return item

    async def get_invoice(
        self,
        invoice_id: str,
        include_items: bool = True,
        include_charges: bool = False,
    ) -> BillingInvoice | None:
        """Get an invoice by ID.

        Args:
            invoice_id: Invoice ID
            include_items: Include line items in result
            include_charges: Include charges in result

        Returns:
            Invoice or None if not found
        """
        if not self.tenant_id:
            return None

        query = select(BillingInvoice).where(
            BillingInvoice.tenant_id == self.tenant_id,
            BillingInvoice.id == invoice_id,
        )

        if include_items:
            query = query.options(selectinload(BillingInvoice.items))
        if include_charges:
            query = query.options(selectinload(BillingInvoice.charges))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_invoice_by_number(self, invoice_number: str) -> BillingInvoice | None:
        """Get an invoice by invoice number.

        Args:
            invoice_number: Invoice number (e.g., INV-ABC123-20260423-XYZ789)

        Returns:
            Invoice or None if not found
        """
        if not self.tenant_id:
            return None

        result = await self.db.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.items))
            .where(
                BillingInvoice.tenant_id == self.tenant_id,
                BillingInvoice.invoice_number == invoice_number,
            )
        )
        return result.scalar_one_or_none()

    async def list_invoices(
        self,
        customer_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        period_start_after: datetime | None = None,
        period_end_before: datetime | None = None,
    ) -> list[BillingInvoice]:
        """List invoices with optional filters.

        Args:
            customer_id: Filter by customer
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset
            period_start_after: Filter period start after date
            period_end_before: Filter period end before date

        Returns:
            List of invoices
        """
        if not self.tenant_id:
            return []

        query = select(BillingInvoice).where(
            BillingInvoice.tenant_id == self.tenant_id
        )

        if customer_id:
            query = query.where(BillingInvoice.customer_id == customer_id)
        if status:
            query = query.where(BillingInvoice.status == status)
        if period_start_after:
            query = query.where(BillingInvoice.period_start >= period_start_after)
        if period_end_before:
            query = query.where(BillingInvoice.period_end <= period_end_before)

        query = query.order_by(BillingInvoice.created_at.desc())
        query = query.limit(limit).offset(offset)
        query = query.options(selectinload(BillingInvoice.items))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def finalize_invoice(self, invoice_id: str) -> BillingInvoice:
        """Finalize a draft invoice (make it open/payable).

        Args:
            invoice_id: Invoice ID to finalize

        Returns:
            Updated invoice

        Raises:
            ValueError: If invoice not found or not in draft status
        """
        if not self.tenant_id:
            raise ValueError("tenant_id is required")

        invoice = await self.get_invoice(invoice_id, include_items=True)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(f"Cannot finalize invoice with status: {invoice.status}")

        # Recalculate totals from items
        total = sum(item.amount for item in invoice.items)
        invoice.subtotal = total
        invoice.total = total + invoice.tax
        invoice.amount_due = invoice.total - invoice.amount_paid
        invoice.balance = invoice.amount_due
        invoice.status = InvoiceStatus.OPEN

        await self.db.flush()
        logger.info(f"Finalized invoice {invoice.invoice_number}")
        return invoice

    async def mark_invoice_paid(
        self,
        invoice_id: str,
        amount_paid: int | None = None,
    ) -> BillingInvoice:
        """Mark an invoice as paid.

        Args:
            invoice_id: Invoice ID
            amount_paid: Amount paid (defaults to amount_due)

        Returns:
            Updated invoice
        """
        if not self.tenant_id:
            raise ValueError("tenant_id is required")

        invoice = await self.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        if amount_paid is None:
            amount_paid = invoice.amount_due

        invoice.amount_paid += amount_paid
        invoice.amount_due = max(0, invoice.total - invoice.amount_paid)
        invoice.balance = invoice.amount_due

        if invoice.amount_due == 0:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.now(UTC)

        await self.db.flush()
        logger.info(f"Marked invoice {invoice.invoice_number} as paid: {amount_paid} cents")
        return invoice

    async def void_invoice(self, invoice_id: str, reason: str | None = None) -> BillingInvoice:
        """Void an invoice.

        Args:
            invoice_id: Invoice ID
            reason: Optional void reason

        Returns:
            Updated invoice
        """
        if not self.tenant_id:
            raise ValueError("tenant_id is required")

        invoice = await self.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("Cannot void a paid invoice")

        invoice.status = InvoiceStatus.VOID
        invoice.voided_at = datetime.now(UTC)

        if reason:
            metadata = invoice.metadata or {}
            metadata["void_reason"] = reason
            invoice.metadata = metadata

        await self.db.flush()
        logger.info(f"Voided invoice {invoice.invoice_number}: {reason}")
        return invoice

    # ====================================================================================
    # Charge Operations
    # ====================================================================================

    async def record_charge(
        self,
        customer_id: str,
        amount: int,
        status: str = ChargeStatus.SUCCEEDED,
        invoice_id: str | None = None,
        stripe_charge_id: str | None = None,
        payment_method_id: str | None = None,
        payment_method_type: str | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
        receipt_url: str | None = None,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> BillingCharge:
        """Record a charge attempt.

        Args:
            customer_id: Customer being charged
            amount: Charge amount in cents
            status: Charge status (succeeded, pending, failed)
            invoice_id: Optional linked invoice
            stripe_charge_id: Stripe charge ID
            payment_method_id: Payment method ID
            payment_method_type: Payment method type (card, bank_transfer, etc.)
            failure_code: Failure code (if failed)
            failure_message: Failure message (if failed)
            receipt_url: Receipt URL
            description: Charge description
            metadata: Additional metadata

        Returns:
            Created charge record
        """
        if not self.tenant_id:
            raise ValueError("tenant_id is required")

        charge = BillingCharge(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            customer_id=customer_id,
            invoice_id=invoice_id,
            stripe_charge_id=stripe_charge_id,
            amount=amount,
            status=status,
            payment_method_id=payment_method_id,
            payment_method_type=payment_method_type,
            failure_code=failure_code,
            failure_message=failure_message,
            receipt_url=receipt_url,
            description=description,
            metadata=metadata or {},
            captured_at=datetime.now(UTC) if status == ChargeStatus.SUCCEEDED else None,
        )

        self.db.add(charge)

        # Update invoice if linked
        if invoice_id and status == ChargeStatus.SUCCEEDED:
            await self.mark_invoice_paid(invoice_id, amount)

        await self.db.flush()
        logger.info(f"Recorded charge: {charge.id} = {amount} cents ({status})")
        return charge

    async def get_charge(self, charge_id: str) -> BillingCharge | None:
        """Get a charge by ID.

        Args:
            charge_id: Charge ID

        Returns:
            Charge or None if not found
        """
        if not self.tenant_id:
            return None

        result = await self.db.execute(
            select(BillingCharge).where(
                BillingCharge.tenant_id == self.tenant_id,
                BillingCharge.id == charge_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_charges(
        self,
        customer_id: str | None = None,
        invoice_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BillingCharge]:
        """List charges with optional filters.

        Args:
            customer_id: Filter by customer
            invoice_id: Filter by invoice
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of charges
        """
        if not self.tenant_id:
            return []

        query = select(BillingCharge).where(BillingCharge.tenant_id == self.tenant_id)

        if customer_id:
            query = query.where(BillingCharge.customer_id == customer_id)
        if invoice_id:
            query = query.where(BillingCharge.invoice_id == invoice_id)
        if status:
            query = query.where(BillingCharge.status == status)

        query = query.order_by(BillingCharge.created_at.desc())
        query = query.limit(limit).offset(offset)
        query = query.options(selectinload(BillingCharge.invoice))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def refund_charge(
        self,
        charge_id: str,
        amount: int | None = None,
        reason: str | None = None,
    ) -> BillingCharge:
        """Record a refund for a charge.

        Args:
            charge_id: Charge to refund
            amount: Refund amount in cents (defaults to full amount)
            reason: Refund reason

        Returns:
            Updated charge
        """
        if not self.tenant_id:
            raise ValueError("tenant_id is required")

        charge = await self.get_charge(charge_id)
        if not charge:
            raise ValueError(f"Charge not found: {charge_id}")

        if amount is None:
            amount = charge.net_amount

        if amount > charge.net_amount:
            raise ValueError(f"Refund amount {amount} exceeds net amount {charge.net_amount}")

        charge.amount_refunded += amount
        charge.refunded_at = datetime.now(UTC)

        if reason:
            metadata = charge.metadata or {}
            metadata["refund_reason"] = reason
            charge.metadata = metadata

        await self.db.flush()
        logger.info(f"Recorded refund: {charge_id} = {amount} cents")
        return charge

    # ====================================================================================
    # Reporting & Aggregation
    # ====================================================================================

    async def get_revenue_summary(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Get revenue summary for a period.

        Args:
            period_start: Period start
            period_end: Period end

        Returns:
            Revenue summary with totals
        """
        if not self.tenant_id:
            return InvoiceService_get_revenue_summaryResult.model_validate({})

        # Invoice totals
        invoice_query = select(
            func.count(BillingInvoice.id).label("count"),
            func.sum(BillingInvoice.total).label("total"),
            func.sum(BillingInvoice.amount_paid).label("paid"),
            func.sum(BillingInvoice.amount_due).label("due"),
        ).where(
            BillingInvoice.tenant_id == self.tenant_id,
            BillingInvoice.period_start >= period_start,
            BillingInvoice.period_end <= period_end,
            BillingInvoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.PAID]),
        )

        invoice_result = await self.db.execute(invoice_query)
        invoice_row = invoice_result.one()

        # Charge totals
        charge_query = select(
            func.count(BillingCharge.id).label("count"),
            func.sum(BillingCharge.amount).label("total"),
            func.sum(BillingCharge.amount_refunded).label("refunded"),
        ).where(
            BillingCharge.tenant_id == self.tenant_id,
            BillingCharge.created_at >= period_start,
            BillingCharge.created_at <= period_end,
            BillingCharge.status == ChargeStatus.SUCCEEDED,
        )

        charge_result = await self.db.execute(charge_query)
        charge_row = charge_result.one()

        return InvoiceService_get_revenue_summaryResult.model_validate({
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "invoices": {
                "count": invoice_row.count or 0,
                "total_cents": invoice_row.total or 0,
                "total_dollars": (invoice_row.total or 0) / 100.0,
                "paid_cents": invoice_row.paid or 0,
                "due_cents": invoice_row.due or 0,
            },
            "charges": {
                "count": charge_row.count or 0,
                "total_cents": charge_row.total or 0,
                "total_dollars": (charge_row.total or 0) / 100.0,
                "refunded_cents": charge_row.refunded or 0,
            },
        })


    async def get_customer_balance(
        self,
        customer_id: str,
    ) -> dict[str, Any]:
        """Get customer balance summary.

        Args:
            customer_id: Customer ID

        Returns:
            Balance summary with open invoices and available credit
        """
        if not self.tenant_id:
            return InvoiceService_get_customer_balanceResult.model_validate({})

        # Open invoices
        open_query = select(
            func.count(BillingInvoice.id).label("count"),
            func.sum(BillingInvoice.amount_due).label("total_due"),
        ).where(
            BillingInvoice.tenant_id == self.tenant_id,
            BillingInvoice.customer_id == customer_id,
            BillingInvoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.DRAFT]),
        )

        open_result = await self.db.execute(open_query)
        open_row = open_result.one()

        # Total paid (all time)
        paid_query = select(
            func.sum(BillingCharge.amount - BillingCharge.amount_refunded).label("total_paid"),
        ).where(
            BillingCharge.tenant_id == self.tenant_id,
            BillingCharge.customer_id == customer_id,
            BillingCharge.status == ChargeStatus.SUCCEEDED,
        )

        paid_result = await self.db.execute(paid_query)
        paid_row = paid_result.one()

        return InvoiceService_get_customer_balanceResult.model_validate({
            "customer_id": customer_id,
            "open_invoices": {
                "count": open_row.count or 0,
                "amount_due_cents": open_row.total_due or 0,
                "amount_due_dollars": (open_row.total_due or 0) / 100.0,
            },
            "lifetime_paid_cents": paid_row.total_paid or 0,
            "lifetime_paid_dollars": (paid_row.total_paid or 0) / 100.0,
        })
