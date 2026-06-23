"""Tests for deterministic entity ID generation.

Verifies that the same entity extracted from the same source produces
identical IDs across idempotent re-runs, ensuring stable entity identity
for downstream graph/agent consumption.
"""

import pytest

from layer2_extraction.extraction.entity_id import compute_deterministic_id, _build_entity_signature
from layer2_extraction.models import Capability, UseCase, Persona, ValueDriver, Feature, ValueMetric


class TestDeterministicIDStability:
    """Test that identical inputs produce identical IDs."""

    def test_capability_id_stability(self):
        """Same capability from same tenant/source produces same ID."""
        entity = Capability(
            name="Real-time Analytics",
            description="Process data streams with sub-second latency",
            technical_features=["streaming", "low-latency"],
            confidence=0.9,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity,
            extraction_version="v1",
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity,
            extraction_version="v1",
        )
        
        assert id1 == id2
        assert len(id1) == 36  # UUIDv5 string

    def test_capability_id_changes_with_different_tenant(self):
        """Different tenant produces different ID for same entity."""
        entity = Capability(
            name="Real-time Analytics",
            description="Process data streams with sub-second latency",
            technical_features=["streaming"],
            confidence=0.9,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity,
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-456",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity,
        )
        
        assert id1 != id2

    def test_capability_id_changes_with_different_source(self):
        """Different source hash produces different ID."""
        entity = Capability(
            name="Real-time Analytics",
            description="Process data streams",
            technical_features=[],
            confidence=0.9,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity,
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc2",
            entity_type="capability",
            entity=entity,
        )
        
        assert id1 != id2

    def test_capability_id_changes_with_extraction_version(self):
        """Different extraction version produces different ID."""
        entity = Capability(
            name="Real-time Analytics",
            description="Process data streams",
            technical_features=[],
            confidence=0.9,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity,
            extraction_version="v1",
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity,
            extraction_version="v2",
        )
        
        assert id1 != id2

    def test_usecase_id_stability(self):
        """UseCase IDs are stable across re-runs."""
        entity = UseCase(
            name="Fraud Detection",
            description="Identify suspicious transactions in real-time",
            industry_context=["finance", "banking"],
            confidence=0.85,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="usecase",
            entity=entity,
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="usecase",
            entity=entity,
        )
        
        assert id1 == id2

    def test_persona_id_stability(self):
        """Persona IDs are stable across re-runs."""
        entity = Persona(
            role_type="economic_buyer",
            seniority_level="c_suite",
            title="Chief Financial Officer",
            department="Finance",
            confidence=0.9,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="persona",
            entity=entity,
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="persona",
            entity=entity,
        )
        
        assert id1 == id2

    def test_valuedriver_id_stability(self):
        """ValueDriver IDs are stable across re-runs."""
        entity = ValueDriver(
            category="cost_reduction",
            name="Operational Efficiency",
            description="Reduce operational costs through automation",
            unit="USD",
            confidence=0.88,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="valuedriver",
            entity=entity,
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="valuedriver",
            entity=entity,
        )
        
        assert id1 == id2

    def test_feature_id_stability(self):
        """Feature IDs are stable across re-runs."""
        entity = Feature(
            name="API Gateway",
            description="Centralized API management",
            confidence=0.92,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="feature",
            entity=entity,
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="feature",
            entity=entity,
        )
        
        assert id1 == id2

    def test_valuemetric_id_stability(self):
        """ValueMetric IDs are stable across re-runs."""
        entity = ValueMetric(
            name="Days Sales Outstanding",
            description="Average number of days to collect payment",
            unit="days",
            direction="lower_is_better",
            confidence=0.9,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="valuemetric",
            entity=entity,
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="valuemetric",
            entity=entity,
        )
        
        assert id1 == id2


class TestEntitySignatureNormalization:
    """Test that entity signatures are normalized for stability."""

    def test_text_normalization_case_insensitive(self):
        """Text normalization is case-insensitive."""
        entity1 = Capability(
            name="Real-Time Analytics",
            description="Process DATA Streams",
            technical_features=[],
            confidence=0.9,
        )
        
        entity2 = Capability(
            name="real-time analytics",
            description="process data streams",
            technical_features=[],
            confidence=0.9,
        )
        
        sig1 = _build_entity_signature("capability", entity1)
        sig2 = _build_entity_signature("capability", entity2)
        
        assert sig1 == sig2

    def test_text_normalization_whitespace(self):
        """Text normalization collapses whitespace."""
        entity1 = Capability(
            name="Real-Time  Analytics",
            description="Process  data  streams",
            technical_features=[],
            confidence=0.9,
        )
        
        entity2 = Capability(
            name="Real-Time Analytics",
            description="Process data streams",
            technical_features=[],
            confidence=0.9,
        )
        
        sig1 = _build_entity_signature("capability", entity1)
        sig2 = _build_entity_signature("capability", entity2)
        
        assert sig1 == sig2

    def test_feature_list_ordering(self):
        """Feature lists are sorted for signature stability."""
        entity1 = Capability(
            name="Analytics",
            description="Data processing",
            technical_features=["streaming", "low-latency", "batch"],
            confidence=0.9,
        )
        
        entity2 = Capability(
            name="Analytics",
            description="Data processing",
            technical_features=["batch", "streaming", "low-latency"],
            confidence=0.9,
        )
        
        sig1 = _build_entity_signature("capability", entity1)
        sig2 = _build_entity_signature("capability", entity2)
        
        assert sig1 == sig2

    def test_feature_list_deduplication(self):
        """Duplicate features are removed for signature stability."""
        entity1 = Capability(
            name="Analytics",
            description="Data processing",
            technical_features=["streaming", "streaming", "batch"],
            confidence=0.9,
        )
        
        entity2 = Capability(
            name="Analytics",
            description="Data processing",
            technical_features=["streaming", "batch"],
            confidence=0.9,
        )
        
        sig1 = _build_entity_signature("capability", entity1)
        sig2 = _build_entity_signature("capability", entity2)
        
        assert sig1 == sig2


class TestIDUniqueness:
    """Test that different entities produce different IDs."""

    def test_different_capabilities_different_ids(self):
        """Different capabilities produce different IDs."""
        entity1 = Capability(
            name="Analytics",
            description="Data processing",
            technical_features=[],
            confidence=0.9,
        )
        
        entity2 = Capability(
            name="Security",
            description="Access control",
            technical_features=[],
            confidence=0.9,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity1,
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity2,
        )
        
        assert id1 != id2

    def test_different_entity_types_different_ids(self):
        """Same name but different entity types produce different IDs."""
        entity1 = Capability(
            name="Analytics",
            description="Data processing",
            technical_features=[],
            confidence=0.9,
        )
        
        entity2 = Feature(
            name="Analytics",
            description="Data processing",
            confidence=0.9,
        )
        
        id1 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="capability",
            entity=entity1,
        )
        
        id2 = compute_deterministic_id(
            tenant_id="tenant-123",
            source_hash="source-hash-doc1",
            entity_type="feature",
            entity=entity2,
        )
        
        assert id1 != id2
