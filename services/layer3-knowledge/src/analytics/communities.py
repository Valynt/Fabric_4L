"""Community detection algorithms for Knowledge Graph analysis."""

import logging
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase
from value_fabric.shared.identity.context import require_context
from value_fabric.shared.identity.isolation import ScopedQuery, TenantScopedCypher
from value_fabric.shared.models.typed_dict import TypedDictModel

from value_fabric.layer3.config import Settings, get_settings
from db.query_execution import run_scoped_query
from db.query_execution import run_validated_query


class CommunityDetector__fallback_community_detectionResult(TypedDictModel):
    algorithm: str
    communities: Any
    note: str
    total_communities: Any

class CommunityDetector_detect_by_value_treeResult(TypedDictModel):
    algorithm: str
    communities: Any
    total_communities: Any

class CommunityDetector__build_rel_filterResult(TypedDictModel):
    BENEFITS: dict[str, Any]
    DRIVES: dict[str, Any]
    ENABLES: dict[str, Any]

class CommunityDetector_detect_louvainResult(TypedDictModel):
    algorithm: str
    communities: Any
    modularity: Any
    total_communities: Any
    total_nodes: Any
    valid_communities: Any

class CommunityDetector_detect_leidenResult(TypedDictModel):
    algorithm: str
    communities: Any
    total_communities: Any
    total_nodes: Any
    valid_communities: Any

logger = logging.getLogger(__name__)


