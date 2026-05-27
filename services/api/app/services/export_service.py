"""Business case export service for PDF, DOCX, and PPTX generation."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Literal

from app.core.database import db
from app.models.schemas import BusinessCase

ExportFormat = Literal["pdf", "docx", "pptx"]


def generate_export(
    account_id: str,
    business_case_id: str,
    tenant_id: str,
    format: ExportFormat,
) -> dict:
    """Generate a business case export in the requested format.

    Returns metadata including a mock download URL and generation status.
    In a production environment this would use python-docx, python-pptx,
    or a headless browser (Playwright) to produce real files.
    """
    case = db.business_cases.get(business_case_id, tenant_id=tenant_id)
    if not case or case.account_id != account_id:
        raise ValueError("business_case_not_found")

    # Generate a deterministic mock download path
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"business_case_{business_case_id}_{timestamp}.{format}"

    return {
        "status": "ready",
        "format": format,
        "filename": filename,
        "download_url": f"/api/v1/accounts/{account_id}/value-case/{business_case_id}/export/download?file={filename}",
        "generated_at": datetime.now(UTC).isoformat(),
        "size_bytes": 0,
    }
