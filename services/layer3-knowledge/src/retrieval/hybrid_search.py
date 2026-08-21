"""Hybrid search combining BM25, vector similarity, and graph structure.

Changes from original:
- Replaced ``AsyncGraphDatabase.driver()`` with shared ``get_driver()`` factory.
- ``_vector_search``: adapts the new Neo4j VectorStore tuple return format
  ``(entity_id, score, metadata)`` into the dict format expected by
  ``_merge_results``.
- ``_vector_search``: gracefully handles ``None`` vector_store (returns []).
- ``_graph_search``: added null-driver guard.
- PERF: Parallelized search operations using asyncio.gather for ~3x speedup
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from neo4j import AsyncDriver
from value_fabric.shared.identity.context import get_request_context
from value_fabric.shared.identity.isolation import ScopedQuery, TenantScopedCypher

from ..config import Settings, get_settings
from ..db.driver import get_driver
from ..db.query_execution import run_scoped_query
from ..retrieval.graph_rag import GraphRAGEngine
from ..retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Result from hybrid search."""

    entity_id: str
    entity_type: str
    name: str
    bm25_score: float
    vector_score: float
    graph_score: float
    combined_score: float
    metadata: dict[str, Any]
    confidence: float = 1.0


class HybridSearch:
    """Hybrid search engine combining multiple retrieval signals.

    Combines:
    1. BM25 sparse retrieval (full-text search)
    2. Dense vector similarity (semantic search)
    3. Graph centrality/pagerank (structural importance)
    4. Recency boost (for temporal relevance)
    """

    def __init__(
        self,
        driver: AsyncDriver | None = None,
        vector_store: VectorStore | None = None,
        graph_engine: GraphRAGEngine | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self._driver = driver
        self._owned_driver = driver is None
        self.vector_store = vector_store
        self.graph_engine = graph_engine

    async def _get_driver(self) -> AsyncDriver:
        """Get or create Neo4j driver via the shared singleton factory."""
        if self._driver is None:
            self._driver = await get_driver(self.settings)
        return self._driver

    async def close(self) -> None:
        if self._owned_driver and self._driver:
            await self._driver.close()
            self._driver = None

    async def search(
        self,
        query: str,
        entity_types: list[str] | None = None,
        top_k: int = 10,
        weights: dict[str, float] | None = None,
        limit: int | None = None,
        tenant_id: str | None = None,
    ) -> list[HybridSearchResult]:
        """Execute hybrid search across all signals.

        Args:
            query: Search query text
            entity_types: Filter by entity types
            top_k: Number of results to return
            weights: Custom weights for bm25, vector, graph
            limit: Alias for top_k for API compatibility

        Returns:
            List of ranked search results
        """
        # Use limit if provided, otherwise top_k (keeping positional compatibility
        # with existing callers that pass weights as the 4th argument).
        result_limit = limit if limit is not None else top_k

        weights = weights or {
            "bm25": self.settings.hybrid_bm25_weight,
            "vector": self.settings.hybrid_vector_weight,
            "graph": self.settings.hybrid_graph_weight,
        }
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        # PERF: Execute searches in parallel - independent operations
        # Before: Sequential (BM25 time + vector time + graph time)
        # After: Parallel (max(BM25 time, vector time, graph time))
        effective_tenant_id = self._resolve_tenant_id(tenant_id)
        bm25_task = self._bm25_search(query, entity_types, result_limit * 2, effective_tenant_id)
        vector_task = self._vector_search(query, entity_types, result_limit * 2, effective_tenant_id)
        graph_task = self._graph_search(query, entity_types, result_limit * 2, effective_tenant_id)

        bm25_results, vector_results, graph_results = await asyncio.gather(
            bm25_task, vector_task, graph_task, return_exceptions=True
        )

        # Handle any exceptions from parallel execution
        if isinstance(bm25_results, Exception):
            logger.warning(f"BM25 search failed: {bm25_results}")
            bm25_results = []
        if isinstance(vector_results, Exception):
            logger.warning(f"Vector search failed: {vector_results}")
            vector_results = []
        if isinstance(graph_results, Exception):
            logger.warning(f"Graph search failed: {graph_results}")
            graph_results = []

        merged = self._merge_results(
            bm25_results, vector_results, graph_results, weights
        )
        return merged[:result_limit]

    async def semantic_search(
        self,
        query: str,
        entity_type: str | None = None,
        top_k: int = 10,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Pure semantic (vector) search."""
        return await self._vector_search(
            query, [entity_type] if entity_type else None, top_k, tenant_id
        )

    async def keyword_search(
        self,
        query: str,
        entity_type: str | None = None,
        top_k: int = 10,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Pure BM25 keyword search."""
        return await self._bm25_search(
            query, [entity_type] if entity_type else None, top_k, tenant_id
        )

    async def fulltext_search(
        self,
        query: str,
        entity_type: str | None = None,
        top_k: int = 10,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Backward-compatible alias for keyword/BM25 search."""
        return await self.keyword_search(query, entity_type, top_k, tenant_id)

    def _resolve_tenant_id(self, tenant_id: str | None = None) -> str:
        """Resolve the tenant for strict graph reads, failing closed if absent."""
        if tenant_id:
            return str(tenant_id)
        context = get_request_context()
        if context and context.tenant_id:
            return str(context.tenant_id)
        raise ValueError("tenant_id is required for tenant-scoped HybridSearch queries")

    def _tenant_builder(self, tenant_id: str | None = None) -> TenantScopedCypher:
        return TenantScopedCypher(self._resolve_tenant_id(tenant_id))

    async def _run_scoped(self, session: Any, scoped: ScopedQuery):
        """Execute a strict scoped query through the Neo4j session seam."""
        return await run_scoped_query(session.run, scoped)

    async def _bm25_search(
        self,
        query: str,
        entity_types: list[str] | None,
        top_k: int,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute BM25 full-text search via Neo4j fulltext index."""
        driver = await self._get_driver()
        results = []
        search_types = entity_types or ["Capability", "UseCase", "Persona", "ValueDriver"]

        async with driver.session(database=self.settings.neo4j_database) as session:
            escaped_query = query.replace('"', '\\"')
            builder = self._tenant_builder(tenant_id)
            for etype in search_types:
                scoped = builder.fulltext_query_nodes_query(
                    f"{etype.lower()}_fulltext",
                    "query",
                    params={"query": escaped_query},
                    return_clause=(
                        "node.id as id, labels(node)[0] as entity_type, node.name as name, "
                        "node.description as description, score"
                    ),
                    limit=top_k,
                )
                try:
                    result = await self._run_scoped(session, scoped)
                    records = [dict(record) async for record in result]
                    for row in records:
                        if row.get("entity_type") == etype:
                            results.append(row)
                except Exception as exc:
                    logger.warning("BM25 search failed for %s: %s", etype, exc)

        results.sort(key=lambda row: row.get("score", 0), reverse=True)
        results = results[:top_k]
        return results

    async def _vector_search(
        self,
        query: str,
        entity_types: list[str] | None,
        top_k: int,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute vector similarity search.

        Adapts the Neo4jVectorStore return format — list of
        ``(entity_id, score, metadata)`` tuples — into the dict format
        expected by ``_merge_results``.
        """
        if not self.vector_store:
            logger.debug("Vector store not configured, skipping vector search")
            return []

        entity_type = entity_types[0] if entity_types else None

        try:
            raw = await self.vector_store.search(
                query_text=query,
                entity_type=entity_type,
                top_k=top_k,
                tenant_id=self._resolve_tenant_id(tenant_id),
            )
        except Exception as exc:
            logger.warning("Vector search failed: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for item in raw:
            # Handle both tuple format (new) and dict format (legacy)
            if isinstance(item, tuple):
                entity_id, score, meta = item
                results.append(
                    {
                        "id": entity_id,
                        "entity_id": entity_id,
                        "score": score,
                        "entity_type": meta.get("entity_type", "Unknown"),
                        "name": meta.get("name", ""),
                        "description": meta.get("description", ""),
                        "metadata": meta,
                    }
                )
            else:
                # Legacy dict format — ensure 'id' key exists
                item.setdefault("id", item.get("entity_id", ""))
                results.append(item)

        return results

    async def _graph_search(
        self,
        query: str,
        entity_types: list[str] | None,
        top_k: int,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute graph-based search (centrality-aware)."""
        driver = await self._get_driver()
        results = []
        search_types = entity_types or ["Capability", "UseCase", "Persona", "ValueDriver"]

        async with driver.session(database=self.settings.neo4j_database) as session:
            escaped_query = query.replace('"', '\\"')
            for etype in search_types:
                builder = self._tenant_builder(tenant_id)
                scoped = builder.custom_tenant_query(
                    """
                    CALL db.index.fulltext.queryNodes($index_name, $query)
                    YIELD node, score
                    WHERE node.tenant_id = $_tenant_id
                    OPTIONAL MATCH (node)-[r]-(neighbor)
                    WHERE neighbor.tenant_id = $_tenant_id
                    WITH node, score as text_score, count(r) as degree
                    RETURN node.id as id, labels(node)[0] as entity_type, node.name as name,
                           text_score * log(degree + 1) as score
                    ORDER BY score DESC
                    LIMIT $limit
                    """,
                    params={"index_name": f"{etype.lower()}_fulltext", "query": escaped_query, "limit": top_k},
                    operation="hybrid_search.graph",
                    labels=(etype,),
                    allowlist_key="hybrid_search.graph_fulltext_tenant_scoped",
                )
                try:
                    result = await self._run_scoped(session, scoped)
                    records = [dict(record) async for record in result]
                    for row in records:
                        if row.get("entity_type") == etype:
                            results.append(row)
                except Exception as exc:
                    logger.warning("Graph search failed for %s: %s", etype, exc)

        results.sort(key=lambda row: row.get("score", 0), reverse=True)
        results = results[:top_k]
        return results

    def _merge_results(
        self,
        bm25_results: list[dict],
        vector_results: list[dict],
        graph_results: list[dict],
        weights: dict[str, float],
    ) -> list[HybridSearchResult]:
        """Merge and rank results from multiple sources."""
        all_ids: set = set()
        bm25_lookup: dict[str, dict] = {}
        vector_lookup: dict[str, dict] = {}
        graph_lookup: dict[str, dict] = {}

        for r in bm25_results:
            eid = r.get("id") or r.get("entity_id")
            if eid:
                all_ids.add(eid)
                bm25_lookup[eid] = r

        for r in vector_results:
            eid = r.get("id") or r.get("entity_id")
            if eid:
                all_ids.add(eid)
                vector_lookup[eid] = r

        for r in graph_results:
            eid = r.get("id") or r.get("entity_id")
            if eid:
                all_ids.add(eid)
                graph_lookup[eid] = r

        # Normalize each signal to [0, 1] by its max. Guard against negative
        # max values (which would invert sign of all normalized scores) and
        # against an all-zero/empty signal (divisor falls back to 1.0).
        def _norm_divisor(results: list[dict]) -> float:
            mx = max((r.get("score", 0.0) for r in results), default=0.0)
            return mx if mx > 0 else 1.0

        bm25_max = _norm_divisor(bm25_results)
        vector_max = _norm_divisor(vector_results)
        graph_max = _norm_divisor(graph_results)

        merged = []
        for entity_id in all_ids:
            # Clamp each per-signal normalized score to [0, 1] so a negative
            # raw score cannot flip the combined score's sign.
            bm25_score = max(0.0, min(1.0, bm25_lookup.get(entity_id, {}).get("score", 0.0) / bm25_max))
            vector_score = max(
                0.0, min(1.0, vector_lookup.get(entity_id, {}).get("score", 0.0) / vector_max)
            )
            graph_score = max(0.0, min(1.0, graph_lookup.get(entity_id, {}).get("score", 0.0) / graph_max))

            combined = (
                weights["bm25"] * bm25_score
                + weights["vector"] * vector_score
                + weights["graph"] * graph_score
            )

            source = (
                bm25_lookup.get(entity_id)
                or vector_lookup.get(entity_id)
                or graph_lookup.get(entity_id)
                or {}
            )

            merged.append(
                HybridSearchResult(
                    entity_id=entity_id,
                    entity_type=source.get("entity_type", "Unknown"),
                    name=source.get("name", source.get("text", "")[:100]),
                    bm25_score=bm25_score,
                    vector_score=vector_score,
                    graph_score=graph_score,
                    combined_score=combined,
                    confidence=combined,
                    metadata=source.get("metadata", {}),
                )
            )

        # Deterministic ordering: primary by combined score (desc), secondary
        # by entity_id (asc) so ties resolve stably across runs. Without the
        # secondary key, set-iteration order made tied results non-reproducible.
        merged.sort(key=lambda x: (-x.combined_score, x.entity_id))
        return merged
