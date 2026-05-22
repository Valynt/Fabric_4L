"""Entity similarity analysis using graph and vector methods."""

import logging
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase
from value_fabric.shared.identity.context import require_context
from value_fabric.shared.identity.isolation import ScopedQuery, TenantScopedCypher
from value_fabric.shared.models.typed_dict import TypedDictModel

from value_fabric.layer3.config import Settings, get_settings
from ..retrieval.vector_store import VectorStore
from ..db.query_execution import run_validated_query


class SimilarityAnalyzer_compare_entitiesResult(TypedDictModel):
    common_neighbors: Any | None = None
    entity1: dict[str, Any] | None = None
    entity2: dict[str, Any] | None = None
    error: str
    jaccard_similarity: Any | None = None
    path_info: Any | None = None
    same_type: bool | None = None

logger = logging.getLogger(__name__)


class SimilarityAnalyzer:
    """Analyze entity similarity using multiple methods.

    Methods:
    - Jaccard similarity (common neighbors)
    - Adamic-Adar (weighted common neighbors)
    - Preferential attachment
    - Vector similarity (via vector store)
    - Path similarity (common paths in value tree)
    """

    def __init__(
        self,
        driver: AsyncDriver | None = None,
        vector_store: VectorStore | None = None,
        settings: Settings | None = None,
    ):
        """Initialize similarity analyzer.

        Args:
            driver: Neo4j async driver
            vector_store: Vector store for semantic similarity
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self._driver = driver
        self._owned_driver = driver is None
        self.vector_store = vector_store

    def _resolve_tenant_id(self, tenant_id: str | None = None) -> str:
        """Return the explicit or request-context tenant id, failing closed if absent."""
        if tenant_id:
            return str(tenant_id)
        context = require_context()
        if not context.tenant_id:
            raise RuntimeError("Tenant-scoped similarity analytics require tenant_id")
        return str(context.tenant_id)

    @staticmethod
    def _query_tuple(scoped_query: ScopedQuery) -> tuple[str, dict[str, Any]]:
        """Expose strict scoped-query execution metadata while preserving session.run compatibility."""
        # strict-scoped-query-execution: callers pass only builder-created tenant-scoped query objects.
        return scoped_query.as_tuple()

    def _builder(self, tenant_id: str | None = None) -> TenantScopedCypher:
        return TenantScopedCypher(self._resolve_tenant_id(tenant_id))

    async def _get_driver(self) -> AsyncDriver:
        """Get or create Neo4j driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=self.settings.neo4j_auth,
                max_connection_pool_size=self.settings.neo4j_max_pool_size,
            )
        return self._driver

    async def close(self) -> None:
        """Close Neo4j driver if owned."""
        if self._owned_driver and self._driver:
            await self._driver.close()
            self._driver = None

    async def find_similar(
        self,
        entity_id: str,
        method: str = "combined",
        top_k: int = 10,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar entities using specified method.

        Args:
            entity_id: Entity to find similar entities for
            method: Similarity method (jaccard, adamic_adar, vector, path, combined)
            top_k: Number of similar entities to return

        Returns:
            List of similar entities with scores
        """
        if method == "jaccard":
            return await self._jaccard_similarity(entity_id, top_k, tenant_id)
        elif method == "adamic_adar":
            return await self._adamic_adar_similarity(entity_id, top_k, tenant_id)
        elif method == "vector":
            return await self._vector_similarity(entity_id, top_k, tenant_id)
        elif method == "path":
            return await self._path_similarity(entity_id, top_k, tenant_id)
        elif method == "combined":
            return await self._combined_similarity(entity_id, top_k, tenant_id)
        else:
            raise ValueError(f"Unknown similarity method: {method}")

    async def find_similar_by_type(
        self,
        entity_id: str,
        target_type: str,
        top_k: int = 10,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar entities of a specific type.

        Useful for finding similar capabilities, personas, etc.
        """
        driver = await self._get_driver()
        builder = self._builder(tenant_id)

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Get vector embedding for the source entity
            vector_results = []
            if self.vector_store:
                vector_results = await self.vector_store.search_by_entity_id(
                    entity_id, top_k=top_k * 2, tenant_id=builder.tenant_id
                )
                # Filter by target type
                vector_results = [
                    r for r in vector_results if r.get("entity_type") == target_type
                ][:top_k]

            # Get graph-based similar entities
            graph_query = builder.custom_tenant_query(
                """
                // strict-scoped-query-execution
                // Find entities that share common neighbors within one tenant
                MATCH (source)-[:ENABLES|BENEFITS|DRIVES]-(common)-[:ENABLES|BENEFITS|DRIVES]-(similar)
                WHERE source.id = $entity_id
                  AND source.tenant_id = $_tenant_id
                  AND common.tenant_id = $_tenant_id
                  AND similar.tenant_id = $_tenant_id
                  AND similar.id <> $entity_id
                  AND $target_type IN labels(similar)
                WITH similar, count(common) as common_neighbors,
                     collect(DISTINCT common.name) as shared
                RETURN similar.id as id,
                       similar.name as name,
                       labels(similar)[0] as type,
                       common_neighbors as score,
                       shared
                ORDER BY common_neighbors DESC
                LIMIT $limit
                """,
                params={"entity_id": entity_id, "target_type": target_type, "limit": top_k},
                operation="similarity.find_similar_by_type",
                labels=("Entity", target_type),
            )
            graph_result = await run_validated_query(session, *self._query_tuple(graph_query))

            graph_results = []
            async for record in graph_result:
                graph_results.append(
                    {
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "score": record["score"],
                        "shared_entities": record["shared"],
                        "method": "graph_common_neighbors",
                    }
                )

            # Combine and deduplicate
            seen_ids = set()
            combined = []

            for r in vector_results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    combined.append(
                        {
                            "id": r["id"],
                            "name": r.get("text", "")[:100],
                            "type": target_type,
                            "score": r["score"],
                            "method": "vector",
                        }
                    )

            for r in graph_results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    combined.append(r)

            # Sort by score and limit
            combined.sort(key=lambda x: x["score"], reverse=True)
            return combined[:top_k]

    async def compare_entities(
        self,
        entity_id1: str,
        entity_id2: str,
        tenant_id: str | None = None,
    ) -> dict:
        """Compare two entities and return similarity metrics.

        Args:
            entity_id1: First entity ID
            entity_id2: Second entity ID

        Returns:
            Comparison metrics
        """
        driver = await self._get_driver()
        builder = self._builder(tenant_id)

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Get both entities
            entity_query = builder.custom_tenant_query(
                """
                // strict-scoped-query-execution
                MATCH (e1), (e2)
                WHERE e1.id = $id1 AND e1.tenant_id = $_tenant_id
                  AND e2.id = $id2 AND e2.tenant_id = $_tenant_id
                RETURN e1, e2,
                       labels(e1)[0] as type1,
                       labels(e2)[0] as type2
                """,
                params={"id1": entity_id1, "id2": entity_id2},
                operation="similarity.compare_entities.lookup",
                labels=("Entity",),
            )
            result = await run_validated_query(session, *self._query_tuple(entity_query))
            record = await result.single()

            if not record:
                return SimilarityAnalyzer_compare_entitiesResult.model_validate({"error": "One or both entities not found"})

            e1, e2 = record["e1"], record["e2"]

            # Calculate common neighbors (Jaccard)
            common_query = builder.custom_tenant_query(
                """
                // strict-scoped-query-execution
                MATCH (e1)-[:ENABLES|BENEFITS|DRIVES]-(common),
                      (e2)-[:ENABLES|BENEFITS|DRIVES]-(common)
                WHERE e1.id = $id1 AND e1.tenant_id = $_tenant_id
                  AND e2.id = $id2 AND e2.tenant_id = $_tenant_id
                  AND common.tenant_id = $_tenant_id
                WITH count(DISTINCT common) as common_count
                // strict-scoped-query-execution
                MATCH (e1)-[:ENABLES|BENEFITS|DRIVES]-(all1)
                WHERE e1.id = $id1 AND e1.tenant_id = $_tenant_id
                  AND all1.tenant_id = $_tenant_id
                WITH common_count, count(DISTINCT all1) as e1_neighbors
                // strict-scoped-query-execution
                MATCH (e2)-[:ENABLES|BENEFITS|DRIVES]-(all2)
                WHERE e2.id = $id2 AND e2.tenant_id = $_tenant_id
                  AND all2.tenant_id = $_tenant_id
                RETURN common_count,
                       e1_neighbors,
                       count(DISTINCT all2) as e2_neighbors
                """,
                params={"id1": entity_id1, "id2": entity_id2},
                operation="similarity.compare_entities.common_neighbors",
                labels=("Entity",),
            )
            common_result = await run_validated_query(session, *self._query_tuple(common_query))
            common_record = await common_result.single()

            if common_record:
                common = common_record["common_count"]
                total = (
                    common_record["e1_neighbors"]
                    + common_record["e2_neighbors"]
                    - common
                )
                jaccard = common / total if total > 0 else 0.0
            else:
                jaccard = 0.0
                common = 0

            # Check if connected in value tree
            path_query = builder.custom_tenant_query(
                """
                // strict-scoped-query-execution
                MATCH path = shortestPath(
                    (e1)-[:ENABLES|BENEFITS|DRIVES|CONTRIBUTES_TO*1..10]-(e2)
                )
                WHERE e1.id = $id1 AND e1.tenant_id = $_tenant_id
                  AND e2.id = $id2 AND e2.tenant_id = $_tenant_id
                  AND all(node IN nodes(path) WHERE node.tenant_id = $_tenant_id)
                RETURN length(path) as path_length,
                       [node IN nodes(path) | node.name] as path_names
                """,
                params={"id1": entity_id1, "id2": entity_id2},
                operation="similarity.compare_entities.path",
                labels=("Entity",),
            )
            path_result = await run_validated_query(session, *self._query_tuple(path_query))
            path_record = await path_result.single()

            path_info = {
                "connected": path_record is not None,
                "path_length": path_record["path_length"] if path_record else None,
                "path_nodes": path_record["path_names"] if path_record else [],
            }

            return SimilarityAnalyzer_compare_entitiesResult.model_validate({
                "entity1": {
                    "id": entity_id1,
                    "name": e1.get("name", "Unknown"),
                    "type": record["type1"],
                },
                "entity2": {
                    "id": entity_id2,
                    "name": e2.get("name", "Unknown"),
                    "type": record["type2"],
                },
                "same_type": record["type1"] == record["type2"],
                "jaccard_similarity": jaccard,
                "common_neighbors": common,
                "path_info": path_info,
            })


    async def _jaccard_similarity(self, entity_id: str, top_k: int, tenant_id: str | None = None) -> list[dict]:
        """Calculate Jaccard similarity based on common neighbors."""
        driver = await self._get_driver()
        builder = self._builder(tenant_id)

        async with driver.session(database=self.settings.neo4j_database) as session:
            query = builder.custom_tenant_query(
                """
                // strict-scoped-query-execution
                // Get source entity's neighbors
                MATCH (source)-[:ENABLES|BENEFITS|DRIVES]-(neighbor)
                WHERE source.id = $entity_id
                  AND source.tenant_id = $_tenant_id
                  AND neighbor.tenant_id = $_tenant_id
                WITH source, collect(DISTINCT neighbor) as source_neighbors, count(neighbor) as source_count
                // Find other entities with shared neighbors
                // strict-scoped-query-execution
                MATCH (other)-[:ENABLES|BENEFITS|DRIVES]-(shared)
                WHERE other.id <> $entity_id
                  AND other.tenant_id = $_tenant_id
                  AND shared.tenant_id = $_tenant_id
                  AND shared IN source_neighbors
                WITH other, source_neighbors, source_count,
                     collect(DISTINCT shared) as shared_neighbors,
                     count(DISTINCT shared) as shared_count
                // Calculate Jaccard
                // strict-scoped-query-execution
                MATCH (other)-[:ENABLES|BENEFITS|DRIVES]-(other_neighbor)
                WHERE other_neighbor.tenant_id = $_tenant_id
                WITH other, shared_neighbors, shared_count,
                     collect(DISTINCT other_neighbor) as other_neighbors
                WITH other, shared_count,
                     size(source_neighbors) + size(other_neighbors) - shared_count as union_size,
                     shared_neighbors
                WHERE union_size > 0
                RETURN other.id as id,
                       other.name as name,
                       labels(other)[0] as type,
                       shared_count / toFloat(union_size) as score,
                       [n IN shared_neighbors | n.name] as shared
                ORDER BY score DESC
                LIMIT $limit
                """,
                params={"entity_id": entity_id, "limit": top_k},
                operation="similarity.jaccard",
                labels=("Entity",),
            )
            result = await run_validated_query(session, *self._query_tuple(query))

            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "type": r["type"],
                    "score": r["score"],
                    "shared_neighbors": r["shared"],
                    "method": "jaccard",
                }
                async for r in result
            ]

    async def _adamic_adar_similarity(self, entity_id: str, top_k: int, tenant_id: str | None = None) -> list[dict]:
        """Calculate Adamic-Adar similarity (weighted common neighbors)."""
        driver = await self._get_driver()
        builder = self._builder(tenant_id)

        async with driver.session(database=self.settings.neo4j_database) as session:
            query = builder.custom_tenant_query(
                """
                // strict-scoped-query-execution
                MATCH (source)-[:ENABLES|BENEFITS|DRIVES]-(common)-[:ENABLES|BENEFITS|DRIVES]-(other)
                WHERE source.id = $entity_id
                  AND source.tenant_id = $_tenant_id
                  AND common.tenant_id = $_tenant_id
                  AND other.tenant_id = $_tenant_id
                  AND other.id <> $entity_id
                WITH other, common,
                     count {{(common)--()}} as common_degree
                WHERE common_degree > 1
                WITH other, sum(1.0 / log(common_degree)) as score,
                     collect(common.name) as shared
                RETURN other.id as id,
                       other.name as name,
                       labels(other)[0] as type,
                       score,
                       shared
                ORDER BY score DESC
                LIMIT $limit
                """,
                params={"entity_id": entity_id, "limit": top_k},
                operation="similarity.adamic_adar",
                labels=("Entity",),
            )
            result = await run_validated_query(session, *self._query_tuple(query))

            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "type": r["type"],
                    "score": r["score"],
                    "shared_neighbors": r["shared"],
                    "method": "adamic_adar",
                }
                async for r in result
            ]

    async def _vector_similarity(self, entity_id: str, top_k: int, tenant_id: str | None = None) -> list[dict]:
        """Calculate vector-based similarity."""
        if not self.vector_store:
            return []

        resolved_tenant_id = self._resolve_tenant_id(tenant_id)
        results = await self.vector_store.search_by_entity_id(
            entity_id, top_k=top_k, tenant_id=resolved_tenant_id
        )

        return [
            {
                "id": r["id"],
                "name": r.get("text", "")[:100],
                "type": r.get("entity_type", "Unknown"),
                "score": r["score"],
                "method": "vector",
            }
            for r in results
        ]

    async def _path_similarity(self, entity_id: str, top_k: int, tenant_id: str | None = None) -> list[dict]:
        """Calculate similarity based on common paths in value tree."""
        driver = await self._get_driver()
        builder = self._builder(tenant_id)

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Find entities that share paths to common value drivers
            query = builder.custom_tenant_query(
                """
                // strict-scoped-query-execution
                // Find all paths from source to value drivers
                MATCH path1 = (source)-[:ENABLES|BENEFITS|DRIVES*1..4]->(vd:ValueDriver)
                WHERE source.id = $entity_id
                  AND source.tenant_id = $_tenant_id
                  AND vd.tenant_id = $_tenant_id
                  AND all(node IN nodes(path1) WHERE node.tenant_id = $_tenant_id)
                WITH source, vd, collect(path1) as source_paths
                // Find other entities that also connect to these value drivers
                MATCH path2 = (other)-[:ENABLES|BENEFITS|DRIVES*1..4]->(vd)
                WHERE other.id <> $entity_id
                  AND other.tenant_id = $_tenant_id
                  AND all(node IN nodes(path2) WHERE node.tenant_id = $_tenant_id)
                WITH other, count(DISTINCT vd) as shared_value_drivers,
                     collect(DISTINCT vd.name) as value_driver_names
                WHERE shared_value_drivers > 0
                RETURN other.id as id,
                       other.name as name,
                       labels(other)[0] as type,
                       shared_value_drivers as score,
                       value_driver_names as shared_value_drivers
                ORDER BY shared_value_drivers DESC
                LIMIT $limit
                """,
                params={"entity_id": entity_id, "limit": top_k},
                operation="similarity.path",
                labels=("ValueDriver",),
            )
            result = await run_validated_query(session, *self._query_tuple(query))

            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "type": r["type"],
                    "score": r["score"],
                    "shared_value_drivers": r["shared_value_drivers"],
                    "method": "path",
                }
                async for r in result
            ]

    async def _combined_similarity(self, entity_id: str, top_k: int, tenant_id: str | None = None) -> list[dict]:
        """Combine multiple similarity methods."""
        # Get scores from different methods
        jaccard_scores = {
            r["id"]: r["score"]
            for r in await self._jaccard_similarity(entity_id, top_k * 2, tenant_id)
        }
        vector_scores = {
            r["id"]: r["score"]
            for r in await self._vector_similarity(entity_id, top_k * 2, tenant_id)
        }
        path_scores = {
            r["id"]: r["score"]
            for r in await self._path_similarity(entity_id, top_k * 2, tenant_id)
        }

        # Combine all unique entity IDs
        all_ids = (
            set(jaccard_scores.keys())
            | set(vector_scores.keys())
            | set(path_scores.keys())
        )

        # Calculate weighted combined score
        combined = []
        for entity_id in all_ids:
            j_score = jaccard_scores.get(entity_id, 0.0)
            v_score = vector_scores.get(entity_id, 0.0)
            p_score = path_scores.get(entity_id, 0.0)

            # Weight: graph 40%, vector 40%, path 20%
            combined_score = 0.4 * j_score + 0.4 * v_score + 0.2 * p_score

            if combined_score > 0:
                combined.append(
                    {
                        "id": entity_id,
                        "score": combined_score,
                        "component_scores": {
                            "jaccard": j_score,
                            "vector": v_score,
                            "path": p_score,
                        },
                        "method": "combined",
                    }
                )

        # Sort and get entity details
        combined.sort(key=lambda x: x["score"], reverse=True)
        top_entities = combined[:top_k]

        # Enrich with entity details
        driver = await self._get_driver()
        builder = self._builder(tenant_id)
        async with driver.session(database=self.settings.neo4j_database) as session:
            for entity in top_entities:
                enrich_query = builder.custom_tenant_query(
                    """
                    // strict-scoped-query-execution
                    MATCH (n)
                    WHERE n.id = $id AND n.tenant_id = $_tenant_id
                    RETURN n.name as name, labels(n)[0] as type
                    """,
                    params={"id": entity["id"]},
                    operation="similarity.combined.enrich",
                    labels=("Entity",),
                )
                result = await run_validated_query(session, *self._query_tuple(enrich_query))
                record = await result.single()
                if record:
                    entity["name"] = record["name"]
                    entity["type"] = record["type"]

        return top_entities
