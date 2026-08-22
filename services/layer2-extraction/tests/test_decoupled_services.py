"""Unit and boundary tests for decoupled Layer 2 services."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from layer2_extraction.domain.models import (
    ChallengeEntity,
    ExtractionResult,
    FinancialMetricEntity,
    GoalEntity,
    InitiativeEntity,
    KPIEntity,
    ProvenanceMetadata,
    RelationshipEntity,
    SystemEntity,
)
from layer2_extraction.services.extraction_orchestrator import (
    ExtractionArtifacts,
    ExtractionPipelineOrchestrator,
    build_e2e_local_extraction_artifacts,
    deserialize_artifacts,
    serialize_artifacts,
)
from layer2_extraction.services.ingestion_retry_worker import (
    attempt_ingestion,
    process_pending_ingestions,
    queue_for_retry,
)
from layer2_extraction.services.quarantine_service import (
    quarantine_validation_failure,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quarantine_validation_failure_requires_tenant() -> None:
    """Quarantine service fails closed if tenant_id is missing."""
    mock_store = AsyncMock()
    with pytest.raises(ValueError, match="tenant_id is required"):
        await quarantine_validation_failure(
            tenant_id="",
            job_id="job-1",
            source_url="http://test.org",
            source_hash="hash123",
            payload="test payload",
            errors=["error 1"],
            model_version="gpt-4o",
            schema_version="1.0.0",
            prompt_template_version="v1.0",
            quarantine_store=mock_store,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quarantine_validation_failure_persists_record() -> None:
    """Quarantine service creates and stores record with full metadata."""
    mock_store = AsyncMock()
    set_pipeline_mock = AsyncMock()

    record = await quarantine_validation_failure(
        tenant_id="tenant-123",
        job_id="job-456",
        source_url="http://example.com/doc",
        source_hash="sha256-abc",
        payload="bad content",
        errors=["Schema violation: missing fields"],
        model_version="gpt-4o",
        schema_version="1.0.0",
        prompt_template_version="v1.0",
        prompt_template_hash="tmpl-hash",
        reason="validation_error",
        quarantine_store=mock_store,
        set_pipeline_job_fn=set_pipeline_mock,
    )

    assert record.tenant_id == "tenant-123"
    assert record.job_id == "job-456"
    assert record.model_version == "gpt-4o"
    assert record.schema_version == "1.0.0"
    mock_store.put.assert_awaited_once_with(record)
    set_pipeline_mock.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_for_retry_and_attempt_ingestion_flow() -> None:
    """Ingestion retry worker enqueues on failure and updates status."""
    mock_job_store = AsyncMock()
    mock_pending_store = AsyncMock()
    mock_ws = AsyncMock()
    mock_l3 = AsyncMock()
    mock_l3.ingest_subgraph.side_effect = ConnectionError("Layer 3 unavailable")
    set_pipeline_mock = AsyncMock()

    artifacts = build_e2e_local_extraction_artifacts(
        text="Sample extraction text",
        tenant_id="tenant-1",
        source_url="http://example.com",
        source_hash="hash-1",
        model_version="gpt-4o",
        prompt_template_version="v1",
        extraction_timestamp=datetime.now(UTC),
    )

    result = await attempt_ingestion(
        job_store=mock_job_store,
        pending_ingestion_store=mock_pending_store,
        ws_manager=mock_ws,
        l3_client=mock_l3,
        set_pipeline_job_fn=set_pipeline_mock,
        serialize_artifacts_fn=serialize_artifacts,
        tenant_id="tenant-1",
        job_id="job-retry-1",
        source_url="http://example.com",
        artifacts=artifacts,
        retry_count=0,
        retry_base_seconds=0.1,
    )

    assert result is False
    mock_pending_store.enqueue.assert_awaited_once()


@pytest.mark.unit
def test_artifact_serialization_roundtrip() -> None:
    """Artifacts serialize and deserialize without data loss."""
    artifacts = build_e2e_local_extraction_artifacts(
        text="Serialization test",
        tenant_id="tenant-test",
        source_url="http://test.com",
        source_hash="hash-xyz",
        model_version="gpt-4o",
        prompt_template_version="v1.0",
        extraction_timestamp=datetime.now(UTC),
    )

    serialized = serialize_artifacts(artifacts)
    assert "entities" in serialized
    assert "relationships" in serialized
    assert len(serialized["entities"]) == 6

    deserialized = deserialize_artifacts(serialized)
    assert len(deserialized.entities) == 6
    assert len(deserialized.relationships) == 2
    assert deserialized.quality_score == 0.98
