from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""Graph visualisation domain router — full graph, entity subgraph, query subgraph.

Migrated from app_monolith.py as part of ARCH-L3-011 (Sprint 3 cutover).
All Cypher queries are tenant-scoped; tenant_id is required and extracted
from the authenticated request context (fail-closed on missing context).
"""


import asyncio
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ...api.dependencies import (
    AppState,
    get_app_state,
    get_graph_rag,
    get_hybrid_search,
)
from ...api.dependencies_tenant_secured import require_request_tenant_id
from ...api.models import (
    GraphEdge,
    GraphNode,
    GraphNodeWithLayout,
    GraphResponse,
    GraphStats,
    SubgraphResponse,
)
from ...db.query_execution import (
    MAX_QUERY_DEPTH,
    QUERY_TIMEOUT_SECONDS,
    CypherDepthLimitExceeded,
)
from ...graph.query_guards import sanitize_query_depth, sanitize_query_timeout_seconds

try:
    from ...metrics.prometheus_metrics import get_metrics
except (ImportError, ModuleNotFoundError):
    get_metrics = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Graph"])


def _build_graph_node(
    *,
    node_id: str,
    label: str,
    node_type: str,
    confidence: float = 0.8,
    x: float | None = None,
    y: float | None = None,
    r: float | None = None,
    properties: dict[str, Any] | None = None,
) -> GraphNode | GraphNodeWithLayout:
    """Construct a graph node using the canonical visualisation contract."""
    if x is not None or y is not None or r is not None:
        return GraphNodeWithLayout.model_validate(
            {
                "id": node_id,
                "label": label,
                "type": node_type,
                "confidence": confidence,
                "x": x,
                "y": y,
                "r": r,
                "properties": properties or {},
            }
        )
    return GraphNode.model_validate(
        {
            "id": node_id,
            "label": label,
            "type": node_type,
            "confidence": confidence,
            "properties": properties or {},
        }
    )


@router.get("/graph", response_model=GraphResponse, tags=["Graph"])
async def get_full_graph(
    tenant_id: str = Depends(require_request_tenant_id),
    limit: int = 1000,
    app_state: AppState = Depends(get_app_state),
) -> GraphResponse:
    """Return the complete knowledge graph for visualisation (tenant-scoped)."""
    neo4j = app_state.neo4j_driver
    if not neo4j:
        raise ServiceUnavailableError(message="Neo4j not available")

    try:
        nodes, node_ids, node_types = await _fetch_graph_nodes(neo4j, tenant_id, limit)
        edges = await _fetch_graph_edges(neo4j, tenant_id, node_ids)
        total_nodes, total_edges = await _fetch_graph_stats(neo4j, tenant_id)
        density = _calculate_density(total_nodes, total_edges)

        response = GraphResponse(
            nodes=nodes,
            edges=edges,
            stats=GraphStats(
                total_nodes=total_nodes,
                total_edges=total_edges,
                node_types=node_types,
                communities=0,
                density=density,
            ),
        )

        _record_full_graph_metrics(len(nodes))
        return response

    except (HTTPException, NotFoundError, ValidationError, ServiceUnavailableError):
        raise
    except TimeoutError:
        raise ValidationError(
            message="Query timed out after 30s (code: CYPHER_TIMEOUT)"
        )
    except Exception as e:
        logger.error("Failed to retrieve graph: %s", e)
        raise ServiceUnavailableError(message="Failed to retrieve graph")


async def _fetch_graph_nodes(
    neo4j, tenant_id: str, limit: int
) -> tuple[list[GraphNode | GraphNodeWithLayout], set[str], dict[str, int]]:
    """Fetch graph nodes and return nodes, node IDs, and node types."""
    nodes_result = await asyncio.wait_for(
        neo4j.execute_query(
            """
            MATCH (n {tenant_id: $tenant_id})
            WHERE n.id IS NOT NULL
            RETURN n.id as id, n.name as label, n.type as type,
                   n.confidence as confidence, n.x as x, n.y as y
            LIMIT $limit
            """,
            {"tenant_id": tenant_id, "limit": limit},
        ),
        timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
    )

    nodes: list[GraphNode | GraphNodeWithLayout] = []
    node_ids: set[str] = set()
    node_types: dict[str, int] = {}

    for r in nodes_result:
        r_dict: dict[str, Any] = r
        node_type = r_dict.get("type", "Unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1
        node_id = r_dict.get("id")
        if not node_id:
            continue
        resolved_name = r_dict.get("label") or node_id
        node = _build_graph_node(
            node_id=node_id,
            label=resolved_name,
            node_type=node_type,
            confidence=r_dict.get("confidence") or 0.8,
            x=r_dict.get("x"),
            y=r_dict.get("y"),
            properties={"name": resolved_name},
        )
        nodes.append(node)
        node_ids.add(node_id)

    return nodes, node_ids, node_types


async def _fetch_graph_edges(
    neo4j, tenant_id: str, node_ids: set[str]
) -> list[GraphEdge]:
    """Fetch graph edges for the given node IDs."""
    edges_result = await asyncio.wait_for(
        neo4j.execute_query(
            """
            MATCH (a {tenant_id: $tenant_id})-[r]->(b {tenant_id: $tenant_id})
            WHERE a.id IN $node_ids AND b.id IN $node_ids
            RETURN a.id as source, b.id as target, type(r) as rel_type, r.weight as weight
            """,
            {"tenant_id": tenant_id, "node_ids": list(node_ids)},
        ),
        timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
    )

    edges = []
    for r in edges_result:
        r_dict: dict[str, Any] = r
        source = r_dict.get("source")
        target = r_dict.get("target")
        if not source or not target:
            continue
        edges.append(
            GraphEdge(
                source=source,
                target=target,
                type=r_dict.get("rel_type", "RELATED_TO"),
                weight=r_dict.get("weight") or 1.0,
            )
        )

    return edges


async def _fetch_graph_stats(neo4j, tenant_id: str) -> tuple[int, int]:
    """Fetch total node and edge counts for the tenant."""
    total_nodes_result = await asyncio.wait_for(
        neo4j.execute_query(
            "MATCH (n {tenant_id: $tenant_id}) RETURN count(n) as total",
            {"tenant_id": tenant_id},
        ),
        timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
    )
    total_edges_result = await asyncio.wait_for(
        neo4j.execute_query(
            "MATCH (:Entity {tenant_id: $tenant_id})-[r]->(:Entity {tenant_id: $tenant_id}) RETURN count(r) as total",
            {"tenant_id": tenant_id},
        ),
        timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
    )

    if not total_nodes_result or not total_edges_result:
        logger.warning("Graph stats query returned empty results")

    total_nodes = total_nodes_result[0].get("total", 0) if total_nodes_result else 0
    total_edges = total_edges_result[0].get("total", 0) if total_edges_result else 0

    return total_nodes, total_edges


def _calculate_density(total_nodes: int, total_edges: int) -> float:
    """Calculate graph density."""
    if total_nodes <= 1:
        return 0.0
    return round((2 * total_edges) / (total_nodes * (total_nodes - 1)), 4)


def _record_full_graph_metrics(node_count: int) -> None:
    """Record metrics for full graph operation."""
    metrics = get_metrics() if get_metrics else None
    if metrics:
        metrics.observe_graph_result_size(
            size=node_count, endpoint="/graph", operation="get_full_graph"
        )


@router.get("/entities/{entity_id}/subgraph", response_model=SubgraphResponse)
async def get_entity_subgraph(
    entity_id: str,
    tenant_id: str = Depends(require_request_tenant_id),
    depth: int = Query(
        2,
        ge=1,
        le=MAX_QUERY_DEPTH,
        description=f"Traversal depth (1-{MAX_QUERY_DEPTH})",
    ),
    app_state: AppState = Depends(get_app_state),
) -> SubgraphResponse:
    """Return a subgraph centred on the specified entity (tenant-scoped)."""
    neo4j = app_state.neo4j_driver
    if not neo4j:
        raise ServiceUnavailableError(message="Neo4j not available")

    depth = sanitize_query_depth(depth, default_depth=2)

    try:
        root_record = await _get_root_entity(neo4j, entity_id, tenant_id)
        nodes_map, edges_map, node_types = await _build_entity_subgraph(
            neo4j, entity_id, depth, tenant_id, root_record
        )

        nodes = list(nodes_map.values())
        edges = list(edges_map.values())
        n = len(nodes)
        e = len(edges)

        response = SubgraphResponse(
            root_entity_id=entity_id,
            nodes=nodes,
            edges=edges,
            depth=depth,
            stats=GraphStats(
                total_nodes=n,
                total_edges=e,
                node_types=node_types,
                communities=0,
                density=0.0 if n <= 1 else (2 * e) / (n * (n - 1)),
            ),
        )

        _record_subgraph_metrics(
            depth, len(nodes), f"/entities/{entity_id}/subgraph", "get_entity_subgraph"
        )
        return response

    except (HTTPException, NotFoundError, ValidationError, ServiceUnavailableError):
        raise
    except CypherDepthLimitExceeded as exc:
        logger.warning("Cypher depth limit exceeded for %s: %s", entity_id, exc)
        raise ValidationError(
            message="Query depth limit exceeded (code: CYPHER_DEPTH_LIMIT_EXCEEDED)"
        ) from exc
    except TimeoutError:
        raise ValidationError(
            message="Query timed out after 30s (code: CYPHER_TIMEOUT)"
        )
    except Exception as e:
        logger.error("Failed to retrieve subgraph for %s: %s", entity_id, e)
        raise ServiceUnavailableError(message="Failed to retrieve subgraph")


async def _get_root_entity(neo4j, entity_id: str, tenant_id: str) -> dict[str, Any]:
    """Fetch the root entity record."""
    root_result = await asyncio.wait_for(
        neo4j.execute_query(
            """
            MATCH (n {id: $entity_id, tenant_id: $tenant_id})
            RETURN n.id as id, n.name as label, n.type as type, n.confidence as confidence
            """,
            {"entity_id": entity_id, "tenant_id": tenant_id},
        ),
        timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
    )
    if not root_result:
        raise NotFoundError(message=str(f"Entity {entity_id} not found"))
    return root_result[0]


async def _build_entity_subgraph(
    neo4j, entity_id: str, depth: int, tenant_id: str, root_record: dict[str, Any]
) -> tuple[
    dict[str, GraphNode | GraphNodeWithLayout], dict[str, GraphEdge], dict[str, int]
]:
    """Build the entity subgraph nodes and edges."""
    subgraph_result = await asyncio.wait_for(
        neo4j.execute_query(
            """
            MATCH path = (root {id: $entity_id, tenant_id: $tenant_id})-[*1..$depth]-(connected {tenant_id: $tenant_id})
            WHERE root.id IS NOT NULL AND connected.id IS NOT NULL
            RETURN root, connected, relationships(path) as rels, length(path) as path_length
            """,
            {"entity_id": entity_id, "depth": depth, "tenant_id": tenant_id},
        ),
        timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
    )

    nodes_map: dict[str, GraphNode | GraphNodeWithLayout] = {}
    edges_map: dict[str, GraphEdge] = {}
    node_types: dict[str, int] = {}

    root_type = root_record.get("type", "Unknown")
    node_types[root_type] = node_types.get(root_type, 0) + 1
    nodes_map[entity_id] = _build_graph_node(
        node_id=entity_id,
        label=root_record.get("label") or entity_id,
        node_type=root_type,
        confidence=root_record.get("confidence") or 0.8,
        properties={"is_root": True},
    )

    for r in subgraph_result:
        r_dict: dict[str, Any] = r
        connected = r_dict.get("connected")
        rels = r_dict.get("rels", [])

        if connected and connected.get("id"):
            conn_id = connected.get("id")
            conn_type = connected.get("type", "Unknown")
            if conn_id not in nodes_map:
                node_types[conn_type] = node_types.get(conn_type, 0) + 1
                nodes_map[conn_id] = _build_graph_node(
                    node_id=conn_id,
                    label=connected.get("name") or conn_id,
                    node_type=conn_type,
                    confidence=connected.get("confidence") or 0.8,
                    properties={},
                )

            for rel in rels:
                start_id = rel.get("start_node", {}).get("id")
                end_id = rel.get("end_node", {}).get("id")
                rel_type = rel.get("type", "RELATED_TO")
                if start_id and end_id:
                    edge_key = f"{start_id}-{end_id}-{rel_type}"
                    if edge_key not in edges_map:
                        edges_map[edge_key] = GraphEdge(
                            source=start_id,
                            target=end_id,
                            type=rel_type,
                            weight=rel.get("weight", 1.0),
                        )

    return nodes_map, edges_map, node_types


_VALID_REL_TYPE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@router.get("/graph/subgraph", response_model=SubgraphResponse)
async def get_query_subgraph(
    tenant_id: str = Depends(require_request_tenant_id),
    query: str | None = Query(
        None, description="Search query to find matching entities"
    ),
    center_entity_id: str | None = Query(
        None, description="Center entity ID for expansion mode"
    ),
    depth: int = Query(
        2,
        ge=1,
        le=MAX_QUERY_DEPTH,
        description=f"Traversal depth (1-{MAX_QUERY_DEPTH})",
    ),
    limit: int = Query(100, ge=1, le=500, description="Max nodes to return"),
    entity_types: list[str] | None = Query(None, description="Filter by entity types"),
    relationship_types: list[str] | None = Query(
        None, description="Filter by relationship types"
    ),
    hybrid_search=Depends(get_hybrid_search),
    graph_rag=Depends(get_graph_rag),
    app_state: AppState = Depends(get_app_state),
) -> SubgraphResponse:
    """Return a coherent subgraph based on a query or centre entity (tenant-scoped).

    **Query mode**: provide ``query`` to search for entities; returns subgraph
    with matching nodes + 1-hop neighbours.

    **Centre mode**: provide ``center_entity_id`` to expand N hops from that node.
    """
    if not query and not center_entity_id:
        raise ValidationError(
            message="Either 'query' or 'center_entity_id' parameter is required"
        )

    neo4j = app_state.neo4j_driver
    if not neo4j:
        raise ServiceUnavailableError(message="Neo4j not available")

    try:
        if center_entity_id:
            nodes, edges = await _get_center_entity_subgraph(
                neo4j, center_entity_id, tenant_id, depth, limit, relationship_types
            )
        else:
            nodes, edges = await _get_query_search_subgraph(
                neo4j, hybrid_search, query, limit, entity_types, tenant_id
            )

        n = len(nodes)
        e = len(edges)
        density = 0.0 if n <= 1 else (2 * e) / (n * (n - 1))

        response = SubgraphResponse(
            root_entity_id=center_entity_id or "",
            nodes=nodes,
            edges=edges,
            depth=depth,
            stats=GraphStats(total_nodes=n, total_edges=e, density=density),
        )

        _record_subgraph_metrics(
            depth, len(nodes), "/v1/graph/subgraph", "get_query_subgraph"
        )
        return response

    except (HTTPException, NotFoundError, ValidationError, ServiceUnavailableError):
        raise
    except CypherDepthLimitExceeded as exc:
        logger.warning("Cypher depth limit exceeded: %s", exc)
        raise ValidationError(
            message="Query depth limit exceeded (code: CYPHER_DEPTH_LIMIT_EXCEEDED)"
        ) from exc
    except TimeoutError:
        raise ValidationError(
            message="Query timed out after 30s (code: CYPHER_TIMEOUT)"
        )
    except Exception as e:
        logger.error("Failed to retrieve subgraph: %s", e)
        raise ServiceUnavailableError(message="Failed to retrieve subgraph")


async def _get_center_entity_subgraph(
    neo4j,
    center_entity_id: str,
    tenant_id: str,
    depth: int,
    limit: int,
    relationship_types: list[str] | None,
) -> tuple[list[GraphNode | GraphNodeWithLayout], list[GraphEdge]]:
    """Get subgraph centered on a specific entity."""
    root_result = await asyncio.wait_for(
        neo4j.execute_query(
            "MATCH (root {id: $entity_id, tenant_id: $tenant_id}) RETURN root",
            {"entity_id": center_entity_id, "tenant_id": tenant_id},
        ),
        timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
    )
    if not root_result:
        raise NotFoundError(message=str(f"Entity {center_entity_id} not found"))

    query_params: dict[str, Any] = {
        "entity_id": center_entity_id,
        "tenant_id": tenant_id,
        "depth": depth,
        "limit": limit,
    }

    rel_filter = ""
    if relationship_types:
        validated = [r for r in relationship_types if _VALID_REL_TYPE.match(r)]
        if not validated:
            raise ValidationError(message="No valid relationship types provided")
        rel_filter = "AND ALL(r IN relationships(path) WHERE type(r) IN $rel_types)"
        query_params["rel_types"] = validated

    subgraph_query = f"""
    MATCH path = (root {{id: $entity_id, tenant_id: $tenant_id}})-[*1..$depth]-(connected {{tenant_id: $tenant_id}})
    WHERE root.id IS NOT NULL AND connected.id IS NOT NULL
    {rel_filter}
    WITH root, connected, relationships(path) as rels, length(path) as hops
    RETURN root, collect(DISTINCT connected) as neighbors,
           collect(DISTINCT rels) as paths, max(hops) as max_hops
    LIMIT $limit
    """
    result = await asyncio.wait_for(
        neo4j.execute_query(subgraph_query, query_params),
        timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
    )

    nodes: list[GraphNode | GraphNodeWithLayout] = []
    edges: list[GraphEdge] = []

    if result:
        record: dict[str, Any] = result[0]
        root_data = record.get("root", {})
        neighbors = record.get("neighbors", [])
        paths = record.get("paths", [])

        if root_data:
            nodes.append(
                _build_graph_node(
                    node_id=root_data.get("id", center_entity_id),
                    label=root_data.get("name", root_data.get("id", "Unknown")),
                    node_type=root_data.get("entity_type", "Unknown"),
                    properties={
                        k: v
                        for k, v in root_data.items()
                        if k not in ["id", "name", "entity_type"]
                    },
                )
            )

        for neighbor in neighbors:
            if neighbor and neighbor.get("id"):
                nodes.append(
                    _build_graph_node(
                        node_id=neighbor.get("id"),
                        label=neighbor.get("name", neighbor.get("id", "Unknown")),
                        node_type=neighbor.get("entity_type", "Unknown"),
                        properties={
                            k: v
                            for k, v in neighbor.items()
                            if k not in ["id", "name", "entity_type"]
                        },
                    )
                )

        edge_keys: set[str] = set()
        for rel_list in paths:
            for rel in rel_list:
                if hasattr(rel, "start_node") and hasattr(rel, "end_node"):
                    src = rel.start_node.get("id")
                    tgt = rel.end_node.get("id")
                    edge_key = f"{src}-{tgt}-{rel.type}"
                    if src and tgt and edge_key not in edge_keys:
                        edge_keys.add(edge_key)
                        edges.append(
                            GraphEdge(
                                source=src, target=tgt, type=rel.type, properties={}
                            )
                        )

    return nodes, edges


async def _get_query_search_subgraph(
    neo4j,
    hybrid_search,
    query: str,
    limit: int,
    entity_types: list[str] | None,
    tenant_id: str,
) -> tuple[list[GraphNode | GraphNodeWithLayout], list[GraphEdge]]:
    """Get subgraph based on search query."""
    search_results = await hybrid_search.search(
        query=query,
        top_k=min(limit, 50),
        entity_type_filter=entity_types[0] if entity_types else None,
    )

    if not search_results:
        return [], []

    seed_ids = [r.entity_id for r in search_results if r.entity_id]
    if not seed_ids:
        return [], []

    result = await asyncio.wait_for(
        neo4j.execute_query(
            """
            UNWIND $seed_ids as seed_id
            MATCH (seed {id: seed_id, tenant_id: $tenant_id})
            OPTIONAL MATCH (seed)-[r]-(neighbor {tenant_id: $tenant_id})
            WHERE neighbor.id IS NOT NULL
            RETURN seed, collect(DISTINCT neighbor) as neighbors,
                   collect(DISTINCT r) as rels
            """,
            {"seed_ids": seed_ids[:20], "tenant_id": tenant_id},
        ),
        timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
    )

    nodes: list[GraphNode | GraphNodeWithLayout] = []
    edges: list[GraphEdge] = []
    node_ids: set[str] = set()

    for record in result:
        record_dict: dict[str, Any] = record
        seed = record_dict.get("seed")
        neighbors = record_dict.get("neighbors", [])
        rels = record_dict.get("rels", [])

        if seed and seed.get("id") and seed.get("id") not in node_ids:
            node_ids.add(seed.get("id"))
            nodes.append(
                _build_graph_node(
                    node_id=seed.get("id"),
                    label=seed.get("name", seed.get("id", "Unknown")),
                    node_type=seed.get("entity_type", "Unknown"),
                    properties={
                        k: v
                        for k, v in seed.items()
                        if k not in ["id", "name", "entity_type"]
                    },
                )
            )

        for neighbor in neighbors:
            if neighbor and neighbor.get("id") and neighbor.get("id") not in node_ids:
                node_ids.add(neighbor.get("id"))
                nodes.append(
                    _build_graph_node(
                        node_id=neighbor.get("id"),
                        label=neighbor.get("name", neighbor.get("id", "Unknown")),
                        node_type=neighbor.get("entity_type", "Unknown"),
                        properties={
                            k: v
                            for k, v in neighbor.items()
                            if k not in ["id", "name", "entity_type"]
                        },
                    )
                )

        for rel in rels:
            if hasattr(rel, "start_node") and hasattr(rel, "end_node"):
                src = rel.start_node.get("id")
                tgt = rel.end_node.get("id")
                if src and tgt and src in node_ids and tgt in node_ids:
                    edges.append(
                        GraphEdge(source=src, target=tgt, type=rel.type, properties={})
                    )

    return nodes, edges


def _record_subgraph_metrics(
    depth: int, node_count: int, endpoint: str, operation: str
) -> None:
    """Record metrics for subgraph operations."""
    metrics = get_metrics() if get_metrics else None
    if metrics:
        metrics.observe_graph_traversal_depth(
            depth=depth, endpoint=endpoint, operation=operation
        )
        metrics.observe_graph_result_size(
            size=node_count, endpoint=endpoint, operation=operation
        )
