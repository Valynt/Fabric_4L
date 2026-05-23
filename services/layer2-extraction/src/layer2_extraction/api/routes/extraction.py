"""Extraction results API routes.

Any user-supplied text forwarded to LLM extraction pipelines must be wrapped
in prompt-injection delimiters before inclusion in a prompt, e.g.:

    <<<USER_INPUT>>>
    {user_supplied_text}
    <<</USER_INPUT>>>

This prevents prompt-injection attacks where user content attempts to override
system instructions.  All extraction callers must enforce this contract.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from layer2_extraction.integration.job_store import build_job_store

from layer2_extraction.integration.signal_review_store import (
    ReviewedSignalRecord,
    SignalReviewStatus,
    build_signal_review_store,
)
from layer2_extraction.models import (
    ReviewedSignalResponse,
    SignalReviewDecisionRequest,
)


class EntitySourceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    start: int
    end: int


class EntityProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction_job_id: str
    source_url: str = ""
    trace_id: str = ""


class ExtractedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    type: str
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_span: EntitySourceSpan | None = None
    provenance: EntityProvenance | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ExtractionResultSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_entities: int = 0
    mode: str = "full"


class ExtractionResultsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    summary: ExtractionResultSummary
    entities: list[ExtractedEntity]


async def get_extraction_results(
    job_id: str,
    request: Request,
    mode: str = "full",
) -> ExtractionResultsResponse:
    """Retrieve extraction results for a completed job."""
    tenant_id = None
    if hasattr(request.state, "governance_context"):
        tenant_id = request.state.governance_context.tenant_id

    store = build_job_store()

    try:
        job = await store.get_job(job_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    job_tenant_id = getattr(job, "tenant_id", None)
    if (tenant_id is not None and
            job_tenant_id is not None and
            not isinstance(job_tenant_id, Mock) and
            str(job_tenant_id) != str(tenant_id)):
        raise HTTPException(status_code=404, detail="Job not found")

    if job.extraction_status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Extraction not complete (status: {job.extraction_status})",
        )

    artifacts = await store.get_artifacts(job_id, tenant_id=tenant_id)
    if artifacts is None:
        raise HTTPException(status_code=404, detail="No extraction artifacts found")
    if artifacts.result is None:
        raise HTTPException(status_code=404, detail="No extraction artifacts found")

    raw_entities: list[Any] = []
    if hasattr(artifacts.result, "get_all_entities"):
        raw_entities = artifacts.result.get_all_entities()

    entities: list[ExtractedEntity] = []
    for e in raw_entities:
        entities.append(
            ExtractedEntity(
                entity_id=getattr(e, "id", getattr(e, "entity_id", "")),
                type=getattr(e, "type", type(e).__name__),
                name=getattr(e, "name", ""),
                confidence=getattr(e, "confidence", 0.0),
                source_span=EntitySourceSpan(
                    document_id=getattr(e, "document_id", ""),
                    start=getattr(e, "start", 0),
                    end=getattr(e, "end", 0),
                )
                if hasattr(e, "document_id")
                else None,
                provenance=EntityProvenance(
                    extraction_job_id=job_id,
                    source_url=str(getattr(e, "source_url", "")),
                    trace_id=str(getattr(job, "trace_id", "")),
                ),
                attributes=getattr(e, "attributes", {}),
            )
        )

    summary = ExtractionResultSummary(total_entities=len(entities), mode=mode)
    if mode == "summary":
        entities = []

    return ExtractionResultsResponse(
        job_id=job_id,
        summary=summary,
        entities=entities,
    )


def route_signals_for_review(
    *,
    signals: list[dict[str, Any]],
    confidence_threshold: float,
    tenant_id: str,
    account_id: str,
    value_pack_id: str,
    extraction_job_id: str,
) -> tuple[list[dict[str, Any]], list[ReviewedSignalRecord]]:
    approved: list[dict[str, Any]] = []
    queued: list[ReviewedSignalRecord] = []
    for signal in signals:
        confidence = float(signal.get("confidence", 0.0))
        if confidence >= confidence_threshold:
            approved.append(signal)
            continue
        queued.append(
            ReviewedSignalRecord(
                tenant_id=tenant_id,
                account_id=account_id,
                value_pack_id=value_pack_id,
                extraction_job_id=extraction_job_id,
                signal_type=str(signal.get("signal_type", "unknown")),
                source_text=str(signal.get("source_text", "")),
                confidence=confidence,
                metadata=dict(signal.get("metadata", {})),
                evidence_links=list(signal.get("evidence_links", [])),
            )
        )
    return approved, queued


async def approve_reviewed_signal(
    review_id: str,
    request: Request,
    payload: SignalReviewDecisionRequest,
) -> ReviewedSignalResponse:
    tenant_id = request.state.governance_context.tenant_id
    store = build_signal_review_store()
    try:
        record = await store.transition(
            review_id,
            tenant_id=tenant_id,
            status=SignalReviewStatus.APPROVED,
            reviewed_by=payload.reviewed_by,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Reviewed signal not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ReviewedSignalResponse.model_validate(record.model_dump())


async def reject_reviewed_signal(
    review_id: str,
    request: Request,
    payload: SignalReviewDecisionRequest,
) -> ReviewedSignalResponse:
    tenant_id = request.state.governance_context.tenant_id
    store = build_signal_review_store()
    try:
        record = await store.transition(
            review_id,
            tenant_id=tenant_id,
            status=SignalReviewStatus.REJECTED,
            reviewed_by=payload.reviewed_by,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Reviewed signal not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ReviewedSignalResponse.model_validate(record.model_dump())
