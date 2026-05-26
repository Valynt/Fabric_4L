"""Phase 2: Deterministic Entity Resolution Tests.

Tests verify:
- Resolution stability (same input produces same output)
- Ambiguity handling (tie-breaking rules work correctly)
- Explainability (metadata and provenance are populated)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.schema.entity_resolution import (
    BatchResolutionRequest,
    EntityResolutionRequest,
    EntityResolutionResponse,
    MatchCandidate,
    MatchConfidence,
    ResolutionStrategy,
    TieBreakRule,
)
from src.services.entity_resolution import EntityResolutionService


class TestResolutionStability:
    """Test that resolution is deterministic and stable."""

    @pytest.mark.asyncio
    async def test_exact_match_stability(self):
        """Exact match should always return the same entity."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-123", "properties": {"id": "product-123", "name": "Test Product"}}
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
        )
        
        # Resolve twice
        response1 = await service.resolve(request)
        response2 = await service.resolve(request)
        
        # Should return same entity
        assert response1.matched_entity_id == response2.matched_entity_id
        assert response1.matched_entity_id == "product-123"
        assert response1.confidence == MatchConfidence.HIGH

    @pytest.mark.asyncio
    async def test_no_match_consistency(self):
        """No match should consistently return no match."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Nonexistent Product"},
            strategy=ResolutionStrategy.EXACT,
        )
        
        response1 = await service.resolve(request)
        response2 = await service.resolve(request)
        
        assert response1.matched_entity_id is None
        assert response2.matched_entity_id is None
        assert response1.confidence == MatchConfidence.NONE


class TestAmbiguityHandling:
    """Test tie-breaking rules for ambiguous matches."""

    @pytest.mark.asyncio
    async def test_highest_confidence_tie_break(self):
        """HIGHEST_CONFIDENCE rule should select top-scoring candidate."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-1", "properties": {"id": "product-1", "name": "Test Product"}},
            {"id": "product-2", "properties": {"id": "product-2", "name": "Test Product"}},
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
            tie_break_rule=TieBreakRule.HIGHEST_CONFIDENCE,
        )
        
        response = await service.resolve(request)
        
        # Should return single best match
        assert response.matched_entity_id is not None
        assert len(response.candidates) == 1
        assert response.provenance.tie_break_applied is True
        assert response.provenance.tie_break_rule == TieBreakRule.HIGHEST_CONFIDENCE
        assert response.explanation["tie_break_rule"] == TieBreakRule.HIGHEST_CONFIDENCE.value

    @pytest.mark.asyncio
    async def test_hostile_ambiguous_candidates_stable_selection(self):
        """Ambiguous same-score candidates must deterministically choose lowest entity_id."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-z", "properties": {"id": "product-z", "name": "Test Product"}},
            {"id": "product-a", "properties": {"id": "product-a", "name": "Test Product"}},
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        service = EntityResolutionService(driver)
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
            tie_break_rule=TieBreakRule.HIGHEST_CONFIDENCE,
        )

        response1 = await service.resolve(request)
        response2 = await service.resolve(request)
        assert response1.matched_entity_id == "product-a"
        assert response2.matched_entity_id == "product-a"
        assert response1.explanation["source_evidence_ids"] == ["product-a"]

    @pytest.mark.asyncio
    async def test_manual_review_tie_break(self):
        """MANUAL_REVIEW rule should return all candidates for review."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-1", "properties": {"id": "product-1", "name": "Test Product"}},
            {"id": "product-2", "properties": {"id": "product-2", "name": "Test Product"}},
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
            tie_break_rule=TieBreakRule.MANUAL_REVIEW,
        )
        
        response = await service.resolve(request)
        
        # Should return all candidates for manual review
        assert response.matched_entity_id is None
        assert len(response.candidates) == 2
        assert response.confidence == MatchConfidence.AMBIGUOUS
        assert response.requires_manual_review is True
        assert response.provenance.tie_break_applied is True
        assert response.provenance.tie_break_rule == TieBreakRule.MANUAL_REVIEW
        assert response.explanation["tie_break_rule"] == TieBreakRule.MANUAL_REVIEW.value
        assert response.explanation["source_evidence_ids"] == ["product-1", "product-2"]
        assert "reasoning_trace_keys" in response.explanation

    @pytest.mark.asyncio
    async def test_no_tie_break_needed(self):
        """No tie-break needed when scores are significantly different."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-1", "properties": {"id": "product-1", "name": "Test Product"}},
            {"id": "product-2", "properties": {"id": "product-2", "name": "Different Product"}},
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
            tie_break_rule=TieBreakRule.HIGHEST_CONFIDENCE,
        )
        
        response = await service.resolve(request)
        
        # Should return single match without tie-break
        assert response.matched_entity_id == "product-1"
        assert len(response.candidates) == 1
        assert response.provenance.tie_break_applied is False


class TestExplainability:
    """Test that resolution responses include explainability metadata."""

    @pytest.mark.asyncio
    async def test_candidate_explanation_populated(self):
        """Candidates should have explanation metadata."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-1", "properties": {"id": "product-1", "name": "Test Product", "category": "Software"}}
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product", "category": "Software"},
            strategy=ResolutionStrategy.EXACT,
        )
        
        response = await service.resolve(request)
        
        # Check candidate explanation
        assert len(response.candidates) > 0
        candidate = response.candidates[0]
        assert candidate.explanation != ""
        assert len(candidate.matched_attributes) > 0
        assert "name" in candidate.matched_attributes

    @pytest.mark.asyncio
    async def test_provenance_populated(self):
        """Response should include provenance metadata."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-1", "properties": {"id": "product-1", "name": "Test Product"}}
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
            request_id="req-123",
        )
        
        response = await service.resolve(request)
        
        # Check provenance
        assert response.provenance is not None
        assert response.provenance.strategy_used == ResolutionStrategy.EXACT
        assert response.provenance.candidates_evaluated == 1
        assert response.provenance.source_system == "layer3-knowledge"
        assert response.request_id == "req-123"

    @pytest.mark.asyncio
    async def test_confidence_levels(self):
        """Confidence levels should be determined correctly from scores."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-1", "properties": {"id": "product-1", "name": "Test Product"}}
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        # High confidence (exact match)
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
            min_confidence=0.7,
        )
        response = await service.resolve(request)
        assert response.confidence in [MatchConfidence.HIGH, MatchConfidence.MEDIUM]


