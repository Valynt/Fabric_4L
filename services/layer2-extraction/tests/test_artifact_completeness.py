"""Artifact completeness contract tests for Layer 2 outputs.

Verifies that all extraction artifacts have required metadata fields
for production-grade trustworthiness and downstream consumption.
"""

import pytest

from layer2_extraction.models import Capability, UseCase, Persona, ValueDriver, Feature, ValueMetric, Relationship
from layer2_extraction.validation.artifact_validator import (
    validate_artifact_for_persistence,
    validate_extraction_result,
    validate_relationship_for_persistence,
    ArtifactValidationError,
)
from layer2_extraction.models.extraction_response import ExtractionResult


class TestEntityMetadataCompleteness:
    """Test that all entity types have required metadata fields."""
    
    def test_capability_metadata_completeness(self):
        """Capability must have all required metadata fields."""
        entity = Capability(
            name="Test Capability",
            description="A test capability for validation",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        # Should not raise
        validate_artifact_for_persistence(entity, "entity")
    
    def test_capability_missing_tenant_id(self):
        """Capability without tenant_id should fail validation."""
        entity = Capability(
            name="Test Capability",
            description="A test capability for validation",
            tenant_id="",  # Empty
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact_for_persistence(entity, "entity")
        
        assert "tenant_id" in str(exc_info.value).lower()
    
    def test_capability_missing_deterministic_id(self):
        """Capability without deterministic_id should fail validation."""
        entity = Capability(
            name="Test Capability",
            description="A test capability for validation",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="",  # Empty
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact_for_persistence(entity, "entity")
        
        assert "deterministic_id" in str(exc_info.value).lower()
    
    def test_usecase_metadata_completeness(self):
        """UseCase must have all required metadata fields."""
        entity = UseCase(
            name="Test Use Case",
            description="A test use case for validation",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        # Should not raise
        validate_artifact_for_persistence(entity, "entity")
    
    def test_persona_metadata_completeness(self):
        """Persona must have all required metadata fields."""
        entity = Persona(
            role_type="economic_buyer",
            title="CFO",
            department="Finance",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        # Should not raise
        validate_artifact_for_persistence(entity, "entity")
    
    def test_valuedriver_metadata_completeness(self):
        """ValueDriver must have all required metadata fields."""
        entity = ValueDriver(
            category="cost_reduction",
            name="Operational Efficiency",
            description="Reduce operational costs",
            unit="USD",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        # Should not raise
        validate_artifact_for_persistence(entity, "entity")
    
    def test_feature_metadata_completeness(self):
        """Feature must have all required metadata fields."""
        entity = Feature(
            name="Test Feature",
            description="A test feature for validation",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        # Should not raise
        validate_artifact_for_persistence(entity, "entity")
    
    def test_valuemetric_metadata_completeness(self):
        """ValueMetric must have all required metadata fields."""
        entity = ValueMetric(
            name="Days Sales Outstanding",
            description="Average days to collect payment",
            unit="days",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        # Should not raise
        validate_artifact_for_persistence(entity, "entity")


class TestRelationshipMetadataCompleteness:
    """Test that relationships have required metadata fields."""
    
    def test_relationship_metadata_completeness(self):
        """Relationship must have all required metadata fields."""
        rel = Relationship(
            source_id="entity-1",
            target_id="entity-2",
            predicate="enables",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        # Should not raise
        validate_relationship_for_persistence(rel)
    
    def test_relationship_missing_source_id(self):
        """Relationship without source_id should fail validation."""
        rel = Relationship(
            source_id="",  # Empty
            target_id="entity-2",
            predicate="enables",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_relationship_for_persistence(rel)
        
        assert "source" in str(exc_info.value).lower()
    
    def test_relationship_missing_target_id(self):
        """Relationship without target_id should fail validation."""
        rel = Relationship(
            source_id="entity-1",
            target_id="",  # Empty
            predicate="enables",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_relationship_for_persistence(rel)
        
        assert "target" in str(exc_info.value).lower()


class TestExtractionResultCompleteness:
    """Test that ExtractionResult has required metadata fields."""
    
    def test_extraction_result_completeness(self):
        """ExtractionResult must have all required metadata fields."""
        result = ExtractionResult(
            job_id="job-456",
            source_url="https://example.com/doc",
            capabilities=[],
            use_cases=[],
            personas=[],
            value_drivers=[],
            features=[],
            chunks_processed=10,
            tenant_id="tenant-123",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        # Should not raise
        validate_extraction_result(result)
    
    def test_extraction_result_missing_tenant_id(self):
        """ExtractionResult without tenant_id should fail validation."""
        result = ExtractionResult(
            job_id="job-456",
            source_url="https://example.com/doc",
            capabilities=[],
            use_cases=[],
            personas=[],
            value_drivers=[],
            features=[],
            chunks_processed=10,
            tenant_id="",  # Empty
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_extraction_result(result)
        
        assert "tenant_id" in str(exc_info.value).lower()
    
    def test_extraction_result_with_entities_completeness(self):
        """ExtractionResult with entities must validate entity metadata."""
        entity = Capability(
            name="Test Capability",
            description="A test capability",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        result = ExtractionResult(
            job_id="job-456",
            source_url="https://example.com/doc",
            capabilities=[entity],
            use_cases=[],
            personas=[],
            value_drivers=[],
            features=[],
            chunks_processed=10,
            tenant_id="tenant-123",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        # Should not raise
        validate_extraction_result(result)
    
    def test_extraction_result_with_incomplete_entity(self):
        """ExtractionResult with incomplete entity should fail validation."""
        entity = Capability(
            name="Test Capability",
            description="A test capability",
            tenant_id="",  # Missing
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        result = ExtractionResult(
            job_id="job-456",
            source_url="https://example.com/doc",
            capabilities=[entity],
            use_cases=[],
            personas=[],
            value_drivers=[],
            features=[],
            chunks_processed=10,
            tenant_id="tenant-123",
            schema_version="v1",
            prompt_version_id="prompt-v1",
            model_version="gpt-4o",
        )
        
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_extraction_result(result)
        
        assert "capabilities" in str(exc_info.value).lower()


class TestPromptVersionIdField:
    """Test that prompt_version_id field is used instead of prompt_version."""
    
    def test_capability_uses_prompt_version_id(self):
        """Capability should use prompt_version_id field."""
        entity = Capability(
            name="Test Capability",
            description="A test capability",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",  # New field
            model_version="gpt-4o",
        )
        
        assert hasattr(entity, "prompt_version_id")
        assert entity.prompt_version_id == "prompt-v1"
    
    def test_relationship_uses_prompt_version_id(self):
        """Relationship should use prompt_version_id field."""
        rel = Relationship(
            source_id="entity-1",
            target_id="entity-2",
            predicate="enables",
            tenant_id="tenant-123",
            extraction_job_id="job-456",
            deterministic_id="det-789",
            schema_version="v1",
            prompt_version_id="prompt-v1",  # New field
            model_version="gpt-4o",
        )
        
        assert hasattr(rel, "prompt_version_id")
        assert rel.prompt_version_id == "prompt-v1"
