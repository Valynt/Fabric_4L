"""Pipeline status helpers for Layer 2 extraction jobs."""

from __future__ import annotations

import datetime as _datetime_module
from datetime import datetime
from typing import Protocol


class PipelineJobLike(Protocol):
    job_id: str
    extraction_status: str
    ingestion_status: str
    entities_extracted: int
    relationships_extracted: int
    retry_count: int
    last_error: str | None
    next_retry_at: datetime | str | None
    created_at: datetime | str | None
    completed_at: datetime | str | None


def compute_overall_status(extraction_status: str, ingestion_status: str) -> str:
    if extraction_status == "failed" or ingestion_status == "failed":
        return "failed"
    if extraction_status == "pending" and ingestion_status == "pending":
        return "pending"
    if extraction_status in {"pending", "running"}:
        return "running"
    if extraction_status == "completed" and ingestion_status in {"pending", "queued"}:
        return "partial"
    if extraction_status == "completed" and ingestion_status == "running":
        return "running"
    if extraction_status == "completed" and ingestion_status in {"completed", "skipped"}:
        return "completed"
    return "pending"


def to_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, _datetime_module.datetime):
        return value
    return datetime.fromisoformat(value)


def pipeline_response_payload(job: PipelineJobLike) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "overall_status": compute_overall_status(job.extraction_status, job.ingestion_status),
        "extraction_status": job.extraction_status,
        "ingestion_status": job.ingestion_status,
        "entities_extracted": job.entities_extracted,
        "relationships_extracted": job.relationships_extracted,
        "retry_count": job.retry_count,
        "last_error": job.last_error,
        "next_retry_at": to_datetime(job.next_retry_at),
        "started_at": to_datetime(job.created_at),
        "completed_at": to_datetime(job.completed_at),
    }
