"""Centrality analysis for identifying key entities in the Knowledge Graph."""

import logging
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase
from value_fabric.shared.identity.context import require_context
from value_fabric.shared.identity.isolation import ScopedQuery, TenantScopedCypher
from value_fabric.shared.models.typed_dict import TypedDictModel

from config import Settings, get_settings
from db.query_execution import run_scoped_query
from db.query_execution import run_validated_query


class CentralityAnalyzer__fallback_centralityResult(TypedDictModel):
    algorithm: str
    note: str
    top_entities: Any
    total_ranked: Any

class CentralityAnalyzer_calculate_degree_centralityResult(TypedDictModel):
    algorithm: str
    top_entities: Any
    total_ranked: Any

class CentralityAnalyzer_get_value_tree_centralityResult(TypedDictModel):
    algorithm: str
    by_layer: dict[str, Any]
    key_connectors: Any

class CentralityAnalyzer_calculate_pagerankResult(TypedDictModel):
    algorithm: str
    top_entities: Any
    total_ranked: Any

class CentralityAnalyzer_calculate_betweennessResult(TypedDictModel):
    algorithm: str
    top_entities: Any
    total_ranked: Any

logger = logging.getLogger(__name__)


class CentralityAnalyzer:
    """Centrality analysis using Neo4j GDS.

    Identifies key entities in the knowledge graph using:
    - PageRank (overall importance)
    - Betweenness (bridge/connector importance)
    - Degree centrality (connectivity)
    - Eigenvector centrality (influence)
    """

    def __init__(
        self,
        driver: AsyncDriver | None = None,
        settings: Settings | None = None,
    ):
        """Initialize centrality analyzer.

        Args:
            driver: Neo4j async driver
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self._driver = driver
        self._owned_driver = driver is None

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

    def _resolve_tenant_id(self, tenant_id: str | None = None) -> str:
        """Resolve the tenant id for tenant-owned graph analytics.

        Layer 3 graph analytics must fail closed outside an authenticated tenant
        context because Neo4j Community Edition cannot enforce row-level
        security at the database layer.
        """
        resolved = tenant_id or require_context().tenant_id
        if not resolved:
            raise RuntimeError("tenant_id is required for Layer 3 centrality analytics")
        return str(resolved)

    def _tenant_builder(self, tenant_id: str | None = None) -> TenantScopedCypher:
        """Return the canonical strict Cypher builder for the active tenant."""
        return TenantScopedCypher(self._resolve_tenant_id(tenant_id))

    async def _run_scoped(self, session: Any, query: ScopedQuery):
        """Execute a strict scoped query through the Neo4j session seam."""
        return await run_scoped_query(session.run, query)

    async def calculate_pagerank(
        self,
        node_labels: list[str] | None = None,
        relationship_types: list[str] | None = None,
        top_k: int = 20,
        tenant_id: str | None = None,
    ) -> dict:
        """Calculate PageRank for all nodes.

        Args:
            node_labels: Filter by node labels
            relationship_types: Filter by relationship types
            top_k: Number of top results to return

        Returns:
            PageRank results
        """
        driver = await self._get_driver()

        async with driver.session(database=self.settings.neo4j_database) as session:
            try:
                # Check for GDS
                await run_validated_query(session, "RETURN gds.version() as version")
            except Exception:
                logger.warning("GDS not available, using fallback")
                return await self._fallback_centrality(
                    session, node_labels, "degree", top_k, tenant_id=tenant_id
                )

            graph_name = f"centrality_{self._random_id()}"

            try:
                # Project graph
                await self._project_graph(
                    session, graph_name, node_labels, relationship_types, tenant_id=tenant_id
                )

                # Calculate PageRank
                result = await run_validated_query(session,
                    """
                    CALL gds.pageRank.stream($graph_name, {
                        maxIterations: 20,
                        dampingFactor: 0.85,
                        concurrency: 4
                    })
                    YIELD nodeId, score
                    RETURN gds.util.asNode(nodeId) as node, score
                    ORDER BY score DESC
                    LIMIT $limit
                    """,
                    {"graph_name": graph_name, "limit": top_k},
                )

                rankings = []
                async for record in result:
                    node = record["node"]
                    rankings.append(
                        {
                            "id": node["id"],
                            "name": node.get("name", node.get("title", "Unknown")),
                            "type": list(node.labels)[0]
                            if hasattr(node, "labels")
                            else "Unknown",
                            "score": record["score"],
                        }
                    )

                return CentralityAnalyzer_calculate_pagerankResult.model_validate({
                    "algorithm": "pagerank",
                    "total_ranked": len(rankings),
                    "top_entities": rankings,
                })


            finally:
                await self._drop_graph(session, graph_name)

    async def calculate_betweenness(
        self,
        node_labels: list[str] | None = None,
        relationship_types: list[str] | None = None,
        top_k: int = 20,
        tenant_id: str | None = None,
    ) -> dict:
        """Calculate betweenness centrality.

        Identifies entities that act as bridges between different parts
        of the graph (important connectors).
        """
        driver = await self._get_driver()

        async with driver.session(database=self.settings.neo4j_database) as session:
            try:
                await run_validated_query(session, "RETURN gds.version() as version")
            except Exception:
                return await self._fallback_centrality(
                    session, node_labels, "betweenness", top_k, tenant_id=tenant_id
                )

            graph_name = f"centrality_{self._random_id()}"

            try:
                await self._project_graph(
                    session, graph_name, node_labels, relationship_types, tenant_id=tenant_id
                )

                result = await run_validated_query(session,
                    """
                    CALL gds.betweenness.stream($graph_name, {
                        concurrency: 4
                    })
                    YIELD nodeId, score
                    RETURN gds.util.asNode(nodeId) as node, score
                    ORDER BY score DESC
                    LIMIT $limit
                    """,
                    {"graph_name": graph_name, "limit": top_k},
                )

                rankings = []
                async for record in result:
                    node = record["node"]
                    rankings.append(
                        {
                            "id": node["id"],
                            "name": node.get("name", node.get("title", "Unknown")),
                            "type": list(node.labels)[0]
                            if hasattr(node, "labels")
                            else "Unknown",
                            "score": record["score"],
                        }
                    )

                return CentralityAnalyzer_calculate_betweennessResult.model_validate({
                    "algorithm": "betweenness",
                    "total_ranked": len(rankings),
                    "top_entities": rankings,
                })


            finally:
                await self._drop_graph(session, graph_name)

    async def calculate_degree_centrality(
        self,
        node_labels: list[str] | None = None,
        top_k: int = 20,
        tenant_id: str | None = None,
    ) -> dict:
        """Calculate degree centrality within the active tenant only.

        Useful for finding hubs and highly connected entities.
        """
        driver = await self._get_driver()
        builder = self._tenant_builder(tenant_id)
        label_filter = "AND any(label IN labels(n) WHERE label IN $node_labels)" if node_labels else ""
        query = builder.custom_tenant_query(
            f"""
            MATCH (n)
            WHERE n.tenant_id = $_tenant_id
            {label_filter}
            OPTIONAL MATCH (n)-[r]-(m)
            WITH n, r, m
            WHERE r IS NULL OR m.tenant_id = $_tenant_id
            WITH n, count(r) as degree
            RETURN n.id as id,
                   n.name as name,
                   labels(n)[0] as type,
                   degree
            ORDER BY degree DESC
            LIMIT $limit
            """,
            params={"limit": top_k, "node_labels": node_labels or []},
            operation="centrality.degree",
            labels=tuple(node_labels or ["*"]),
        )

        async with driver.session(database=self.settings.neo4j_database) as session:
            result = await self._run_scoped(session, query)

            rankings = []
            async for record in result:
                rankings.append(
                    {
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "score": record["degree"],
                    }
                )

            return CentralityAnalyzer_calculate_degree_centralityResult.model_validate({
                "algorithm": "degree",
                "total_ranked": len(rankings),
                "top_entities": rankings,
            })


    async def get_value_tree_centrality(self, tenant_id: str | None = None) -> dict:
        """Analyze centrality within the tenant-scoped 4-layer value tree.

        Returns key entities at each layer and cross-layer connectors.
        """
        driver = await self._get_driver()
        builder = self._tenant_builder(tenant_id)

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Get most connected capabilities
            capabilities_query = builder.custom_tenant_query(
                """
                MATCH (c:Capability)-[r:ENABLES]->(uc:UseCase)
                WHERE c.tenant_id = $_tenant_id AND uc.tenant_id = $_tenant_id
                WITH c, count(r) as use_case_count
                RETURN c.id as id, c.name as name, use_case_count
                ORDER BY use_case_count DESC
                LIMIT 10
                """,
                operation="centrality.value_tree.capabilities",
                labels=("Capability", "UseCase"),
            )
            capabilities_result = await self._run_scoped(session, capabilities_query)
            top_capabilities = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "use_cases_enabled": r["use_case_count"],
                }
                async for r in capabilities_result
            ]

            # Get most beneficial use cases
            usecases_query = builder.custom_tenant_query(
                """
                MATCH (uc:UseCase)-[r:BENEFITS]->(p:Persona)
                WHERE uc.tenant_id = $_tenant_id AND p.tenant_id = $_tenant_id
                WITH uc, count(r) as persona_count
                RETURN uc.id as id, uc.name as name, persona_count
                ORDER BY persona_count DESC
                LIMIT 10
                """,
                operation="centrality.value_tree.use_cases",
                labels=("UseCase", "Persona"),
            )
            usecases_result = await self._run_scoped(session, usecases_query)
            top_use_cases = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "personas_benefited": r["persona_count"],
                }
                async for r in usecases_result
            ]

            # Get most influential personas
            personas_query = builder.custom_tenant_query(
                """
                MATCH (p:Persona)-[r:DRIVES]->(vd:ValueDriver)
                WHERE p.tenant_id = $_tenant_id AND vd.tenant_id = $_tenant_id
                WITH p, count(r) as value_driver_count
                RETURN p.id as id, p.title as name, value_driver_count
                ORDER BY value_driver_count DESC
                LIMIT 10
                """,
                operation="centrality.value_tree.personas",
                labels=("Persona", "ValueDriver"),
            )
            personas_result = await self._run_scoped(session, personas_query)
            top_personas = [
                {
                    "id": r["id"],
                    "title": r["name"],
                    "value_drivers_driven": r["value_driver_count"],
                }
                async for r in personas_result
            ]

            # Get key connectors (entities bridging multiple layers)
            connectors_query = builder.custom_tenant_query(
                """
                MATCH (n)
                WHERE n.tenant_id = $_tenant_id
                  AND any(label IN labels(n) WHERE label IN $value_tree_labels)
                  AND EXISTS {
                    MATCH (n)-[:ENABLES|:BENEFITS|:DRIVES]-(connected)
                    WHERE connected.tenant_id = $_tenant_id
                  }
                OPTIONAL MATCH (n)-[:ENABLES]->(enabled)
                WHERE enabled.tenant_id = $_tenant_id
                WITH n, count(enabled) AS enables_count
                OPTIONAL MATCH (n)-[:BENEFITS]->(benefited)
                WHERE benefited.tenant_id = $_tenant_id
                WITH n, enables_count, count(benefited) AS benefits_count
                OPTIONAL MATCH (n)-[:DRIVES]->(driven)
                WHERE driven.tenant_id = $_tenant_id
                WITH n, enables_count, benefits_count, count(driven) AS drives_count
                WHERE (enables_count + benefits_count + drives_count) > 2
                RETURN n.id as id,
                       n.name as name,
                       labels(n)[0] as type,
                       enables_count, benefits_count, drives_count,
                       (enables_count + benefits_count + drives_count) as total
                ORDER BY total DESC
                LIMIT 10
                """,
                params={"value_tree_labels": ["Capability", "UseCase", "Persona", "ValueDriver"]},
                operation="centrality.value_tree.connectors",
                labels=("Capability", "UseCase", "Persona", "ValueDriver"),
            )
            connectors_result = await self._run_scoped(session, connectors_query)
            key_connectors = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "type": r["type"],
                    "outbound_connections": r["total"],
                }
                async for r in connectors_result
            ]

            return CentralityAnalyzer_get_value_tree_centralityResult.model_validate({
                "algorithm": "value_tree_analysis",
                "by_layer": {
                    "capabilities": top_capabilities,
                    "use_cases": top_use_cases,
                    "personas": top_personas,
                },
                "key_connectors": key_connectors,
            })


    async def _project_graph(
        self,
        session,
        graph_name: str,
        node_labels: list[str] | None,
        relationship_types: list[str] | None,
        tenant_id: str | None = None,
    ) -> None:
        """Project a tenant-scoped graph for GDS algorithms."""
        node_filter = node_labels or ["Capability", "UseCase", "Persona", "ValueDriver"]
        rel_filter = relationship_types or ["ENABLES", "BENEFITS", "DRIVES", "CONTRIBUTES_TO"]
        builder = self._tenant_builder(tenant_id)
        query = builder.custom_tenant_query(
            """
            CALL gds.graph.project.cypher(
                $graph_name,
                $node_query,
                $relationship_query,
                {parameters: {_tenant_id: $_tenant_id, node_labels: $node_filter, relationship_types: $rel_filter}}
            )
            """,
            params={
                "graph_name": graph_name,
                "node_filter": node_filter,
                "rel_filter": rel_filter,
                "node_query": """
                    MATCH (n)
                    WHERE n.tenant_id = $_tenant_id
                      AND any(label IN labels(n) WHERE label IN $node_labels)
                    RETURN id(n) AS id
                """,
                "relationship_query": """
                    MATCH (source)-[r]-(target)
                    WHERE source.tenant_id = $_tenant_id
                      AND target.tenant_id = $_tenant_id
                      AND type(r) IN $relationship_types
                    RETURN id(source) AS source, id(target) AS target, type(r) AS type
                """,
            },
            operation="centrality.gds_project",
            labels=tuple(node_filter),
        )
        await self._run_scoped(session, query)

    async def _drop_graph(self, session, graph_name: str) -> None:
        """Drop GDS graph projection."""
        try:
            await run_validated_query(session,
                "CALL gds.graph.drop($graph_name)",
                {"graph_name": graph_name},
            )
        except Exception as e:
            logger.debug(f"Could not drop graph: {e}")

    async def _fallback_centrality(
        self,
        session,
        node_labels: list[str] | None,
        metric: str,
        top_k: int,
        tenant_id: str | None = None,
    ) -> dict:
        """Fallback centrality using tenant-scoped degree count."""
        builder = self._tenant_builder(tenant_id)
        label_filter = "AND any(label IN labels(n) WHERE label IN $node_labels)" if node_labels else ""
        query = builder.custom_tenant_query(
            f"""
            MATCH (n)
            WHERE n.tenant_id = $_tenant_id
            {label_filter}
            OPTIONAL MATCH (n)-[r]-(m)
            WITH n, r, m
            WHERE r IS NULL OR m.tenant_id = $_tenant_id
            WITH n, count(r) as degree
            RETURN n.id as id,
                   n.name as name,
                   labels(n)[0] as type,
                   degree as score
            ORDER BY degree DESC
            LIMIT $limit
            """,
            params={"limit": top_k, "node_labels": node_labels or []},
            operation=f"centrality.{metric}.fallback",
            labels=tuple(node_labels or ["*"]),
        )
        result = await self._run_scoped(session, query)

        rankings = []
        async for record in result:
            rankings.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "score": record["score"],
                }
            )

        return CentralityAnalyzer__fallback_centralityResult.model_validate({
            "algorithm": f"{metric}_fallback",
            "note": "Using degree centrality fallback - GDS not available",
            "total_ranked": len(rankings),
            "top_entities": rankings,
        })


    def _random_id(self) -> str:
        """Generate random ID."""
        import random
        import string

        return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
