"""Phase 2: Deterministic Entity Resolution Policy.

Implements the resolution policy with:
- Scoring algorithms for different strategies
- Tie-breaking rules for ambiguous matches
- Explainability metadata generation
- Provenance tracking
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from neo4j import AsyncDriver

from ..db.query_execution import run_validated_query
from ..schema.entity_resolution import (
    BatchResolutionRequest,
    BatchResolutionResponse,
    EntityResolutionRequest,
    EntityResolutionResponse,
    MatchCandidate,
    MatchConfidence,
    ResolutionProvenance,
    ResolutionStrategy,
    TieBreakRule,
)

logger = logging.getLogger(__name__)

# Constants for scoring and confidence thresholds
_SCORE_DIFF_THRESHOLD = 0.1
_CONFIDENCE_HIGH_THRESHOLD = 0.9
_CONFIDENCE_MEDIUM_THRESHOLD = 0.7
_CONFIDENCE_LOW_THRESHOLD = 0.5
_CANDIDATE_LIMIT = 10


class EntityResolutionService:
    """Service for deterministic entity resolution."""

    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    async def resolve(self, request: EntityResolutionRequest) -> EntityResolutionResponse:
        """Resolve a single entity using the specified strategy.

        Args:
            request: Resolution request with query attributes and strategy

        Returns:
            Resolution response with matched entity and confidence
        """
        provenance = ResolutionProvenance(
            strategy_used=request.strategy,
            source_system="layer3-knowledge",
        )

        try:
            # Find candidates based on strategy
            candidates = await self._find_candidates(request)
            provenance.candidates_evaluated = len(candidates)

            # Score candidates
            scored_candidates = await self._score_candidates(request, candidates)

            # Apply tie-breaking if needed
            if len(scored_candidates) > 1:
                provenance.tie_break_applied = True
                provenance.tie_break_rule = request.tie_break_rule
                scored_candidates = self._apply_tie_break(
                    scored_candidates, request.tie_break_rule
                )

            selected_tie_break_rule = (
                request.tie_break_rule.value if provenance.tie_break_applied else "none"
            )

            # Determine final match
            if not scored_candidates:
                response = EntityResolutionResponse(
                    request_id=request.request_id,
                    matched_entity_id=None,
                    confidence=MatchConfidence.NONE,
                    candidates=[],
                    provenance=provenance,
                    requires_manual_review=False,
                    explanation=self._build_explanation(
                        canonical_entity_id=None,
                        confidence_score=0.0,
                        tie_break_rule=selected_tie_break_rule,
                        candidates=[],
                    ),
                )
            elif len(scored_candidates) == 1:
                top_candidate = scored_candidates[0]
                confidence = self._determine_confidence(top_candidate.score, request.min_confidence)
                response = EntityResolutionResponse(
                    request_id=request.request_id,
                    matched_entity_id=top_candidate.entity_id,
                    confidence=confidence,
                    candidates=scored_candidates,
                    provenance=provenance,
                    requires_manual_review=(confidence == MatchConfidence.AMBIGUOUS),
                    explanation=self._build_explanation(
                        canonical_entity_id=top_candidate.entity_id,
                        confidence_score=top_candidate.score,
                        tie_break_rule=selected_tie_break_rule,
                        candidates=scored_candidates,
                    ),
                )
            else:
                # Multiple candidates after tie-break - ambiguous
                response = EntityResolutionResponse(
                    request_id=request.request_id,
                    matched_entity_id=None,
                    confidence=MatchConfidence.AMBIGUOUS,
                    candidates=scored_candidates,
                    provenance=provenance,
                    requires_manual_review=True,
                    explanation=self._build_explanation(
                        canonical_entity_id=None,
                        confidence_score=scored_candidates[0].score if scored_candidates else 0.0,
                        tie_break_rule=selected_tie_break_rule,
                        candidates=scored_candidates,
                    ),
                )

            return response

        except Exception as e:
            logger.error(f"Entity resolution failed: {e}", exc_info=True)
            return EntityResolutionResponse(
                request_id=request.request_id,
                matched_entity_id=None,
                confidence=MatchConfidence.NONE,
                candidates=[],
                provenance=provenance,
                requires_manual_review=True,
                error=str(e),
                explanation=self._build_explanation(
                    canonical_entity_id=None,
                    confidence_score=0.0,
                    tie_break_rule="error",
                    candidates=[],
                ),
            )

    async def resolve_batch(self, request: BatchResolutionRequest) -> BatchResolutionResponse:
        """Resolve multiple entities in batch.

        Args:
            request: Batch resolution request

        Returns:
            Batch resolution response with statistics
        """
        responses = []
        successful = 0
        failed = 0
        requires_review = 0

        for req in request.requests:
            # Create a copy to avoid mutating input objects
            req_copy = req.model_copy(update={
                "tenant_id": request.tenant_id,
                "request_id": req.request_id or request.request_id,
            })

            response = await self.resolve(req_copy)
            responses.append(response)

            if response.error:
                failed += 1
            elif response.requires_manual_review:
                requires_review += 1
            else:
                successful += 1

        return BatchResolutionResponse(
            request_id=request.request_id,
            responses=responses,
            total_processed=len(responses),
            successful=successful,
            failed=failed,
            requires_manual_review=requires_review,
        )

    async def _find_candidates(
        self, request: EntityResolutionRequest
    ) -> list[dict[str, Any]]:
        """Find candidate entities based on strategy.

        Args:
            request: Resolution request

        Returns:
            List of candidate entity records
        """
        async with self._driver.session() as session:
            if request.strategy == ResolutionStrategy.EXACT:
                return await self._find_exact_candidates(session, request)
            elif request.strategy == ResolutionStrategy.FUZZY:
                return await self._find_fuzzy_candidates(session, request)
            elif request.strategy == ResolutionStrategy.VECTOR:
                return await self._find_vector_candidates(session, request)
            else:  # HYBRID
                return await self._find_hybrid_candidates(session, request)

    async def _find_exact_candidates(
        self, session, request: EntityResolutionRequest
    ) -> list[dict[str, Any]]:
        """Find candidates using exact attribute matching."""
        # Build WHERE clauses from query attributes
        where_clauses = []
        params = {"tenant_id": request.tenant_id}
        
        for key, value in request.query_attributes.items():
            if value is not None:
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value

        where_clause = " AND ".join(where_clauses) if where_clauses else "true"
        
        query = f"""
        MATCH (n:{request.entity_type} {{tenant_id: $tenant_id}})
        WHERE {where_clause}
        RETURN n.id as id, n as properties
        LIMIT {_CANDIDATE_LIMIT}
        """
        
        result = await run_validated_query(session, query, params)
        records = await result.data()
        return records

    async def _find_fuzzy_candidates(
        self, session, request: EntityResolutionRequest
    ) -> list[dict[str, Any]]:
        """Find candidates using fuzzy name matching.
        
        TODO: Implement Levenshtein distance or similar fuzzy matching algorithm.
        Currently falls back to substring matching as a placeholder.
        """
        name = request.query_attributes.get("name")
        if not name:
            return await self._find_exact_candidates(session, request)
        
        query = f"""
        MATCH (n:{request.entity_type} {{tenant_id: $tenant_id}})
        WHERE toLower(n.name) CONTAINS toLower($name)
        RETURN n.id as id, n as properties
        LIMIT {_CANDIDATE_LIMIT}
        """
        
        result = await run_validated_query(session, query, {
            "tenant_id": request.tenant_id,
            "name": name,
        })
        records = await result.data()
        return records

    async def _find_vector_candidates(
        self, session, request: EntityResolutionRequest
    ) -> list[dict[str, Any]]:
        """Find candidates using vector similarity.
        
        TODO: Implement vector similarity search using pgvector or Neo4j vector index.
        Currently falls back to fuzzy matching as a placeholder.
        """
        return await self._find_fuzzy_candidates(session, request)

    async def _find_hybrid_candidates(
        self, session, request: EntityResolutionRequest
    ) -> list[dict[str, Any]]:
        """Find candidates using hybrid exact + fuzzy matching."""
        exact = await self._find_exact_candidates(session, request)
        if exact:
            return exact
        return await self._find_fuzzy_candidates(session, request)

    async def _score_candidates(
        self, request: EntityResolutionRequest, candidates: list[dict[str, Any]]
    ) -> list[MatchCandidate]:
        """Score candidates based on match quality.

        Args:
            request: Resolution request
            candidates: Candidate entity records

        Returns:
            List of scored candidates
        """
        scored = []
        
        for candidate in candidates:
            score = 0.0
            matched_attrs = []
            explanation_parts = []
            
            props = candidate.get("properties", {})
            
            # Score based on attribute matches
            for attr, query_value in request.query_attributes.items():
                if query_value is None:
                    continue
                    
                entity_value = props.get(attr)
                if entity_value is not None:
                    if str(entity_value).lower() == str(query_value).lower():
                        score += 1.0
                        matched_attrs.append(attr)
                        explanation_parts.append(f"Exact match on {attr}")
                    elif str(query_value).lower() in str(entity_value).lower():
                        score += 0.5
                        matched_attrs.append(attr)
                        explanation_parts.append(f"Partial match on {attr}")
            
            # Normalize score
            num_attrs = len([v for v in request.query_attributes.values() if v is not None])
            if num_attrs > 0:
                score = score / num_attrs
            
            # Add explanation
            explanation = "; ".join(explanation_parts) if explanation_parts else "No strong matches"
            
            scored.append(MatchCandidate(
                entity_id=candidate["id"],
                entity_type=request.entity_type,
                score=score,
                matched_attributes=matched_attrs,
                explanation=explanation,
                metadata={"raw_properties": props},
            ))
        
        # Sort by score descending
        return sorted(scored, key=lambda c: (-c.score, c.entity_id))

    def _apply_tie_break(
        self, candidates: list[MatchCandidate], rule: TieBreakRule
    ) -> list[MatchCandidate]:
        """Apply tie-breaking rule to ambiguous matches.

        Args:
            candidates: Scored candidates
            rule: Tie-break rule to apply

        Returns:
            Candidates after tie-breaking (may return multiple if MANUAL_REVIEW)
        """
        if len(candidates) <= 1:
            return candidates
        
        # Check if scores are significantly different
        top_score = candidates[0].score
        second_score = candidates[1].score if len(candidates) > 1 else 0
        
        # If top score is significantly higher, no tie-break needed
        if top_score - second_score > _SCORE_DIFF_THRESHOLD:
            return [candidates[0]]
        
        if rule == TieBreakRule.MANUAL_REVIEW:
            # Return all candidates for manual review
            return candidates
        elif rule == TieBreakRule.HIGHEST_CONFIDENCE:
            # Already sorted by score, return top
            return [candidates[0]]
        elif rule == TieBreakRule.MOST_RECENT:
            # TODO: Implement most_recent tie-break using updated_at property
            return [candidates[0]]
        elif rule == TieBreakRule.MOST_REFERENCED:
            # TODO: Implement most_referenced tie-break using relationship count
            return [candidates[0]]
        else:
            return [candidates[0]]

    def _build_explanation(
        self,
        *,
        canonical_entity_id: str | None,
        confidence_score: float,
        tie_break_rule: str,
        candidates: list[MatchCandidate],
    ) -> dict[str, Any]:
        """Build a transparent deterministic explanation payload."""
        return {
            "canonical_entity_id": canonical_entity_id,
            "confidence": confidence_score,
            "tie_break_rule": tie_break_rule,
            "source_evidence_ids": [candidate.entity_id for candidate in candidates],
            "reasoning_trace_keys": [
                "candidate_retrieval",
                "candidate_scoring",
                "deterministic_ordering",
                "tie_break_resolution",
            ],
        }

    def _determine_confidence(self, score: float, min_confidence: float) -> MatchConfidence:
        """Determine confidence level from score.

        Args:
            score: Match score (0.0-1.0)
            min_confidence: Minimum threshold for acceptance

        Returns:
            Confidence level
        """
        if score >= _CONFIDENCE_HIGH_THRESHOLD:
            return MatchConfidence.HIGH
        elif score >= _CONFIDENCE_MEDIUM_THRESHOLD:
            return MatchConfidence.MEDIUM
        elif score >= _CONFIDENCE_LOW_THRESHOLD:
            return MatchConfidence.LOW
        elif score >= min_confidence:
            return MatchConfidence.LOW
        else:
            return MatchConfidence.NONE
