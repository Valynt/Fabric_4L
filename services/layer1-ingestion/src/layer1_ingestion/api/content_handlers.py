"""Content retrieval route handlers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy.orm import Session
from value_fabric.shared.error_handling.exceptions import NotFoundError
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..shared.database import get_db_from_context
from ..shared.models import ExtractedData, RawContent
from .dependencies import get_tenant_id
from .schemas.content_schemas import ExtractedDataResponse, RawContentResponse


class list_contentResult(TypedDictModel):
    items: Any
    limit: Any
    page: Any
    total: Any


async def get_raw_content(
    content_id: UUID,
    include_html: bool = Query(default=True),
    include_screenshot: bool = Query(default=False),
    include_har: bool = Query(default=False),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context),
):
    """Retrieve raw content by ID."""
    content = (
        db.query(RawContent)
        .filter(RawContent.id == content_id, RawContent.tenant_id == org_id)
        .first()
    )

    if not content:
        raise NotFoundError(message="Content not found")

    storage = {}
    if include_html:
        storage["html"] = content.storage_html_path
    if include_screenshot:
        storage["screenshot"] = content.storage_screenshot_path
    if include_har:
        storage["har"] = content.storage_har_path

    return RawContentResponse(
        id=content.id,
        job_id=content.job_id,
        source_url=content.source_url,
        source_final_url=content.source_final_url,
        source_domain=content.source_domain,
        source_http_status=content.source_http_status,
        storage=storage,
        metadata={
            "title": content.meta_title,
            "description": content.meta_description,
            "language": content.meta_language,
            "og_tags": content.meta_og_tags,
            "structured_data": content.meta_structured_data,
        },
        capture={
            "method": content.capture_method,
            "browser_version": content.capture_browser_version,
            "javascript_executed": content.capture_javascript_executed,
            "wait_time_ms": content.capture_wait_time_ms,
        },
        content_hash=content.content_hash,
        is_duplicate=content.is_duplicate,
        processing_status=content.processing_status,
        created_at=content.created_at,
    )


async def get_extracted_data(
    extracted_data_id: UUID,
    format: str = Query(default="json", pattern="^(json|markdown|flattened)$"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context),
):
    """Retrieve extracted data by ID."""
    data = (
        db.query(ExtractedData)
        .filter(
            ExtractedData.id == extracted_data_id, ExtractedData.tenant_id == org_id
        )
        .first()
    )

    if not data:
        raise NotFoundError(message="Extracted data not found")

    return ExtractedDataResponse(
        id=data.id,
        job_id=data.job_id,
        raw_content_id=data.raw_content_id,
        extraction_method=data.extraction_method,
        extraction_confidence_score=(
            float(data.extraction_confidence_score)
            if data.extraction_confidence_score
            else 0.0
        ),
        data=data.data,
        validation={
            "schema_valid": data.validation_schema_valid,
            "errors": data.validation_errors,
            "data_quality_score": (
                float(data.validation_data_quality_score)
                if data.validation_data_quality_score
                else 0.0
            ),
        },
        post_processing={
            "pii_redaction_applied": data.post_pii_redaction_applied,
            "redacted_fields": data.post_redacted_fields,
            "normalized_fields": data.post_normalized_fields,
            "enriched_fields": data.post_enriched_fields,
        },
        created_at=data.created_at,
    )


async def list_content(
    job_id: UUID | None = Query(None),
    domain: str | None = Query(None),
    processing_status: str | None = Query(None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context),
):
    """List raw content with filtering."""
    query = db.query(RawContent).filter(RawContent.tenant_id == org_id)

    if job_id:
        query = query.filter(RawContent.job_id == job_id)

    if domain:
        query = query.filter(RawContent.source_domain == domain)

    if processing_status:
        query = query.filter(RawContent.processing_status == processing_status)

    total = query.count()
    offset = (page - 1) * limit
    items = (
        query.order_by(RawContent.created_at.desc()).offset(offset).limit(limit).all()
    )

    return list_contentResult.model_validate(
        {
            "items": [
                {
                    "id": str(item.id),
                    "job_id": str(item.job_id),
                    "source_url": item.source_url,
                    "source_domain": item.source_domain,
                    "processing_status": item.processing_status,
                    "created_at": item.created_at.isoformat(),
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }
    )
