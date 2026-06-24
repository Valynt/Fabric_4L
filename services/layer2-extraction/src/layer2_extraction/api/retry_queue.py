"""Retry queue helpers for Layer 2 extract-and-ingest pipelines."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from layer2_extraction.models import ExtractionResult, Relationship


@dataclass(frozen=True)
class ExtractionArtifactsPayload:
    result: ExtractionResult
    relationships: list[Relationship]


@dataclass(frozen=True)
class PendingRetryState:
    retry_count: int
    last_error: str
    next_retry_at: datetime


class PendingRecordLike(Protocol):
    job_id: str
    retry_count: int
    last_error: str | None
    next_retry_at: datetime | None


def retry_delay_seconds(*, retry_base_seconds: int, retry_count: int) -> int:
    return int(retry_base_seconds * max(1, 2 ** max(retry_count - 1, 0)))


def next_retry_at(
    *,
    now: datetime,
    retry_base_seconds: int,
    retry_count: int,
    fromtimestamp: Callable[..., datetime] | None = None,
) -> datetime:
    delay_seconds = retry_delay_seconds(
        retry_base_seconds=retry_base_seconds,
        retry_count=retry_count,
    )
    fromtimestamp_fn = fromtimestamp or datetime.fromtimestamp
    if now.tzinfo is None:
        return fromtimestamp_fn(now.timestamp() + delay_seconds)
    return fromtimestamp_fn(now.timestamp() + delay_seconds, tz=UTC)


def serialize_artifacts(artifacts: ExtractionArtifactsPayload) -> tuple[str, str]:
    result_json = json.dumps(artifacts.result.model_dump(mode="json"))
    relationships_json = json.dumps([r.model_dump(mode="json") for r in artifacts.relationships])
    return result_json, relationships_json


def deserialize_artifacts(result_json: str, relationships_json: str) -> ExtractionArtifactsPayload:
    result = ExtractionResult(**json.loads(result_json))
    relationships = [Relationship(**item) for item in json.loads(relationships_json)]
    return ExtractionArtifactsPayload(result=result, relationships=relationships)


def pipeline_job_kwargs_for_pending_record(
    record: PendingRecordLike,
    *,
    created_at: datetime,
) -> dict[str, object]:
    return {
        "job_id": record.job_id,
        "extraction_status": "completed",
        "ingestion_status": "queued",
        "created_at": created_at.isoformat(),
        "entities_extracted": 0,
        "relationships_extracted": 0,
        "retry_count": record.retry_count,
        "last_error": record.last_error,
        "next_retry_at": record.next_retry_at.isoformat() if record.next_retry_at else None,
        "completed_at": None,
    }


def pending_retry_state(
    *,
    now: datetime,
    current_retry_count: int,
    retry_base_seconds: int,
    last_error: str = "Layer 3 unavailable",
    fromtimestamp: Callable[..., datetime] | None = None,
) -> PendingRetryState:
    retry_count = current_retry_count + 1
    delay_seconds = retry_base_seconds * (2 ** max(current_retry_count, 0))
    fromtimestamp_fn = fromtimestamp or datetime.fromtimestamp
    if now.tzinfo is None:
        retry_at = fromtimestamp_fn(now.timestamp() + delay_seconds)
    else:
        retry_at = fromtimestamp_fn(now.timestamp() + delay_seconds, tz=UTC)
    return PendingRetryState(
        retry_count=retry_count,
        last_error=last_error,
        next_retry_at=retry_at,
    )
