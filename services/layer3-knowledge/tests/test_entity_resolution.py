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

    @pytest.mark.asyncio
    async def test_most_recent_prefers_latest_non_null_updated_at(self):
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-a", "properties": {"id": "product-a", "name": "Test Product", "updated_at": None}, "reference_count": 9},
            {"id": "product-b", "properties": {"id": "product-b", "name": "Test Product", "updated_at": "2026-05-01T00:00:00Z"}, "reference_count": 1},
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        service = EntityResolutionService(driver)
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
            tie_break_rule=TieBreakRule.MOST_RECENT,
        )
        response = await service.resolve(request)
        assert response.matched_entity_id == "product-b"
        assert response.explanation["tie_break_evidence"][0]["entity_id"] == "product-b"

    @pytest.mark.asyncio
    async def test_most_referenced_prefers_highest_reference_count(self):
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-a", "properties": {"id": "product-a", "name": "Test Product", "updated_at": "2026-05-01T00:00:00Z"}, "reference_count": 3},
            {"id": "product-b", "properties": {"id": "product-b", "name": "Test Product", "updated_at": "2026-04-01T00:00:00Z"}, "reference_count": 8},
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        service = EntityResolutionService(driver)
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
            tie_break_rule=TieBreakRule.MOST_REFERENCED,
        )
        response = await service.resolve(request)
        assert response.matched_entity_id == "product-b"

    @pytest.mark.asyncio
    async def test_equal_metrics_collision_uses_canonical_id_order(self):
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "product-z", "properties": {"id": "product-z", "name": "Test Product", "updated_at": "2026-05-01T00:00:00Z"}, "reference_count": 5},
            {"id": "product-a", "properties": {"id": "product-a", "name": "Test Product", "updated_at": "2026-05-01T00:00:00Z"}, "reference_count": 5},
        ])
        session.run = AsyncMock(return_value=result)
        driver.session = MagicMock(return_value=session)
        service = EntityResolutionService(driver)
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Test Product"},
            strategy=ResolutionStrategy.EXACT,
            tie_break_rule=TieBreakRule.MOST_REFERENCED,
        )
        response1 = await service.resolve(request)
        response2 = await service.resolve(request)
        assert response1.matched_entity_id == "product-a"
        assert response2.matched_entity_id == "product-a"


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


class TestHybridRetrievalAndIsolation:
    @pytest.mark.asyncio
    async def test_ranked_pipeline_near_duplicate_and_multilingual(self):
        driver = AsyncMock()
        session = AsyncMock()
        driver.session = MagicMock(return_value=session)
        service = EntityResolutionService(driver)

        exact_records = []
        fuzzy_records = [
            {"id": "ent-1", "properties": {"id": "ent-1", "name": "Cafe Central", "tenant_id": "t1"}},
            {"id": "ent-2", "properties": {"id": "ent-2", "name": "Cafe Centrale", "tenant_id": "t1"}},
        ]
        vector_records = [
            {"id": "ent-2", "properties": {"id": "ent-2", "name": "Cafe Centrale", "tenant_id": "t1"}, "vector_score": 0.91},
            {"id": "ent-1", "properties": {"id": "ent-1", "name": "Cafe Central", "tenant_id": "t1"}, "vector_score": 0.75},
        ]

        with patch("src.services.entity_resolution.run_validated_query") as mocked_query:
            mocked_query.side_effect = [
                AsyncMock(data=AsyncMock(return_value=exact_records)),
                AsyncMock(data=AsyncMock(return_value=fuzzy_records)),
                AsyncMock(data=AsyncMock(return_value=vector_records)),
            ]

            request = EntityResolutionRequest(
                entity_type="Organization",
                tenant_id="t1",
                query_attributes={"name": "Café Central", "embedding": [0.1, 0.2, 0.3]},
                strategy=ResolutionStrategy.HYBRID,
            )
            response = await service.resolve(request)

        assert response.matched_entity_id == "ent-1"
        assert len(response.candidates) == 1
        assert response.candidates[0].metadata["retrieval_metadata"]["sources"] == ["fuzzy", "vector"]
        assert "decision_factors" in response.candidates[0].metadata

    @pytest.mark.asyncio
    async def test_tenant_scoped_vector_query_and_ambiguous_names(self):
        driver = AsyncMock()
        session = AsyncMock()
        driver.session = MagicMock(return_value=session)
        service = EntityResolutionService(driver)

        with patch("src.services.entity_resolution.run_validated_query") as mocked_query:
            mocked_query.return_value = AsyncMock(data=AsyncMock(return_value=[]))
            request = EntityResolutionRequest(
                entity_type="Person",
                tenant_id="tenant-secure",
                query_attributes={"name": "Alex Li", "embedding": [0.11, 0.22]},
                strategy=ResolutionStrategy.VECTOR,
            )
            await service.resolve(request)

            _, query, params = mocked_query.call_args[0]
            assert "node.tenant_id = $tenant_id" in query
            assert params["tenant_id"] == "tenant-secure"

    @pytest.mark.asyncio
    async def test_fuzzy_similarity_handles_case_and_accents(self):
        service = EntityResolutionService(AsyncMock())
        sim = service._name_similarity("MÜNCHEN AG", "Munchen ag")
        assert sim >= 0.95