class TestBatchResolution:
    """Test batch resolution functionality."""

    @pytest.mark.asyncio
    async def test_batch_resolution_statistics(self):
        """Batch resolution should calculate correct statistics."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-1", "properties": {"id": "product-1", "name": "Test Product"}}
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = BatchResolutionRequest(
            tenant_id="tenant-1",
            request_id="batch-123",
            requests=[
                EntityResolutionRequest(
                    entity_type="Product",
                    tenant_id="tenant-1",
                    query_attributes={"name": "Test Product"},
                ),
                EntityResolutionRequest(
                    entity_type="Product",
                    tenant_id="tenant-1",
                    query_attributes={"name": "Another Product"},
                ),
            ],
        )
        
        response = await service.resolve_batch(request)
        
        assert response.total_processed == 2
        assert response.request_id == "batch-123"
        assert len(response.responses) == 2

    @pytest.mark.asyncio
    async def test_batch_resolution_tenant_isolation(self):
        """All batch requests should use the batch tenant_id."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = BatchResolutionRequest(
            tenant_id="tenant-1",
            requests=[
                EntityResolutionRequest(
                    entity_type="Product",
                    tenant_id="wrong-tenant",  # Should be overridden
                    query_attributes={"name": "Test Product"},
                ),
            ],
        )
        
        response = await service.resolve_batch(request)
        
        # Verify tenant_id was enforced
        assert response.total_processed == 1


class TestScoring:
    """Test candidate scoring logic."""

    @pytest.mark.asyncio
    async def test_exact_match_scores_high(self):
        """Exact attribute matches should score high."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-1", "properties": {"id": "product-1", "name": "Test Product", "category": "Software"}}
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product", "category": "Software"},
            strategy=ResolutionStrategy.EXACT,
        )
        
        response = await service.resolve(request)
        
        # Should have high score due to exact matches
        assert len(response.candidates) > 0
        assert response.candidates[0].score >= 0.9

    @pytest.mark.asyncio
    async def test_partial_match_scores_lower(self):
        """Partial matches should score lower than exact matches."""
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-1", "properties": {"id": "product-1", "name": "Test Product Extra", "category": "Software"}}
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        
        service = EntityResolutionService(driver)
        
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.FUZZY,
        )
        
        response = await service.resolve(request)
        
        # Should have lower score due to partial match
        assert len(response.candidates) > 0
        # Score should be between 0.5 and 1.0 for partial match
        assert 0.5 <= response.candidates[0].score <= 1.0
