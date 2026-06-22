from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from layer2_extraction.api.pipeline_status import (
    compute_overall_status,
    pipeline_response_payload,
    to_datetime,
)


@pytest.mark.parametrize(
    ("extraction_status", "ingestion_status", "expected"),
    [
        ("pending", "pending", "pending"),
        ("pending", "queued", "running"),
        ("running", "pending", "running"),
        ("running", "running", "running"),
        ("completed", "completed", "completed"),
        ("completed", "skipped", "completed"),
        ("completed", "pending", "partial"),
        ("completed", "queued", "partial"),
        ("completed", "running", "running"),
        ("failed", "pending", "failed"),
        ("failed", "completed", "failed"),
        ("pending", "failed", "failed"),
    ],
)
def test_compute_overall_status_matrix(
    extraction_status: str,
    ingestion_status: str,
    expected: str,
) -> None:
    assert compute_overall_status(extraction_status, ingestion_status) == expected


def test_to_datetime_preserves_none_and_datetime_instances() -> None:
    value = datetime(2026, 1, 1, tzinfo=UTC)

    assert to_datetime(None) is None
    assert to_datetime(value) is value


def test_to_datetime_parses_iso_strings() -> None:
    assert to_datetime("2026-01-01T00:00:00+00:00") == datetime(2026, 1, 1, tzinfo=UTC)


def test_pipeline_response_payload_preserves_status_contract() -> None:
    job = SimpleNamespace(
        job_id="job-1",
        extraction_status="completed",
        ingestion_status="queued",
        entities_extracted=3,
        relationships_extracted=2,
        retry_count=1,
        last_error="Layer 3 unavailable",
        next_retry_at="2026-01-01T00:01:00",
        created_at="2026-01-01T00:00:00",
        completed_at=None,
    )

    payload = pipeline_response_payload(job)

    assert payload == {
        "job_id": "job-1",
        "overall_status": "partial",
        "extraction_status": "completed",
        "ingestion_status": "queued",
        "entities_extracted": 3,
        "relationships_extracted": 2,
        "retry_count": 1,
        "last_error": "Layer 3 unavailable",
        "next_retry_at": datetime(2026, 1, 1, 0, 1, 0),
        "started_at": datetime(2026, 1, 1, 0, 0, 0),
        "completed_at": None,
    }
