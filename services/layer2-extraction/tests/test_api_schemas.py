from __future__ import annotations

from datetime import datetime

from layer2_extraction.api.main import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CONFIDENCE_THRESHOLD,
    EntityListResponse,
    ExtractAndIngestResponse,
    ExtractionStatusResponse,
    ExtractRequest,
    ExtractResponse,
    ProvenanceResponse,
    RelationshipsResponse,
)


def test_extract_request_default_config_matches_entrypoint_constants() -> None:
    request = ExtractRequest(
        content_id="content-1",
        source_url="https://example.com",
        markdown_content="# Demo",
    )

    assert request.extraction_config == {
        "entity_types": ["Capability", "UseCase", "Persona", "ValueDriver"],
        "confidence_threshold": DEFAULT_CONFIDENCE_THRESHOLD,
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
    }


def test_response_models_preserve_public_payload_shape() -> None:
    assert ExtractResponse(
        extraction_job_id="job-1",
        status="queued",
        message="Extraction job started",
    ).model_dump() == {
        "extraction_job_id": "job-1",
        "status": "queued",
        "message": "Extraction job started",
    }

    assert ExtractAndIngestResponse(
        job_id="job-2",
        overall_status="pending",
        extraction_status="pending",
        ingestion_status="pending",
        message="Extraction and ingestion job started",
    ).model_dump() == {
        "job_id": "job-2",
        "overall_status": "pending",
        "extraction_status": "pending",
        "ingestion_status": "pending",
        "message": "Extraction and ingestion job started",
    }


def test_extraction_status_response_defaults_and_datetimes() -> None:
    started = datetime(2026, 1, 1, 0, 0, 0)
    response = ExtractionStatusResponse(
        job_id="job-1",
        overall_status="partial",
        extraction_status="completed",
        ingestion_status="queued",
        entities_extracted=3,
        relationships_extracted=2,
        completed_at=None,
        started_at=started,
    )

    assert response.retry_count == 0
    assert response.last_error is None
    assert response.next_retry_at is None
    assert response.started_at is started


def test_list_relationship_and_provenance_response_shapes() -> None:
    assert EntityListResponse(entity_type="Capability", entities=[{"id": "c1"}], total=1).model_dump() == {
        "entity_type": "Capability",
        "entities": [{"id": "c1"}],
        "total": 1,
    }
    assert RelationshipsResponse(entity_id="c1", incoming=[], outgoing=[{"id": "r1"}]).model_dump() == {
        "entity_id": "c1",
        "incoming": [],
        "outgoing": [{"id": "r1"}],
    }
    assert ProvenanceResponse(
        activity_id="job-1",
        source={"url": "https://example.com"},
        extraction={"model": "model-a"},
        steps=[],
        output={"entities": []},
    ).model_dump() == {
        "activity_id": "job-1",
        "source": {"url": "https://example.com"},
        "extraction": {"model": "model-a"},
        "steps": [],
        "output": {"entities": []},
    }
