from __future__ import annotations

"""Evidence vector search service for Layer 3.

Provides semantic search capabilities to match pain signals
against evidence sources (case studies, benchmarks, etc.).
"""


import asyncio
import logging
from functools import lru_cache
from typing import Any

from neo4j import AsyncDriver

from ..config.embedding_dimension import validate_embedding_dimension
from ..db.query_execution import run_validated_query
from .embedding_errors import EmbeddingProviderUnavailableError

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def _get_embedding_model():
    """Load and cache the sentence-transformers model.

    Uses the EMBEDDING_MODEL setting (default: sentence-transformers/all-MiniLM-L6-v2).
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Install it to use real embeddings."
        ) from exc
    from config import get_settings

    settings = get_settings()
    return SentenceTransformer(settings.embedding_model)
class EvidenceSearchService:
    """Service for evidence matching using vector similarity.

    Searches case studies, benchmarks, and other evidence sources
    to find supporting material for pain signals.
    """

    def __init__(self, driver: AsyncDriver):
        """Initialize with Neo4j driver.

        Args:
            driver: Neo4j async driver instance
        """
        self._driver = driver

    async def find_matching_evidence(
        self,
        tenant_id: str,
        signal_description: str,
        industry: str | None = None,
        evidence_types: list[str] | None = None,
        limit: int = 5,
        min_score: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Find evidence matching a signal description.

        Uses vector similarity search to find relevant case studies,
        benchmarks, and ROI calculators.

        Args:
            signal_description: Signal text to match against
            industry: Optional industry filter
            limit: Maximum results to return
            min_score: Minimum similarity score (0.0-1.0)

        Returns:
            List of evidence matches with scores and reasoning
        """
        # Generate embedding for the signal description
        # In production, this would call an embedding service
        signal_embedding = await self._generate_embedding(signal_description)

        async with self._driver.session() as session:
            if industry:
                # Filter by industry and similarity
                query = """
                CALL db.index.vector.queryNodes(
                    'evidence_embedding_idx',
                    $limit * 2,
                    $embedding
                ) YIELD node, score
                WHERE node.tenant_id = $tenant_id
                  AND node.industry = $industry
                  AND score >= $min_score
                RETURN node.id as evidence_id,
                       node.evidence_type as evidence_type,
                       node.title as title,
                       node.industry as industry,
                       score as similarity_score
                ORDER BY score DESC
                LIMIT $limit
                """
                params = {
                    "embedding": signal_embedding,
                    "tenant_id": tenant_id,
                    "industry": industry,
                    "min_score": min_score,
                    "limit": limit,
                }
            else:
                # Search across all industries
                query = """
                CALL db.index.vector.queryNodes(
                    'evidence_embedding_idx',
                    $limit * 2,
                    $embedding
                ) YIELD node, score
                WHERE node.tenant_id = $tenant_id
                  AND score >= $min_score
                  AND ($evidence_types IS NULL OR node.evidence_type IN $evidence_types)
                RETURN node.id as evidence_id,
                       node.evidence_type as evidence_type,
                       node.title as title,
                       node.industry as industry,
                       score as similarity_score
                ORDER BY score DESC
                LIMIT $limit
                """
                params = {
                    "embedding": signal_embedding,
                    "tenant_id": tenant_id,
                    "evidence_types": evidence_types,
                    "min_score": min_score,
                    "limit": limit,
                }

            result = await run_validated_query(
                session,
                query,
                params,
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="evidence_search.find_matching_evidence",
            )
            records = await result.data()

            # Transform to match schema and add reasoning
            matches = []
            for record in records:
                match = {
                    "evidence_id": record["evidence_id"],
                    "evidence_type": record["evidence_type"],
                    "title": record["title"],
                    "match_score": int(record["similarity_score"] * 100),  # Convert to 0-100
                    "match_reasoning": self._generate_reasoning(
                        signal_description,
                        record["title"],
                        record["similarity_score"],
                    ),
                    "relevance_quote": None,  # Would be populated from evidence content
                }
                matches.append(match)

            return matches

    async def search_by_keywords(
        self,
        tenant_id: str,
        keywords: list[str],
        evidence_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search evidence by keywords using full-text index.

        Args:
            keywords: Search terms
            evidence_types: Optional filter by evidence type
            limit: Maximum results

        Returns:
            List of matching evidence
        """
        # Build full-text search query
        search_terms = " OR ".join(keywords)

        async with self._driver.session() as session:
            if evidence_types:
                query = """
                CALL db.index.fulltext.queryNodes(
                    'evidence_fulltext',
                    $search_terms
                ) YIELD node, score
                WHERE node.tenant_id = $tenant_id
                  AND node.evidence_type IN $evidence_types
                RETURN node.id as evidence_id,
                       node.evidence_type as evidence_type,
                       node.title as title,
                       score as relevance
                ORDER BY score DESC
                LIMIT $limit
                """
                params = {
                    "search_terms": search_terms,
                    "tenant_id": tenant_id,
                    "evidence_types": evidence_types,
                    "limit": limit,
                }
            else:
                query = """
                CALL db.index.fulltext.queryNodes(
                    'evidence_fulltext',
                    $search_terms
                ) YIELD node, score
                WHERE node.tenant_id = $tenant_id
                RETURN node.id as evidence_id,
                       node.evidence_type as evidence_type,
                       node.title as title,
                       score as relevance
                ORDER BY score DESC
                LIMIT $limit
                """
                params = {
                    "search_terms": search_terms,
                    "tenant_id": tenant_id,
                    "limit": limit,
                }

            result = await run_validated_query(
                session,
                query,
                params,
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="evidence_search.search_by_keywords",
            )
            records = await result.data()

            return [
                {
                    "evidence_id": r["evidence_id"],
                    "evidence_type": r["evidence_type"],
                    "title": r["title"],
                    "match_score": int(r["relevance"] * 100),
                    "match_reasoning": f"Matched by keywords: {', '.join(keywords)}",
                    "relevance_quote": None,
                }
                for r in records
            ]

    async def get_evidence_details(
        self,
        tenant_id: str,
        evidence_id: str,
    ) -> dict[str, Any] | None:
        """Get detailed information about an evidence item.

        Args:
            evidence_id: Evidence identifier

        Returns:
            Evidence details or None if not found
        """
        async with self._driver.session() as session:
            query = """
            MATCH (e:Evidence {id: $evidence_id, tenant_id: $tenant_id})
            RETURN e {
                id: e.id,
                evidence_type: e.evidence_type,
                title: e.title,
                description: e.description,
                industry: e.industry,
                content: e.content,
                source_url: e.source_url,
                created_at: e.created_at
            } as evidence
            """

            result = await run_validated_query(
                session,
                query,
                {"evidence_id": evidence_id, "tenant_id": tenant_id},
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="evidence_search.get_evidence_details",
            )
            record = await result.single()
            return record["evidence"] if record else None

    async def index_evidence(
        self,
        tenant_id: str,
        evidence_data: dict[str, Any],
        content_embedding: list[float],
    ) -> str:
        """Index new evidence for search.

        Creates an Evidence node with vector embedding.

        Args:
            evidence_data: Evidence metadata
            content_embedding: Pre-computed embedding vector

        Returns:
            Evidence ID
        """
        evidence_id = evidence_data.get("id")

        async with self._driver.session() as session:
            query = """
            MERGE (e:Evidence {id: $evidence_id, tenant_id: $tenant_id})
            SET e.evidence_type = $evidence_type,
                e.title = $title,
                e.description = $description,
                e.industry = $industry,
                e.content = $content,
                e.source_url = $source_url,
                e.embedding = $embedding,
                e.created_at = datetime()
            RETURN e.id as evidence_id
            """

            result = await run_validated_query(
                session,
                query,
                {
                    "evidence_id": evidence_id,
                    "tenant_id": tenant_id,
                    "evidence_type": evidence_data.get("evidence_type", "case_study"),
                    "title": evidence_data.get("title", ""),
                    "description": evidence_data.get("description", ""),
                    "industry": evidence_data.get("industry"),
                    "content": evidence_data.get("content", ""),
                    "source_url": evidence_data.get("source_url"),
                    "embedding": content_embedding,
                },
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="evidence_search.index_evidence",
            )
            record = await result.single()
            return record["evidence_id"] if record else evidence_id

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text using sentence-transformers.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (384 dimensions)
        """
        try:
            model = _get_embedding_model()
            embedding = await asyncio.to_thread(model.encode, text)
            embedding_list = embedding.tolist()
            from ..config import get_settings

            validate_embedding_dimension(
                configured_dimension=get_settings().embedding_dimension,
                model=model,
                model_name=get_settings().embedding_model,
            )
            if len(embedding_list) != get_settings().embedding_dimension:
                raise ValueError(
                    f"VECTOR_DIMENSION_MISMATCH: expected={get_settings().embedding_dimension} actual={len(embedding_list)}"
                )
            return embedding_list
        except Exception as exc:
            raise EmbeddingProviderUnavailableError(
                "Embedding provider unavailable",
                provider="sentence-transformers",
                failure_cause=exc.__class__.__name__,
                retry_after_seconds=30,
                retry_hint="retry_with_backoff",
            ) from exc

    def _generate_reasoning(
        self,
        signal_description: str,
        evidence_title: str,
        similarity_score: float,
    ) -> str:
        """Generate human-readable reasoning for evidence match.

        Args:
            signal_description: Signal text
            evidence_title: Evidence title
            similarity_score: Similarity score

        Returns:
            Reasoning string
        """
        if similarity_score >= 0.9:
            return (
                f"Very high semantic match ({similarity_score:.0%}) between signal "
                f"and evidence '{evidence_title}'. Content addresses same operational domain."
            )
        elif similarity_score >= 0.8:
            return (
                f"Strong semantic match ({similarity_score:.0%}) with evidence "
                f"'{evidence_title}'. Relevant case study for similar pain."
            )
        elif similarity_score >= 0.7:
            return (
                f"Moderate semantic match ({similarity_score:.0%}) with "
                f"'{evidence_title}'. Provides supporting context."
            )
        else:
            return (
                f"Partial match ({similarity_score:.0%}) with '{evidence_title}'. "
                f"May provide indirect relevance."
            )
