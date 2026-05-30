"""Contract tests for Entity Browser canonical API.

Validates that backend models and API responses match the canonical contract.
These tests do not require Neo4j and run quickly.
"""

import pytest
from datetime import UTC, datetime

try:
    from pydantic import ValidationError
    from src.api.models import (
        EntitySummary,
        EntityDetail,
        EntityFilterRequest,
        EntityListResponse,
        EntityRelationships,
        RelationshipPreview,
        ProvenanceEvent,
    )
except (ImportError, Exception):
    pytest.skip(
        "src service stack not available (check PYTHONPATH / installed packages)",
        allow_module_level=True,
    )


class TestEntitySummaryContract:
    """Validate EntitySummary canonical contract."""

    def test_entity_summary_creation_valid(self):
        """Test creating valid EntitySummary with all fields."""
        entity = EntitySummary(
            id="ent-123",
            name="Test Capability",
            entity_type="Capability",
            domain="Finance",
            status="validated",
            confidence=0.94,
            confidence_label="high",
            description="A test entity",
            updated_at=datetime.now(UTC),
            source_name="test-source",
            extraction_job_id="job-456",
        )
        
        assert entity.id == "ent-123"
        assert entity.name == "Test Capability"
        assert entity.domain == "Finance"
        assert entity.status == "validated"
        assert entity.confidence == 0.94
        assert entity.confidence_label == "high"

    def test_entity_summary_minimal_valid(self):
        """Test EntitySummary with only required fields."""
        entity = EntitySummary(
            id="ent-123",
            name="Test Entity",
            entity_type="UseCase",
            status="pending",
            confidence=0.75,
            confidence_label="medium",
            updated_at=datetime.now(UTC),
        )
        
        # Optional fields should be None
        assert entity.domain is None
        assert entity.source_name is None

    def test_entity_summary_confidence_label_derivation(self):
        """Test confidence_label auto-derivation from confidence score."""
        entity = EntitySummary(
            id="ent-123",
            name="Test",
            entity_type="Capability",
            status="validated",
            confidence=0.95,
            updated_at=datetime.now(UTC),
        )
        
        assert entity.confidence_label == "high"

    def test_entity_summary_status_derivation(self):
        """Test status auto-derivation from confidence score."""
        entity = EntitySummary(
            id="ent-123",
            name="Test",
            entity_type="Capability",
            confidence=0.65,
            updated_at=datetime.now(UTC),
        )
        
        assert entity.status == "draft"

    def test_entity_summary_confidence_bounds(self):
        """Test confidence must be 0.0-1.0."""
        with pytest.raises(ValidationError):
            EntitySummary(
                id="ent-123",
                name="Test",
                entity_type="Capability",
                status="validated",
                confidence=1.5,  # Invalid: > 1.0
                updated_at=datetime.now(UTC),
            )

    def test_entity_summary_id_length_limit(self):
        """Test entity ID length validation."""
        with pytest.raises(ValidationError):
            EntitySummary(
                id="x" * 300,  # Too long (>255)
                name="Test",
                entity_type="Capability",
                status="validated",
                confidence=0.9,
                updated_at=datetime.now(UTC),
            )

    def test_entity_summary_invalid_status(self):
        """Test invalid status is rejected."""
        with pytest.raises(ValidationError):
            EntitySummary(
                id="ent-123",
                name="Test",
                entity_type="Capability",
                status="invalid_status",  # Not in enum
                confidence=0.9,
                updated_at=datetime.now(UTC),
            )


