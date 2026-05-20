"""Graph visualisation domain router — full graph, entity subgraph, query subgraph.

Migrated from app_monolith.py as part of ARCH-L3-011 (Sprint 3 cutover).
All Cypher queries are tenant-scoped; tenant_id is required and extracted
from the authenticated request context (fail-closed on missing context).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...api.dependencies import AppState, get_app_state, get_graph_rag, get_hybrid_search
from ...api.models import (
    GraphEdge,
    GraphNode,
    GraphNodeWithLayout,
    GraphResponse,
    GraphStats,
    SubgraphResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Graph"])


def _extract_tenant_id(request: Request | None) -> str | None:
    """Extract tenant_id from authenticated request context."""
    if not request:
        return None
    ctx = getattr(request.state, "context", None)
    if ctx and getattr(ctx, "tenant_id", None):
        return str(ctx.tenant_id)
    return None


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
    request: Request,
    limit: int = 1000,
    app_state: AppState = Depends(get_app_state),
) -> GraphResponse:
    """Return the complete knowledge graph for visualisation (tenant-scoped)."""
    neo4j = app_state.neo4j_driver
    if not neo4j:
        raise HTTPException(status_code=503, detail="Neo4j not available")

    tenant_id = _extract_tenant_id(request)
    if not tenant_id:
        raise HTTPException(
            status_code=400, detail="tenant_id is required for graph access"
        )

    try:
        nodes_result = await neo4j.execute_query(
            """
            MATCH (n {tenant_id: $tenant_id})
            WHERE n.id IS NOT NULL
            RETURN n.id as id, n.name as label, n.type as type,
                   n.confidence as confidence, n.x as x, n.y as y
            LIMIT $limit
            """,
            {"tenant_id": tenant_id, "limit": limit},
        )

        nodes: list[GraphNode | GraphNodeWithLayout] = []
        node_ids: set[str] = set()
        node_types: dict[str, int] = {}

        for r in nodes_result:
            node_type = r.get("type", "Unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
            node = _build_graph_node(
                node_id=r.get("id"),
                label=r.get("label") or r.get("id"),
                node_type=node_type,
                confidence=r.get("confidence") or 0.8,
                x=r.get("x"),
                y=r.get("y"),
                properties={"name": r.get("label")},
            )
            nodes.append(node)
            node_ids.add(r.get("id"))

        edges_result = await neo4j.execute_query(
            """
            MATCH (a {tenant_id: $tenant_id})-[r]->(b {tenant_id: $tenant_id})
            WHERE a.id IN $node_ids AND b.id IN $node_ids
            RETURN a.id as source, b.id as target, type(r) as rel_type, r.weight as weight
            """,
            {"tenant_id": tenant_id, "node_ids": list(node_ids)},
        )

        edges = [
            GraphEdge(
                source=r.get("source"),
                target=r.get("target"),
                type=r.get("rel_type", "RELATED_TO"),
                weight=r.get("weight") or 1.0,
            )
            for r in edges_result
        ]

        total_nodes_result = await neo4j.execute_query(
            "MATCH (n {tenant_id: $tenant_id}) RETURN count(n) as total",
            {"tenant_id": tenant_id},
        )
        total_edges_result = await neo4j.execute_query(
            "MATCH (:Entity {tenant_id: $tenant_id})-[r]->(:Entity {tenant_id: $tenant_id}) RETURN count(r) as total",
            {"tenant_id": tenant_id},
        )

        total_nodes = total_nodes_result[0].get("total", 0) if total_nodes_result else 0
        total_edges = total_edges_result[0].get("total", 0) if total_edges_result else 0
        density = (
            0.0
            if total_nodes <= 1
            else round((2 * total_edges) / (total_nodes * (total_nodes - 1)), 4)
        )

        return GraphResponse(
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve graph: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve graph: {str(e)}"
        )


@router.get("/entities/{entity_id}/subgraph", response_model=SubgraphResponse)
async def get_entity_subgraph(
    entity_id: str,
    request: Request,
    depth: int = 2,
    app_state: AppState = Depends(get_app_state),
) -> SubgraphResponse:
    """Return a subgraph centred on the specified entity (tenant-scoped)."""
    neo4j = app_state.neo4j_driver
    if not neo4j:
        raise HTTPException(status_code=503, detail="Neo4j not available")

    tenant_id = _extract_tenant_id(request)
    if not tenant_id:
        raise HTTPException(
            status_code=400, detail="tenant_id is required for value tree access"
        )

    depth = max(1, min(depth, 5))

    try:
        root_result = await neo4j.execute_query(
            """
            MATCH (n {id: $entity_id, tenant_id: $tenant_id})
            RETURN n.id as id, n.name as label, n.type as type, n.confidence as confidence
            """,
            {"entity_id": entity_id, "tenant_id": tenant_id},
        )
        if not root_result:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        root_record = root_result[0]

        subgraph_result = await neo4j.execute_query(
            """
            MATCH path = (root {id: $entity_id, tenant_id: $tenant_id})-[*1..$depth]-(connected {tenant_id: $tenant_id})
            WHERE root.id IS NOT NULL AND connected.id IS NOT NULL
            RETURN root, connected, relationships(path) as rels, length(path) as path_length
            """,
            {"entity_id": entity_id, "depth": depth, "tenant_id": tenant_id},
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
            connected = r.get("connected")
            rels = r.get("rels", [])

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

        nodes = list(nodes_map.values())
        edges = list(edges_map.values())
        n = len(nodes)
        e = len(edges)

        return SubgraphResponse(
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve subgraph for %s: %s", entity_id, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve subgraph: {str(e)}"
        )


_VALID_REL_TYPE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


@router.get("/v1/graph/subgraph", response_model=SubgraphResponse)
async def get_query_subgraph(
    request: Request,
    query: str | None = Query(None, description="Search query to find matching entities"),
    center_entity_id: str | None = Query(None, description="Center entity ID for expansion mode"),
    depth: int = Query(2, ge=1, le=3, description="Traversal depth (1-3)"),
    limit: int = Query(100, ge=1, le=500, description="Max nodes to return"),
    entity_types: list[str] | None = Query(None, description="Filter by entity types"),
    relationship_types: list[str] | None = Query(None, description="Filter by relationship types"),
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
        raise HTTPException(
            status_code=400,
            detail="Either 'query' or 'center_entity_id' parameter is required",
        )

    tenant_id = _extract_tenant_id(request)
    if not tenant_id:
        raise HTTPException(
            status_code=400, detail="tenant_id is required for graph explorer access"
        )

    neo4j = app_state.neo4j_driver
    nodes: list[GraphNode | GraphNodeWithLayout] = []
    edges: list[GraphEdge] = []
    root_id = center_entity_id or ""

    try:
        if center_entity_id:
            root_result = await neo4j.execute_query(
                "MATCH (root {id: $entity_id, tenant_id: $tenant_id}) RETURN root",
                {"entity_id": center_entity_id, "tenant_id": tenant_id},
            )
            if not root_result:
                raise HTTPException(
                    status_code=404, detail=f"Entity {center_entity_id} not found"
                )

            # Build query params; depth and rel_types are always parameterised
            # to prevent Cypher injection regardless of upstream validation.
            query_params: dict[str, Any] = {
                "entity_id": center_entity_id,
                "tenant_id": tenant_id,
                "depth": depth,
                "limit": limit,
            }

            rel_filter = ""
            if relationship_types:
                validated = [r for r in relationship_types if _VALID_REL_TYPE.match(r)]
                if validated:
                    rel_filter = (
                        "AND ALL(r IN relationships(path) WHERE type(r) IN $rel_types)"
                    )
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
            result = await neo4j.execute_query(subgraph_query, query_params)

            if result:
                record = result[0]
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
                                    GraphEdge(source=src, target=tgt, type=rel.type, properties={})
                                )

        else:
            search_results = await hybrid_search.search(
                query=query,
                top_k=min(limit, 50),
                entity_type_filter=entity_types[0] if entity_types else None,
            )

            if not search_results:
                return SubgraphResponse(
                    root_entity_id="",
                    nodes=[],
                    edges=[],
                    depth=depth,
                    stats=GraphStats(total_nodes=0, total_edges=0, density=0.0),
                )

            seed_ids = [r.entity_id for r in search_results if r.entity_id]
            if not seed_ids:
                return SubgraphResponse(
                    root_entity_id="",
                    nodes=[],
                    edges=[],
                    depth=depth,
                    stats=GraphStats(total_nodes=0, total_edges=0, density=0.0),
                )

            result = await neo4j.execute_query(
                """
                UNWIND $seed_ids as seed_id
                MATCH (seed {id: seed_id, tenant_id: $tenant_id})
                OPTIONAL MATCH (seed)-[r]-(neighbor {tenant_id: $tenant_id})
                WHERE neighbor.id IS NOT NULL
                RETURN seed, collect(DISTINCT neighbor) as neighbors,
                       collect(DISTINCT r) as rels
                """,
                {"seed_ids": seed_ids[:20], "tenant_id": tenant_id},
            )

            node_ids: set[str] = set()
            for record in result:
                seed = record.get("seed")
                neighbors = record.get("neighbors", [])
                rels = record.get("rels", [])

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

        n = len(nodes)
        e = len(edges)
        density = 0.0 if n <= 1 else (2 * e) / (n * (n - 1))

        return SubgraphResponse(
            root_entity_id=root_id,
            nodes=nodes,
            edges=edges,
            depth=depth,
            stats=GraphStats(total_nodes=n, total_edges=e, density=density),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve subgraph: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve subgraph: {str(e)}"
        )
