from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from value_fabric.layer4.services.invoice_service import InvoiceService
from value_fabric.layer4.services.usage_service import UsageService, UsageValidationError


@pytest.mark.asyncio
async def test_usage_service_rejects_cross_customer_summary() -> None:
    db = AsyncMock()
    service = UsageService(db, tenant_id="tenant_a")

    with pytest.raises(UsageValidationError, match="forbidden_customer_scope"):
        await service.get_usage_summary(
            customer_id="user_b",
            metric_name="tokens",
            principal_customer_id="user_a",
            allow_cross_customer=False,
        )


@pytest.mark.asyncio
async def test_invoice_service_rejects_cross_customer_invoice_id_path() -> None:
    db = AsyncMock()
    invoice = MagicMock()
    invoice.customer_id = "user_b"

    result = MagicMock()
    result.scalar_one_or_none.return_value = invoice
    db.execute.return_value = result

    service = InvoiceService(db, tenant_id="tenant_a")

    with pytest.raises(PermissionError, match="forbidden_customer_scope"):
        await service.get_invoice(
            "inv_123",
            principal_customer_id="user_a",
            allow_cross_customer=False,
        )


@pytest.mark.asyncio
async def test_invoice_service_rejects_cross_customer_list_filter() -> None:
    db = AsyncMock()
    service = InvoiceService(db, tenant_id="tenant_a")

    with pytest.raises(PermissionError, match="forbidden_customer_scope"):
        await service.list_invoices(
            customer_id="user_b",
            principal_customer_id="user_a",
            allow_cross_customer=False,
        )
