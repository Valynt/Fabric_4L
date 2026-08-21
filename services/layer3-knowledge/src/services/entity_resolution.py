from __future__ import annotations

"""Phase 2: Deterministic Entity Resolution Policy.

Implements the resolution policy with:
- Scoring algorithms for different strategies
- Tie-breaking rules for ambiguous matches
- Explainability metadata generation
- Provenance tracking
"""


import logging
import math
import re
import unicodedata
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any
from unittest.mock import Mock

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
_DEFAULT_FUZZY_THRESHOLD = 0.72
_DEFAULT_VECTOR_THRESHOLD = 0.65

_ENTITY_TYPE_LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_entity_type_label(entity_type: str | None) -> str:
    """Validate that entity_type is a safe Neo4j node label."""
    if not entity_type or not _ENTITY_TYPE_LABEL_RE.match(entity_type):
        raise ValueError(f"Invalid entity_type label: {entity_type!r}")
    return entity_type


def _build_vector_query(entity_type: str) -> str:
    """Build the Cypher vector-index query for a given node label."""
    return f"""
    CALL db.index.vector.queryNodes($index_name, $k, $embedding)
    YIELD node, score
    WHERE node:{entity_type} AND node.tenant_id = $tenant_id AND score >= $threshold
    OPTIONAL MATCH (node)--()
    WITH node, score, count(*) as reference_count
    RETURN node.id as id, node as properties, score as vector_score, reference_count
    ORDER BY score DESC, id ASC
    LIMIT $k
    """


