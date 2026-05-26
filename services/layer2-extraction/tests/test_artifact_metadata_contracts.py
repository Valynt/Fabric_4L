"""Contract tests for persisted Layer 2 artifact metadata."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from layer2_extraction.integration.quarantine_store import QuarantineRecord
from layer2_extraction.models.ontology import Capability, ExtractionResult
from layer2_extraction.validation.artifact_validator import ArtifactValidationError, validate_artifact_for_persistence


def _persisted_entity_payload(entity: Capability, result: ExtractionResult, *, source_hash: str) -> dict[str, object]:
    """Shape the minimum persisted payload expected by downstream consumers."""
    return {
        "stable_id": entity.deterministic_id,
        "tenant_id": entity.tenant_id,
        "source_id": result.source_content_id,
        "source_hash": source_hash,
        "schema_version": entity.schema_version,
        "prompt_template_version": entity.prompt_version_id,
        "confidence": entity.confidence,
        "provenance": {
            "source_refs": entity.source_refs,
            "extraction_job_id": entity.extraction_job_id,
        },
        "timestamps": {
            "extracted_at": entity.extracted_at,
            "processed_at": result.processed_at,
        },
    }


def test_persisted_extraction_artifact_includes_required_metadata_contract_fields() -> None:
    entity = Capability(
        name="Revenue Leak Detection",
        description="Detect revenue leakage and suggest corrective actions.",
        tenant_id="tenant-42",
        extraction_job_id="job-1",
        deterministic_id="det-abc123",
        schema_version="2.1.0",
        prompt_version_id="prompt-template-v9",
        model_version="gpt-4.1",
        confidence=0.94,
        source_refs=["https://example.com/source"],
    )
    result = ExtractionResult(
        job_id="job-1",
        source_url="https://example.com/source",
        source_content_id="source-777",
        tenant_id="tenant-42",
        schema_version="2.1.0",
        prompt_version="prompt-template-v9",
        model_version="gpt-4.1",
        capabilities=[entity],
    )

    validate_artifact_for_persistence(entity, "entity")
    payload = _persisted_entity_payload(entity, result, source_hash="sha256:abc")

    assert payload["stable_id"] == "det-abc123"
    assert payload["tenant_id"] == "tenant-42"
    assert payload["source_id"] == "source-777"
    assert payload["source_hash"] == "sha256:abc"
    assert payload["schema_version"] == "2.1.0"
    assert payload["prompt_template_version"] == "prompt-template-v9"
    assert payload["confidence"] == pytest.approx(0.94)
    assert payload["provenance"]["extraction_job_id"] == "job-1"
    assert payload["timestamps"]["extracted_at"] is not None
    assert payload["timestamps"]["processed_at"] is not None


@pytest.mark.asyncio
async def test_validation_failure_paths_quarantine_with_traceable_metadata() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ArtifactValidationError):
        validate_artifact_for_persistence(
            Capability(
                name="Broken metadata entity",
                description="This intentionally misses required metadata for quarantine testing.",
                tenant_id="",
                extraction_job_id="job-q-1",
                deterministic_id="",
                schema_version="2.1.0",
                prompt_version_id="prompt-template-v9",
                model_version="gpt-4.1",
            ),
            "entity",
        )

    quarantine_record = QuarantineRecord(
        quarantine_id="q-100",
        job_id="job-q-1",
        tenant_id="tenant-42",
        source_url="https://example.com/source",
        source_hash="sha256:quarantine",
        model_version="gpt-4.1",
        schema_version="2.1.0",
        payload_json='{"artifact":"invalid"}',
        validation_errors=["tenant_id missing", "deterministic_id missing"],
        created_at=now,
    )

    assert quarantine_record.tenant_id == "tenant-42"
    assert quarantine_record.source_hash == "sha256:quarantine"
    assert quarantine_record.schema_version == "2.1.0"
    assert quarantine_record.validation_errors
    assert quarantine_record.created_at == now


def test_retry_replay_keeps_stable_id_and_contract_metadata_intact() -> None:
    first = Capability(
        name="Replay-safe entity",
        description="Ensure deterministic identity remains stable across retry/replay.",
        tenant_id="tenant-42",
        extraction_job_id="job-replay",
        deterministic_id="det-replay-001",
        schema_version="2.1.0",
        prompt_version_id="prompt-template-v9",
        model_version="gpt-4.1",
        confidence=0.86,
    )
    replay = first.model_copy(deep=True)
    replay.extracted_at = datetime.now(UTC)

    first_payload = _persisted_entity_payload(
        first,
        ExtractionResult(
            job_id="job-replay",
            source_url="https://example.com/source",
            source_content_id="source-replay",
            tenant_id="tenant-42",
            schema_version="2.1.0",
            prompt_version="prompt-template-v9",
            model_version="gpt-4.1",
        ),
        source_hash="sha256:replay",
    )
    replay_payload = _persisted_entity_payload(
        replay,
        ExtractionResult(
            job_id="job-replay",
            source_url="https://example.com/source",
            source_content_id="source-replay",
            tenant_id="tenant-42",
            schema_version="2.1.0",
            prompt_version="prompt-template-v9",
            model_version="gpt-4.1",
        ),
        source_hash="sha256:replay",
    )

    assert replay_payload["stable_id"] == first_payload["stable_id"]
    assert replay_payload["tenant_id"] == first_payload["tenant_id"]
    assert replay_payload["source_id"] == first_payload["source_id"]
    assert replay_payload["source_hash"] == first_payload["source_hash"]
    assert replay_payload["schema_version"] == first_payload["schema_version"]
    assert replay_payload["prompt_template_version"] == first_payload["prompt_template_version"]
    assert replay_payload["timestamps"]["extracted_at"] >= first_payload["timestamps"]["extracted_at"]
