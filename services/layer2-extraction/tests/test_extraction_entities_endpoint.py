"""Tests for extraction results endpoint."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from fastapi import HTTPException

from layer2_extraction.api.routes.extraction import (
    ExtractedEntity,
    EntityProvenance,
    EntitySourceSpan,
    ExtractionResultSummary,
    ExtractionResultsResponse,
)
from layer2_extraction.models.version_manifest import VersionManifest


@pytest.fixture
def mock_job():
    """Mock extraction job."""
    job = Mock()
    job.job_id = str(uuid4())
    job.extraction_status = "completed"
    job.source_url = "https://example.com"
    job.trace_id = str(uuid4())
    return job


@pytest.fixture
def mock_artifacts():
    """Mock extraction artifacts."""
    artifacts = Mock()
    result = Mock()
    
    # Mock entities
    entity1 = Mock()
    entity1.id = "entity-1"
    entity1.type = "Capability"
    entity1.name = "Data Integration"
    entity1.confidence = 0.92
    entity1.document_id = "doc-1"
    entity1.start = 100
    entity1.end = 150
    entity1.attributes = {"key": "value"}
    
    entity2 = Mock()
    entity2.id = "entity-2"
    entity2.type = "UseCase"
    entity2.name = "Customer Onboarding"
    entity2.confidence = 0.88
    entity2.document_id = "doc-1"
    entity2.start = 200
    entity2.end = 250
    entity2.attributes = {}
    
    result.get_all_entities = Mock(return_value=[entity1, entity2])
    artifacts.result = result
    return artifacts


@pytest.mark.asyncio
async def test_get_extraction_results_success(mock_job, mock_artifacts):
    """Test successful retrieval of extraction entities."""
    from layer2_extraction.api.routes.extraction import get_extraction_results
    
    # Mock request with governance context
    request = Mock()
    request.state = Mock()
    request.state.governance_context = Mock()
    request.state.governance_context.tenant_id = uuid4()
    
    # Mock job store
    job_store = AsyncMock()
    job_store.get_job = AsyncMock(return_value=mock_job)
    job_store.get_artifacts = AsyncMock(return_value=mock_artifacts)
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("layer2_extraction.api.routes.extraction.build_job_store", Mock(return_value=job_store))
        
        response = await get_extraction_results(mock_job.job_id, request)
        
        assert response.job_id == mock_job.job_id
        assert response.summary.total_entities == 2
        assert len(response.entities) == 2
        assert response.entities[0].entity_id == "entity-1"
        assert response.entities[0].type == "Capability"
        assert response.entities[0].name == "Data Integration"
        assert response.entities[0].confidence == 0.92
        assert response.entities[0].source_span is not None
        assert response.entities[0].provenance is not None
        assert response.entities[0].provenance.extraction_job_id == mock_job.job_id
        job_store.get_job.assert_awaited_once_with(mock_job.job_id, tenant_id=request.state.governance_context.tenant_id)
        job_store.get_artifacts.assert_awaited_once_with(mock_job.job_id, tenant_id=request.state.governance_context.tenant_id)


@pytest.mark.asyncio
async def test_get_extraction_results_empty_result(mock_job):
    """Test retrieval when no entities are extracted."""
    from layer2_extraction.api.routes.extraction import get_extraction_results
    
    # Mock request with governance context
    request = Mock()
    request.state = Mock()
    request.state.governance_context = Mock()
    request.state.governance_context.tenant_id = uuid4()
    
    # Mock job store with empty result
    job_store = AsyncMock()
    job_store.get_job = AsyncMock(return_value=mock_job)
    
    artifacts = Mock()
    result = Mock()
    result.get_all_entities = Mock(return_value=[])
    artifacts.result = result
    job_store.get_artifacts = AsyncMock(return_value=artifacts)
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("layer2_extraction.api.routes.extraction.build_job_store", Mock(return_value=job_store))
        
        response = await get_extraction_results(mock_job.job_id, request)
        
        assert response.job_id == mock_job.job_id
        assert response.summary.total_entities == 0
        assert len(response.entities) == 0


@pytest.mark.asyncio
async def test_get_extraction_results_incomplete_job(mock_job):
    """Test retrieval when extraction is not complete."""
    from layer2_extraction.api.routes.extraction import get_extraction_results
    
    # Mock request with governance context
    request = Mock()
    request.state = Mock()
    request.state.governance_context = Mock()
    request.state.governance_context.tenant_id = uuid4()
    
    # Set job status to incomplete
    mock_job.extraction_status = "processing"
    
    # Mock job store
    job_store = AsyncMock()
    job_store.get_job = AsyncMock(return_value=mock_job)
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("layer2_extraction.api.routes.extraction.build_job_store", Mock(return_value=job_store))
        
        with pytest.raises(HTTPException) as exc_info:
            await get_extraction_results(mock_job.job_id, request)
        
        assert exc_info.value.status_code == 409
        assert "not complete" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_extraction_results_missing_job():
    """Test retrieval when job does not exist."""
    from layer2_extraction.api.routes.extraction import get_extraction_results
    
    # Mock request with governance context
    request = Mock()
    request.state = Mock()
    request.state.governance_context = Mock()
    request.state.governance_context.tenant_id = uuid4()
    
    job_id = str(uuid4())
    
    # Mock job store that raises KeyError
    job_store = AsyncMock()
    job_store.get_job = AsyncMock(side_effect=KeyError(job_id))
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("layer2_extraction.api.routes.extraction.build_job_store", Mock(return_value=job_store))
        
        with pytest.raises(HTTPException) as exc_info:
            await get_extraction_results(job_id, request)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_extraction_results_cross_tenant_access_denied(mock_job):
    """Test that cross-tenant access is denied."""
    from layer2_extraction.api.routes.extraction import get_extraction_results
    
    # Mock request with governance context
    request = Mock()
    request.state = Mock()
    request.state.governance_context = Mock()
    tenant_id = uuid4()
    request.state.governance_context.tenant_id = tenant_id
    
    # Set job tenant_id to different tenant
    mock_job.tenant_id = uuid4()
    
    # Mock job store
    job_store = AsyncMock()
    job_store.get_job = AsyncMock(return_value=mock_job)
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("layer2_extraction.api.routes.extraction.build_job_store", Mock(return_value=job_store))
        
        with pytest.raises(HTTPException) as exc_info:
            await get_extraction_results(mock_job.job_id, request)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail
        job_store.get_job.assert_awaited_once_with(mock_job.job_id, tenant_id=tenant_id)


@pytest.mark.asyncio
async def test_get_extraction_results_no_artifacts(mock_job):
    """Test retrieval when no artifacts exist."""
    from layer2_extraction.api.routes.extraction import get_extraction_results
    
    # Mock request with governance context
    request = Mock()
    request.state = Mock()
    request.state.governance_context = Mock()
    request.state.governance_context.tenant_id = uuid4()
    
    # Mock job store with no artifacts
    job_store = AsyncMock()
    job_store.get_job = AsyncMock(return_value=mock_job)
    job_store.get_artifacts = AsyncMock(return_value=None)
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("layer2_extraction.api.routes.extraction.build_job_store", Mock(return_value=job_store))
        
        with pytest.raises(HTTPException) as exc_info:
            await get_extraction_results(mock_job.job_id, request)
        
        assert exc_info.value.status_code == 404
        assert "No extraction artifacts found" in exc_info.value.detail


def test_extracted_entity_validation():
    """Test that ExtractedEntity model validates correctly."""
    entity = ExtractedEntity(
        entity_id="entity-1",
        type="Capability",
        name="Data Integration",
        confidence=0.92,
        source_span=EntitySourceSpan(document_id="doc-1", start=100, end=150),
        provenance=EntityProvenance(
            extraction_job_id="job-1",
            source_url="https://example.com",
            trace_id="trace-1",
            version_manifest=VersionManifest(
                prompt_version="p1", schema_version="s1", model_version="m1", extraction_version="e1", value_pack_version="vp1"
            ),
        ),
        attributes={"key": "value"}
    )
    
    assert entity.entity_id == "entity-1"
    assert entity.type == "Capability"
    assert entity.name == "Data Integration"
    assert entity.confidence == 0.92
    assert entity.source_span.document_id == "doc-1"
    assert entity.provenance.extraction_job_id == "job-1"


def test_entity_provenance_contract_metadata_shape():
    provenance = EntityProvenance(
        extraction_job_id="job-2",
        source_url="https://example.com",
        trace_id="trace-2",
        version_manifest=VersionManifest(
            prompt_version="p2", schema_version="s2", model_version="m2", extraction_version="e2", value_pack_version="vp2"
        ),
    )
    assert provenance.version_manifest is not None
    assert provenance.version_manifest.model_dump().keys() == {
        "prompt_version", "schema_version", "model_version", "extraction_version", "value_pack_version"
    }


def test_extracted_entity_confidence_validation():
    """Test that confidence is validated to be between 0 and 1."""
    with pytest.raises(ValueError):
        ExtractedEntity(
            entity_id="entity-1",
            type="Capability",
            name="Data Integration",
            confidence=1.5,  # Invalid: > 1.0
        )
    
    with pytest.raises(ValueError):
        ExtractedEntity(
            entity_id="entity-1",
            type="Capability",
            name="Data Integration",
            confidence=-0.1,  # Invalid: < 0.0
        )


@pytest.mark.asyncio
async def test_get_extraction_results_summary_mode(mock_job, mock_artifacts):
    from layer2_extraction.api.routes.extraction import get_extraction_results

    request = Mock()
    request.state = Mock()
    request.state.governance_context = Mock()
    request.state.governance_context.tenant_id = uuid4()

    job_store = AsyncMock()
    job_store.get_job = AsyncMock(return_value=mock_job)
    job_store.get_artifacts = AsyncMock(return_value=mock_artifacts)

    with pytest.MonkeyPatch().context() as m:
        m.setattr("layer2_extraction.api.routes.extraction.build_job_store", Mock(return_value=job_store))
        response = await get_extraction_results(mock_job.job_id, request, mode='summary')
        assert response.summary.mode == 'summary'
        assert response.entities == []
