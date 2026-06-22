"""Retry queue helpers for Layer 2 extract-and-ingest pipelines."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from layer2_extraction.models import ExtractionResult, Relationship


@dataclass(frozen=True)
class ExtractionArtifactsPayload:
    result: ExtractionResult
    relationships: list[Relationship]


def retry_delay_seconds(*, retry_base_seconds: int, retry_count: int) -> int:
    return retry_base_seconds * max(1, 2 ** max(retry_count - 1, 0))


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