class TestEntityDetailContract:
    """Validate EntityDetail canonical contract."""

    def test_entity_detail_creation(self):
        """Test creating valid EntityDetail with relationships."""
        detail = EntityDetail(
            id="ent-123",
            name="Test Entity",
            entity_type="Capability",
            domain="Finance",
            status="validated",
            confidence=0.94,
            confidence_label="high",
            updated_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            relationships=EntityRelationships(
                total_count=2,
                incoming=[
                    RelationshipPreview(
                        relationship_type="DEPENDS_ON",
                        target_entity_id="ent-456",
                        target_entity_name="Parent Entity",
                        target_entity_type="Capability",
                    )
                ],
                outgoing=[],
            ),
            provenance=[
                ProvenanceEvent(
                    event_type="extracted",
                    timestamp=datetime.now(UTC),
                    actor="extraction-job-1",
                    details={"source": "acmecorp.com"},
                )
            ],
        )
        
        assert detail.relationships.total_count == 2
        assert len(detail.provenance) == 1
        assert detail.provenance[0].event_type == "extracted"

    def test_entity_detail_is_entity_summary_superset(self):
        """Verify EntityDetail contains all EntitySummary fields."""
        summary_fields = set(EntitySummary.model_fields.keys())
        detail_fields = set(EntityDetail.model_fields.keys())
        
        # All summary fields should be in detail
        assert summary_fields.issubset(detail_fields), \
            f"Missing fields: {summary_fields - detail_fields}"


class TestEntityFilterRequestContract:
    """Validate EntityFilterRequest contract."""

    def test_filter_request_defaults(self):
        """Test default filter values."""
        filters = EntityFilterRequest()
        
        assert filters.limit == 25  # Default per production spec
        assert filters.offset == 0
        assert filters.sort_by == "updated_at"
        assert filters.sort_order == "desc"

    def test_filter_request_pagination_limits(self):
        """Test pagination limits enforced."""
        # Max limit is 100
        with pytest.raises(ValidationError):
            EntityFilterRequest(limit=200)
        
        # Min limit is 1
        with pytest.raises(ValidationError):
            EntityFilterRequest(limit=0)

    def test_filter_request_confidence_range(self):
        """Test confidence range validation."""
        # Valid range
        filters = EntityFilterRequest(min_confidence=0.5, max_confidence=0.9)
        assert filters.min_confidence == 0.5
        assert filters.max_confidence == 0.9
        
        # Out of bounds
        with pytest.raises(ValidationError):
            EntityFilterRequest(min_confidence=-0.1)
        
        with pytest.raises(ValidationError):
            EntityFilterRequest(max_confidence=1.5)

    def test_filter_request_search_text_limit(self):
        """Test search text length limit."""
        with pytest.raises(ValidationError):
            EntityFilterRequest(search_text="x" * 300)  # > 200 limit

    def test_filter_request_valid_domains(self):
        """Test domain filter accepts list."""
        filters = EntityFilterRequest(domains=["Finance", "IT", "Healthcare"])
        assert filters.domains == ["Finance", "IT", "Healthcare"]

    def test_filter_request_valid_statuses(self):
        """Test status filter accepts valid enum values."""
        filters = EntityFilterRequest(statuses=["validated", "pending"])
        assert "validated" in filters.statuses
        
        # Invalid status
        with pytest.raises(ValidationError):
            EntityFilterRequest(statuses=["invalid"])


class TestEntityListResponseContract:
    """Validate EntityListResponse contract."""

    def test_list_response_structure(self):
        """Test complete list response structure."""
        now = datetime.now(UTC)
        
        response = EntityListResponse(
            results=[
                EntitySummary(
                    id="ent-1",
                    name="Entity 1",
                    entity_type="Capability",
                    status="validated",
                    confidence=0.9,
                    updated_at=now,
                ),
                EntitySummary(
                    id="ent-2",
                    name="Entity 2",
                    entity_type="UseCase",
                    status="pending",
                    confidence=0.75,
                    updated_at=now,
                ),
            ],
            total_count=100,
            filtered_count=50,
            limit=25,
            offset=0,
            has_more=True,
            available_domains=["Finance", "IT"],
            available_sources=["source1", "source2"],
        )
        
        assert len(response.results) == 2
        assert response.total_count == 100
        assert response.filtered_count == 50
        assert response.has_more is True
        assert "Finance" in response.available_domains

    def test_list_response_empty(self):
        """Test empty list response."""
        response = EntityListResponse(
            results=[],
            total_count=0,
            filtered_count=0,
            limit=25,
            offset=0,
            has_more=False,
            available_domains=[],
            available_sources=[],
        )
        
        assert response.results == []
        assert response.has_more is False

    def test_list_response_pagination_calculation(self):
        """Test has_more calculation logic."""
        # offset=0, limit=25, filtered=50 → has_more=True
        response = EntityListResponse(
            results=[],
            total_count=100,
            filtered_count=50,
            limit=25,
            offset=0,
            has_more=True,
        )
        assert response.has_more is True


