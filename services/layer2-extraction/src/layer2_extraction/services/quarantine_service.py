"""Quarantine service for Layer 2 extraction validation failures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from value_fabric.shared.audit import AuditAction, emit_audit_event

from layer2_extraction.integration.quarantine_store import (
    QuarantineRecord,
    QuarantineStore,
    build_quarantine_store,
)

logger = structlog.get_logger(__name__)


async def quarantine_validation_failure(
    *,
    tenant_id: str,
    job_id: str,
    source_url: str,
    source_hash: str,
    payload: str,
    errors: list[str],
    model_version: str,
    schema_version: str,
    prompt_template_version: str,
    prompt_template_hash: str | None = None,
    reason: str = "validation_error",
    quarantine_store: QuarantineStore | None = None,
    set_pipeline_job_fn: Callable[..., Awaitable[None]] | None = None,
) -> QuarantineRecord:
    """Quarantine a validation failure with explicit version metadata.

    Args:
        tenant_id: Required tenant identifier (no fallbacks)
        job_id: Extraction job identifier
        source_url: Source document URL
        source_hash: Content hash for provenance
        payload: Failed payload
        errors: Validation error messages
        model_version: LLM model version (required, no fallback)
        schema_version: Schema version (required, no fallback)
        prompt_template_version: Prompt template version identifier
        prompt_template_hash: Optional SHA256 hash of the prompt template
        reason: Quarantine reason
        quarantine_store: Optional quarantine store instance (falls back to default)
        set_pipeline_job_fn: Optional callback to update pipeline job state
    """
    if not tenant_id:
        raise ValueError("tenant_id is required for quarantine records")
    if not model_version:
        raise ValueError("model_version is required for quarantine records")
    if not schema_version:
        raise ValueError("schema_version is required for quarantine records")

    store = (
        quarantine_store if quarantine_store is not None else build_quarantine_store()
    )

    record = QuarantineRecord(
        quarantine_id=str(uuid4()),
        job_id=job_id,
        tenant_id=tenant_id,
        source_url=source_url,
        source_hash=source_hash,
        model_version=model_version,
        schema_version=schema_version,
        prompt_template_version=prompt_template_version,
        prompt_template_hash=prompt_template_hash,
        payload_json=payload,
        validation_errors=errors,
        reason=reason,
    )
    await store.put(record)

    if set_pipeline_job_fn is not None:
        await set_pipeline_job_fn(
            job_id,
            extraction_status="quarantined",
            last_error="; ".join(errors),
            completed_at=datetime.now(UTC),
        )

    try:
        emit_audit_event(
            AuditAction.EXTRACTION_QUARANTINED,
            tenant_id=UUID(tenant_id) if tenant_id else None,
            resource_type="ExtractionJob",
            resource_id=job_id,
            outcome="failure",
            details={
                "reason": reason,
                "source_url": source_url,
                "source_hash": source_hash,
                "model_version": model_version,
                "schema_version": schema_version,
                "prompt_template_version": prompt_template_version,
                "validation_errors": errors,
            },
        )
    except Exception:
        # Audit emission must never break the quarantine flow
        pass

    return record
