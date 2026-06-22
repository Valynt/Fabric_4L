from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from layer2_extraction.api.retry_queue import (
    ExtractionArtifactsPayload,
    deserialize_artifacts,
    next_retry_at,
    retry_delay_seconds,
    serialize_artifacts,
)
from layer2_extraction.models import ExtractionResult


@pytest.mark.parametrize(
    ("retry_count", "expected_delay"),
    [
        (0, 60),
        (1, 60),
        (2, 120),
        (3, 240),
    ],
)
def test_retry_delay_seconds_preserves_exponential_backoff_floor(
    retry_count: int,
    expected_delay: int,
) -> None:
    assert retry_delay_seconds(retry_base_seconds=60, retry_count=retry_count) == expected_delay


def test_next_retry_at_uses_utc_timestamp_math() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    assert next_retry_at(now=now, retry_base_seconds=60, retry_count=2) == now + timedelta(seconds=120)


def test_next_retry_at_preserves_naive_clock_behavior_for_test_doubles() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0)

    retry_at = next_retry_at(now=now, retry_base_seconds=60, retry_count=1)

    assert retry_at == now + timedelta(seconds=60)
    assert retry_at.tzinfo is None


def test_artifact_serialization_roundtrip_preserves_prompt_metadata() -> None:
    original = ExtractionArtifactsPayload(
        result=ExtractionResult(
            job_id="job-1",
            source_url="https://example.com",
            tenant_id="tenant-a",
            schema_version="schema-v1",
            prompt_version="prompt-v1",
            prompt_template_version="entity_v1+relationship_v1",
            prompt_template_hash="sha256:abc",
            model_version="model-v1",
        ),
        relationships=[],
    )

    result_json, relationships_json = serialize_artifacts(original)
    restored = deserialize_artifacts(result_json, relationships_json)

    assert restored.result.prompt_template_version == original.result.prompt_template_version
    assert restored.result.prompt_template_hash == original.result.prompt_template_hash
    assert restored.relationships == []