class TestRelationshipContract:
    """Validate relationship models."""

    def test_relationship_preview(self):
        """Test RelationshipPreview model."""
        rel = RelationshipPreview(
            relationship_type="ENABLES",
            target_entity_id="ent-456",
            target_entity_name="Target Entity",
            target_entity_type="Capability",
        )
        
        assert rel.relationship_type == "ENABLES"
        assert rel.target_entity_name == "Target Entity"

    def test_entity_relationships_limits(self):
        """Test relationship sample limits."""
        relationships = EntityRelationships(
            total_count=100,
            incoming=[],
            outgoing=[],
        )
        
        assert relationships.total_count == 100
        
        # Should enforce max 5 in each direction
        with pytest.raises(ValidationError):
            EntityRelationships(
                total_count=10,
                incoming=[
                    RelationshipPreview(
                        relationship_type="DEPENDS_ON",
                        target_entity_id=f"ent-{i}",
                        target_entity_name=f"Entity {i}",
                        target_entity_type="Capability",
                    )
                    for i in range(10)  # Too many (>5)
                ],
            )


class TestProvenanceContract:
    """Validate provenance event models."""

    def test_provenance_event_creation(self):
        """Test ProvenanceEvent model."""
        event = ProvenanceEvent(
            event_type="extracted",
            timestamp=datetime.now(UTC),
            actor="extraction-job-123",
            details={"source": "acmecorp.com", "confidence": 0.94},
        )
        
        assert event.event_type == "extracted"
        assert event.actor == "extraction-job-123"

    def test_provenance_event_types(self):
        """Test valid provenance event types."""
        valid_types = ["extracted", "validated", "modified", "merged", "deprecated"]
        
        for event_type in valid_types:
            event = ProvenanceEvent(
                event_type=event_type,
                timestamp=datetime.now(UTC),
                actor="test",
            )
            assert event.event_type == event_type


class TestFieldConsistency:
    """Validate field consistency across models."""

    def test_status_values_consistent(self):
        """Test that status enum is consistent everywhere."""
        from src.api.models import EntityStatus
        
        expected_values = {"validated", "pending", "draft", "deprecated"}
        actual_values = set(EntityStatus.__args__)
        
        assert actual_values == expected_values, \
            f"Status values mismatch: {actual_values}"

    def test_confidence_label_values_consistent(self):
        """Test confidence_label enum consistency."""
        from src.api.models import ConfidenceLabel
        
        expected_values = {"high", "medium", "low"}
        actual_values = set(ConfidenceLabel.__args__)
        
        assert actual_values == expected_values

    def test_domain_field_type_consistent(self):
        """Test domain field is optional string in all models."""
        # EntitySummary
        summary = EntitySummary(
            id="ent-1",
            name="Test",
            entity_type="Capability",
            domain="Finance",
            status="validated",
            confidence=0.9,
            updated_at=datetime.now(UTC),
        )
        assert summary.domain == "Finance"
        
        # EntityDetail
        detail = EntityDetail(
            id="ent-1",
            name="Test",
            entity_type="Capability",
            domain=None,  # Nullable
            status="validated",
            confidence=0.9,
            updated_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        assert detail.domain is None