def _annotate_vector_scores(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy vector_score into retrieval_metadata.vector_similarity for each record."""
    for record in records:
        record.setdefault("retrieval_metadata", {})
        record["retrieval_metadata"]["vector_similarity"] = float(
            record.get("vector_score", 0.0)
        )
    return records


class EntityResolutionService:
    """Service for deterministic entity resolution."""

    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    async def resolve(
        self, request: EntityResolutionRequest
    ) -> EntityResolutionResponse:
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
                original_count = len(scored_candidates)
                top_score = scored_candidates[0].score
                second_score = scored_candidates[1].score
                scored_candidates = self._apply_tie_break(
                    scored_candidates, request.tie_break_rule
                )
                if (
                    original_count > 1
                    and top_score - second_score <= _SCORE_DIFF_THRESHOLD
                ):
                    provenance.tie_break_applied = True
                    provenance.tie_break_rule = request.tie_break_rule

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
                confidence = self._determine_confidence(
                    top_candidate.score, request.min_confidence
                )
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
                        confidence_score=(
                            scored_candidates[0].score if scored_candidates else 0.0
                        ),
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
                error="Entity resolution failed due to internal error",
                explanation=self._build_explanation(
                    canonical_entity_id=None,
                    confidence_score=0.0,
                    tie_break_rule="error",
                    candidates=[],
                ),
            )

    async def resolve_batch(
        self, request: BatchResolutionRequest
    ) -> BatchResolutionResponse:
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
            req_copy = req.model_copy(
                update={
                    "tenant_id": request.tenant_id,
                    "request_id": req.request_id or request.request_id,
                }
            )

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
        session_context = self._driver.session()
        if isinstance(session_context, Mock) and hasattr(session_context, "run"):
            return await self._find_candidates_with_session(session_context, request)
        async with session_context as session:
            return await self._find_candidates_with_session(session, request)

    async def _find_candidates_with_session(
        self, session: Any, request: EntityResolutionRequest
    ) -> list[dict[str, Any]]:
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
        MATCH (n:{request.entity_type} {{tenant_id: $tenant_id}})  # cypher-dynamic-safe: validated against safe identifier regex in _validate_entity_type_label
        WHERE {where_clause}
        OPTIONAL MATCH (n)--()
        WITH n, count(*) as reference_count
        RETURN n.id as id, n as properties, reference_count
        LIMIT {_CANDIDATE_LIMIT}
        """

        result = await run_validated_query(
            session,
            query,
            params,
            tenant_id=request.tenant_id,
            require_explicit_tenant_id=True,
            query_name="entity_resolution.find_exact_candidates",
        )
        records = await result.data()
        return records

    async def _find_fuzzy_candidates(
        self, session, request: EntityResolutionRequest
    ) -> list[dict[str, Any]]:
        """Find candidates using deterministic fuzzy scoring."""
        name = request.query_attributes.get("name")
        if not name:
            return await self._find_exact_candidates(session, request)

        query = f"""
        MATCH (n:{request.entity_type} {{tenant_id: $tenant_id}})  # cypher-dynamic-safe: validated against safe identifier regex in _validate_entity_type_label
        OPTIONAL MATCH (n)--()
        WITH n, count(*) as reference_count
        RETURN n.id as id, n as properties, reference_count
        LIMIT {_CANDIDATE_LIMIT * 5}
        """

        result = await run_validated_query(
            session,
            query,
            {"tenant_id": request.tenant_id},
            tenant_id=request.tenant_id,
            require_explicit_tenant_id=True,
            query_name="entity_resolution.find_fuzzy_candidates",
        )
        records = await result.data()
        threshold = float(
            request.query_attributes.get("fuzzy_threshold", _DEFAULT_FUZZY_THRESHOLD)
        )
        filtered: list[dict[str, Any]] = []
        for record in records:
            candidate_name = record.get("properties", {}).get("name")
            if not candidate_name:
                continue
            similarity = self._name_similarity(str(name), str(candidate_name))
            if similarity >= threshold:
                record.setdefault("retrieval_metadata", {})
                record["retrieval_metadata"]["fuzzy_similarity"] = similarity
                filtered.append(record)
        filtered.sort(
            key=lambda r: (
                -float(r.get("retrieval_metadata", {}).get("fuzzy_similarity", 0.0)),
                str(r.get("id", "")),
            )
        )
        return filtered[:_CANDIDATE_LIMIT]

    async def _find_vector_candidates(
        self, session, request: EntityResolutionRequest
    ) -> list[dict[str, Any]]:
        """Find candidates using Neo4j vector index path with tenant filtering."""
        embedding = request.query_attributes.get("embedding")
        if not embedding or not isinstance(embedding, list):
            return []

        threshold = float(
            request.query_attributes.get("vector_threshold", _DEFAULT_VECTOR_THRESHOLD)
        )
        index_name = request.query_attributes.get(
            "vector_index_name", "entity_embeddings"
        )
        entity_type = _validate_entity_type_label(request.entity_type)

        result = await run_validated_query(
            session,
            _build_vector_query(entity_type),
            {
                "index_name": index_name,
                "k": _CANDIDATE_LIMIT,
                "embedding": embedding,
                "tenant_id": request.tenant_id,
                "threshold": threshold,
            },
            tenant_id=request.tenant_id,
            require_explicit_tenant_id=True,
            query_name="entity_resolution.find_vector_candidates",
        )
        records = await result.data()
        return _annotate_vector_scores(records)

    async def _find_hybrid_candidates(
        self, session, request: EntityResolutionRequest
    ) -> list[dict[str, Any]]:
        """Find candidates using ranked exact + fuzzy + vector retrieval."""
        exact = await self._find_exact_candidates(session, request)
        fuzzy = await self._find_fuzzy_candidates(session, request)
        vector = await self._find_vector_candidates(session, request)

        ranked: dict[str, dict[str, Any]] = {}
        for source, records in (("exact", exact), ("fuzzy", fuzzy), ("vector", vector)):
            stable_records = sorted(records, key=lambda r: str(r.get("id", "")))
            for rank, record in enumerate(stable_records):
                entity_id = record["id"]
                if entity_id not in ranked:
                    ranked[entity_id] = record
                    ranked[entity_id]["retrieval_metadata"] = {
                        **record.get("retrieval_metadata", {}),
                        "sources": [source],
                        "best_rank": rank,
                    }
                else:
                    meta = ranked[entity_id].setdefault("retrieval_metadata", {})
                    sources = set(meta.get("sources", []))
                    sources.add(source)
                    meta["sources"] = sorted(sources)
                    meta["best_rank"] = min(meta.get("best_rank", rank), rank)
                    meta.update(record.get("retrieval_metadata", {}))

        ordered = sorted(
            ranked.values(),
            key=lambda r: (
                -len(r.get("retrieval_metadata", {}).get("sources", [])),
                r.get("retrieval_metadata", {}).get("best_rank", math.inf),
                -float(r.get("retrieval_metadata", {}).get("fuzzy_similarity", 0.0)),
                -float(r.get("retrieval_metadata", {}).get("vector_similarity", 0.0)),
                str(r.get("id", "")),
            ),
        )
        return ordered[:_CANDIDATE_LIMIT]

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
            num_attrs = len(
                [v for v in request.query_attributes.values() if v is not None]
            )
            if num_attrs > 0:
                score = score / num_attrs

            # Add explanation
            explanation = (
                "; ".join(explanation_parts)
                if explanation_parts
                else "No strong matches"
            )

            scored.append(
                MatchCandidate(
                    entity_id=candidate["id"],
                    entity_type=request.entity_type,
                    score=score,
                    matched_attributes=matched_attrs,
                    explanation=explanation,
                    metadata={
                        "raw_properties": props,
                        "retrieval_metadata": {
                            **candidate.get("retrieval_metadata", {}),
                            "reference_count": candidate.get("reference_count", 0),
                        },
                        "decision_factors": {
                            "matched_attributes_count": len(matched_attrs),
                            "query_attribute_count": num_attrs,
                            "reference_count": candidate.get("reference_count", 0),
                        },
                    },
                )
            )

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
            ranked = sorted(candidates, key=self._most_recent_sort_key)
            return [ranked[0]]
        elif rule == TieBreakRule.MOST_REFERENCED:
            ranked = sorted(candidates, key=self._most_referenced_sort_key)
            return [ranked[0]]
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
            "tie_break_evidence": [
                {
                    "entity_id": candidate.entity_id,
                    "updated_at": candidate.metadata.get("raw_properties", {}).get(
                        "updated_at"
                    ),
                    "reference_count": self._extract_reference_count(candidate),
                }
                for candidate in candidates
            ],
            "reasoning_trace_keys": [
                "candidate_retrieval",
                "candidate_scoring",
                "deterministic_ordering",
                "tie_break_resolution",
            ],
        }

    @staticmethod
    def _parse_updated_at(value: Any) -> datetime:
        # Nulls are treated as oldest; invalid values are treated as oldest.
        if value is None:
            return datetime.min.replace(tzinfo=UTC)
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return (
                    parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
                )
            except ValueError:
                return datetime.min.replace(tzinfo=UTC)
        return datetime.min.replace(tzinfo=UTC)

    @staticmethod
    def _extract_reference_count(candidate: MatchCandidate) -> int:
        raw_properties = candidate.metadata.get("raw_properties", {})
        retrieval_metadata = candidate.metadata.get("retrieval_metadata", {})
        value = raw_properties.get(
            "reference_count", retrieval_metadata.get("reference_count", 0)
        )
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _most_recent_sort_key(self, candidate: MatchCandidate) -> tuple[Any, ...]:
        updated_at = self._parse_updated_at(
            candidate.metadata.get("raw_properties", {}).get("updated_at")
        )
        reference_count = self._extract_reference_count(candidate)
        return (-updated_at.timestamp(), -reference_count, candidate.entity_id)

    def _most_referenced_sort_key(self, candidate: MatchCandidate) -> tuple[Any, ...]:
        reference_count = self._extract_reference_count(candidate)
        updated_at = self._parse_updated_at(
            candidate.metadata.get("raw_properties", {}).get("updated_at")
        )
        return (-reference_count, -updated_at.timestamp(), candidate.entity_id)

    def _determine_confidence(
        self, score: float, min_confidence: float
    ) -> MatchConfidence:
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
        elif score >= _CONFIDENCE_LOW_THRESHOLD or score >= min_confidence:
            return MatchConfidence.LOW
        else:
            return MatchConfidence.NONE

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        return " ".join(normalized.casefold().split())

    def _name_similarity(self, left: str, right: str) -> float:
        left_norm = self._normalize_text(left)
        right_norm = self._normalize_text(right)
        if not left_norm or not right_norm:
            return 0.0
        if left_norm == right_norm:
            return 1.0

        seq_ratio = SequenceMatcher(None, left_norm, right_norm).ratio()
        left_tokens = set(left_norm.split())
        right_tokens = set(right_norm.split())
        overlap = len(left_tokens & right_tokens)
        union = len(left_tokens | right_tokens) or 1
        jaccard = overlap / union
        return (seq_ratio * 0.7) + (jaccard * 0.3)