class CommunityDetector:
    """Community detection using Neo4j Graph Data Science (GDS).

    Detects communities of related entities (personas, use cases, capabilities)
    for pattern discovery and segmentation.
    """

    def __init__(
        self,
        driver: AsyncDriver | None = None,
        settings: Settings | None = None,
    ):
        """Initialize community detector.

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
        """Resolve the tenant id for tenant-owned community analytics."""
        resolved = tenant_id or require_context().tenant_id
        if not resolved:
            raise RuntimeError("tenant_id is required for Layer 3 community analytics")
        return str(resolved)

    def _tenant_builder(self, tenant_id: str | None = None) -> TenantScopedCypher:
        """Return the canonical strict Cypher builder for the active tenant."""
        return TenantScopedCypher(self._resolve_tenant_id(tenant_id))

    async def _run_scoped(self, session: Any, query: ScopedQuery):
        """Execute a strict scoped query through the Neo4j session seam."""
        return await run_scoped_query(session.run, query)

    async def detect_louvain(
        self,
        node_labels: list[str] | None = None,
        relationship_types: list[str] | None = None,
        min_community_size: int = 3,
        max_levels: int = 10,
        tenant_id: str | None = None,
    ) -> dict:
        """Detect communities using Louvain algorithm.

        Args:
            node_labels: Node labels to include (e.g., ["Persona", "UseCase"])
            relationship_types: Relationship types to follow
            min_community_size: Minimum size for a valid community
            max_levels: Maximum hierarchy levels

        Returns:
            Community detection results with statistics
        """
        driver = await self._get_driver()

        # Build graph projection
        node_filter = self._build_node_filter(node_labels)
        _rel_filter = self._build_rel_filter(relationship_types)

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Check if GDS is available
            try:
                await run_validated_query(session, "RETURN gds.version() as version")
            except Exception as e:
                logger.warning(f"GDS not available: {e}")
                return await self._fallback_community_detection(
                    session, node_labels, relationship_types, min_community_size, tenant_id=tenant_id
                )

            # Create in-memory graph projection
            graph_name = f"communities_{self._random_id()}"

            try:
                # Project graph with tenant-filtered Cypher projection.
                await self._project_graph(
                    session, graph_name, node_filter, relationship_types, tenant_id=tenant_id
                )

                # Run Louvain
                result = await run_validated_query(session,
                    """
                    CALL gds.louvain.stream($graph_name, {
                        maxLevels: $max_levels,
                        tolerance: 0.0001,
                        concurrency: 4
                    })
                    YIELD nodeId, communityId, intermediateCommunityIds
                    RETURN gds.util.asNode(nodeId) as node, communityId
                    """,
                    {"graph_name": graph_name, "max_levels": max_levels},
                )

                # Collect results
                communities: dict[int, list[dict]] = {}
                async for record in result:
                    node = record["node"]
                    community_id = record["communityId"]

                    if community_id not in communities:
                        communities[community_id] = []

                    communities[community_id].append(
                        {
                            "id": node["id"],
                            "name": node.get("name", node.get("title", "Unknown")),
                            "type": list(node.labels)[0]
                            if hasattr(node, "labels")
                            else "Unknown",
                        }
                    )

                # Filter small communities
                valid_communities = {
                    k: v for k, v in communities.items() if len(v) >= min_community_size
                }

                return CommunityDetector_detect_louvainResult.model_validate({
                    "algorithm": "louvain",
                    "total_communities": len(communities),
                    "valid_communities": len(valid_communities),
                    "total_nodes": sum(len(m) for m in communities.values()),
                    "communities": [
                        {
                            "id": cid,
                            "size": len(members),
                            "members": members,
                        }
                        for cid, members in valid_communities.items()
                    ],
                    "modularity": await self._calculate_modularity(
                        session, graph_name, valid_communities
                    ),
                })


            finally:
                # Cleanup graph projection
                try:
                    await run_validated_query(session,
                        "CALL gds.graph.drop($graph_name)",
                        {"graph_name": graph_name},
                    )
                except Exception as e:
                    logger.debug(f"Could not drop graph projection: {e}")

    async def detect_leiden(
        self,
        node_labels: list[str] | None = None,
        relationship_types: list[str] | None = None,
        min_community_size: int = 3,
        tenant_id: str | None = None,
    ) -> dict:
        """Detect communities using Leiden algorithm (higher quality than Louvain).

        Args:
            node_labels: Node labels to include
            relationship_types: Relationship types to follow
            min_community_size: Minimum community size

        Returns:
            Community detection results
        """
        driver = await self._get_driver()

        node_filter = self._build_node_filter(node_labels)
        _rel_filter = self._build_rel_filter(relationship_types)

        async with driver.session(database=self.settings.neo4j_database) as session:
            try:
                await run_validated_query(session, "RETURN gds.version() as version")
            except Exception as e:
                logger.warning(f"GDS not available: {e}")
                return await self._fallback_community_detection(
                    session, node_labels, relationship_types, min_community_size, tenant_id=tenant_id
                )

            graph_name = f"communities_{self._random_id()}"

            try:
                await self._project_graph(
                    session, graph_name, node_filter, relationship_types, tenant_id=tenant_id
                )

                # Run Leiden
                result = await run_validated_query(session,
                    """
                    CALL gds.leiden.stream($graph_name, {
                        concurrency: 4
                    })
                    YIELD nodeId, communityId
                    RETURN gds.util.asNode(nodeId) as node, communityId
                    """,
                    {"graph_name": graph_name},
                )

                communities: dict[int, list[dict]] = {}
                async for record in result:
                    node = record["node"]
                    community_id = record["communityId"]

                    if community_id not in communities:
                        communities[community_id] = []

                    communities[community_id].append(
                        {
                            "id": node["id"],
                            "name": node.get("name", node.get("title", "Unknown")),
                            "type": list(node.labels)[0]
                            if hasattr(node, "labels")
                            else "Unknown",
                        }
                    )

                valid_communities = {
                    k: v for k, v in communities.items() if len(v) >= min_community_size
                }

                return CommunityDetector_detect_leidenResult.model_validate({
                    "algorithm": "leiden",
                    "total_communities": len(communities),
                    "valid_communities": len(valid_communities),
                    "total_nodes": sum(len(m) for m in communities.values()),
                    "communities": [
                        {
                            "id": cid,
                            "size": len(members),
                            "members": members,
                        }
                        for cid, members in valid_communities.items()
                    ],
                })


            finally:
                try:
                    await run_validated_query(session,
                        "CALL gds.graph.drop($graph_name)",
                        {"graph_name": graph_name},
                    )
                except Exception as e:
                    logger.debug(f"Could not drop graph projection: {e}")

    async def detect_by_value_tree(self, tenant_id: str | None = None) -> dict:
        """Detect communities based on the 4-layer value tree structure.

        Groups entities that contribute to common value drivers.

        Returns:
            Value-tree based communities
        """
        driver = await self._get_driver()

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Find tenant-scoped value drivers and their connected subgraphs.
            builder = self._tenant_builder(tenant_id)
            query = builder.custom_tenant_query(
                """
                MATCH (vd:ValueDriver)
                WHERE vd.tenant_id = $_tenant_id
                OPTIONAL MATCH path = (vd)<-[:DRIVES]-(p:Persona)<-[:BENEFITS]-(uc:UseCase)<-[:ENABLES]-(c:Capability)
                WHERE p.tenant_id = $_tenant_id
                  AND uc.tenant_id = $_tenant_id
                  AND c.tenant_id = $_tenant_id
                WITH vd, collect(path) as paths
                RETURN vd.id as value_driver_id,
                       vd.name as value_driver_name,
                       vd.category as category,
                       [path IN paths | [node IN nodes(path) | {
                           id: node.id,
                           name: node.name,
                           type: labels(node)[0]
                       }]] as connected_paths
                """,
                operation="communities.value_tree",
                labels=("ValueDriver", "Persona", "UseCase", "Capability"),
            )
            result = await self._run_scoped(session, query)

            communities = []
            async for record in result:
                # Flatten paths into unique members
                all_members = []
                seen_ids = set()

                for path in record["connected_paths"]:
                    for node in path:
                        if node["id"] not in seen_ids:
                            seen_ids.add(node["id"])
                            all_members.append(node)

                if len(all_members) >= 2:  # At least some connection
                    communities.append(
                        {
                            "value_driver_id": record["value_driver_id"],
                            "value_driver_name": record["value_driver_name"],
                            "category": record["category"],
                            "size": len(all_members),
                            "members": all_members,
                        }
                    )

            return CommunityDetector_detect_by_value_treeResult.model_validate({
                "algorithm": "value_tree",
                "total_communities": len(communities),
                "communities": sorted(
                    communities, key=lambda x: x["size"], reverse=True
                ),
            })


    async def _fallback_community_detection(
        self,
        session,
        node_labels: list[str] | None,
        relationship_types: list[str] | None,
        min_size: int,
        tenant_id: str | None = None,
    ) -> dict:
        """Fallback using connected components when GDS unavailable."""
        label_filter = "AND any(label IN labels(n) WHERE label IN $node_labels)" if node_labels else ""
        rel_filter = "AND type(r) IN $relationship_types" if relationship_types else ""
        builder = self._tenant_builder(tenant_id)
        query = builder.custom_tenant_query(
            f"""
            MATCH (n)-[r]-(m)
            WHERE n.tenant_id = $_tenant_id
              AND m.tenant_id = $_tenant_id
              {label_filter}
              {rel_filter}
            WITH n, collect(m) as neighbors
            WHERE size(neighbors) >= $min_size - 1
            RETURN n.id as id, n.name as name, labels(n)[0] as type,
                   [x IN neighbors | x.id] as neighbor_ids
            """,
            params={
                "min_size": min_size,
                "node_labels": node_labels or [],
                "relationship_types": relationship_types or [],
            },
            operation="communities.fallback",
            labels=tuple(node_labels or ["*"]),
        )
        result = await self._run_scoped(session, query)

        communities = []
        async for record in result:
            communities.append(
                {
                    "center_id": record["id"],
                    "center_name": record["name"],
                    "center_type": record["type"],
                    "size": len(record["neighbor_ids"]) + 1,
                    "members": [record["id"]] + record["neighbor_ids"],
                }
            )

        return CommunityDetector__fallback_community_detectionResult.model_validate({
            "algorithm": "connected_components_fallback",
            "total_communities": len(communities),
            "communities": communities,
            "note": "Using fallback method - GDS not available",
        })


    async def _project_graph(
        self,
        session,
        graph_name: str,
        node_filter: list[str],
        relationship_types: list[str] | None,
        tenant_id: str | None = None,
    ) -> None:
        """Project a tenant-scoped graph for community algorithms."""
        rel_filter = relationship_types or ["ENABLES", "BENEFITS", "DRIVES"]
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
            operation="communities.gds_project",
            labels=tuple(node_filter),
        )
        await self._run_scoped(session, query)

    async def _calculate_modularity(
        self,
        session,
        graph_name: str,
        communities: dict[int, list],
    ) -> float:
        """Calculate modularity score for community quality."""
        try:
            result = await run_validated_query(session,
                """
                CALL gds.modularity.stream($graph_name, {
                    communityProperty: 'communityId'
                })
                YIELD modularity
                RETURN avg(modularity) as avg_modularity
                """,
                {"graph_name": graph_name},
            )
            record = await result.single()
            return record["avg_modularity"] if record else 0.0
        except Exception as e:
            logger.debug(f"Could not calculate modularity: {e}")
            return 0.0

    def _build_node_filter(self, node_labels: list[str] | None) -> Any:
        """Build node filter for GDS graph projection."""
        if not node_labels:
            return ["Capability", "UseCase", "Persona", "ValueDriver"]
        return node_labels

    def _build_rel_filter(self, relationship_types: list[str] | None) -> Any:
        """Build relationship filter for GDS graph projection."""
        if not relationship_types:
            return CommunityDetector__build_rel_filterResult.model_validate({
                "ENABLES": {"orientation": "UNDIRECTED"},
                "BENEFITS": {"orientation": "UNDIRECTED"},
                "DRIVES": {"orientation": "UNDIRECTED"},
            })


        return CommunityDetector__build_rel_filterResult.model_validate({rel: {"orientation": "UNDIRECTED"} for rel in relationship_types})

    def _random_id(self) -> str:
        """Generate random ID for graph projection."""
        import random
        import string

        return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
