from value_fabric.shared.error_handling.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Value Tree API routes.

Provides endpoints for traversing and retrieving the 4-layer value tree:
- Capability -> UseCase -> Persona -> ValueDriver
"""

import asyncio
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field

from ...api.dependencies import AppState, _extract_tenant_id, get_app_state
from ...db.query_execution import (
    MAX_QUERY_DEPTH,
    QUERY_TIMEOUT_SECONDS,
    CypherDepthLimitExceeded,
)
from ...graph.query_guards import sanitize_query_depth, sanitize_query_timeout_seconds

router = APIRouter()


class ValueTreeNode(BaseModel):
    """Node in the value tree."""

    id: str = Field(..., description="Entity ID")
    label: str = Field(..., description="Display name")
    type: str = Field(
        ..., description="Entity type (Capability, UseCase, Persona, ValueDriver)"
    )
    layer: int = Field(
        ..., ge=1, le=4, description="Layer in value tree (1=Capability, 4=ValueDriver)"
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)


class ValueTreeEdge(BaseModel):
    """Edge connecting nodes in the value tree."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type (ENABLES, BENEFITS, DRIVES)")
    weight: float = Field(default=1.0, ge=0.0)


class ValueTreeStats(BaseModel):
    """Statistics for the value tree."""

    total_nodes: int = Field(..., ge=0)
    total_edges: int = Field(..., ge=0)
    by_layer: dict[str, int] = Field(default_factory=dict)
    max_depth: int = Field(default=0)


class ValueTreeResponse(BaseModel):
    """Complete value tree response."""

    root_entity_id: str = Field(..., description="ID of the starting entity")
    direction: Literal["upward", "downward"] = Field(
        ..., description="Traversal direction"
    )
    nodes: list[ValueTreeNode] = Field(..., description="All nodes in the tree")
    edges: list[ValueTreeEdge] = Field(..., description="All edges in the tree")
    paths: list[dict[str, Any]] = Field(
        default_factory=list, description="Value tree paths"
    )
    stats: ValueTreeStats = Field(..., description="Tree statistics")


@router.get(
    "/value-trees/{entity_id}",
    response_model=ValueTreeResponse,
    tags=["Value Trees"],
    summary="Get Value Tree",
    description="Returns the resolved value tree starting from the specified entity.",
    responses={
        200: {
            "description": "Value tree retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "root_entity_id": "cap-1",
                        "direction": "upward",
                        "nodes": [
                            {
                                "id": "cap-1",
                                "label": "CRM Integration",
                                "type": "Capability",
                                "layer": 1,
                            },
                            {
                                "id": "uc-1",
                                "label": "Pipeline Forecast",
                                "type": "UseCase",
                                "layer": 2,
                            },
                        ],
                        "edges": [
                            {"source": "cap-1", "target": "uc-1", "type": "ENABLES"}
                        ],
                        "stats": {
                            "total_nodes": 15,
                            "total_edges": 14,
                            "by_layer": {"1": 3, "2": 5, "3": 4, "4": 3},
                        },
                    }
                }
            },
        },
        404: {"description": "Entity not found"},
    },
)
async def get_value_tree(
    entity_id: str,
    direction: Literal["upward", "downward"] = "upward",
    max_depth: int = 4,
    app_state: AppState = Depends(get_app_state),
    request: Request = None,
) -> ValueTreeResponse:
    """Get the value tree starting from a specific entity.

    - **entity_id**: ID of the starting entity
    - **direction**: upward (Capability -> ValueDriver) or downward (ValueDriver -> Capability)
    - **max_depth**: Maximum traversal depth (1-4)
    """
    try:
        neo4j = app_state.neo4j_driver
        if not neo4j:
            raise ServiceUnavailableError(message = "Neo4j not available")

        # Extract tenant_id for multi-tenant security
        tenant_id = _extract_tenant_id(request)
        if not tenant_id:
            raise ValidationError(message = "tenant_id is required for value tree access")

        # Clamp depth to global limit
        max_depth = sanitize_query_depth(max_depth, default_depth=4)

        # Verify entity exists with mandatory tenant filtering
        root_query = """
        MATCH (n {id: $entity_id, tenant_id: $tenant_id})
        RETURN n.id as id, n.name as label, n.type as type, n.confidence as confidence
        """
        root_result = await asyncio.wait_for(
            neo4j.execute_query(root_query, {"entity_id": entity_id, "tenant_id": tenant_id}),
            timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
        )
        if not root_result:
            raise NotFoundError(message = str(f"Entity {entity_id} not found"))

        root = root_result[0]
        root_type = root.get("type", "Unknown")

        # Determine layer for root
        layer_map = {"Capability": 1, "UseCase": 2, "Persona": 3, "ValueDriver": 4}
        root_layer = layer_map.get(root_type, 1)

        # Build traversal query based on direction with mandatory tenant filtering
        if direction == "upward":
            # Traverse: Capability -(ENABLES)-> UseCase -(BENEFITS)-> Persona -(DRIVES)-> ValueDriver
            path_query = """
            MATCH path = (start {id: $entity_id, tenant_id: $tenant_id})-[:ENABLES|BENEFITS|DRIVES*1..$max_depth]->(target {tenant_id: $tenant_id})
            WHERE target.id IS NOT NULL
            RETURN start, target, relationships(path) as rels, nodes(path) as path_nodes,
                   length(path) as path_length
            """
        else:
            # Downward: ValueDriver <-(DRIVES)- Persona <-(BENEFITS)- UseCase <-(ENABLES)- Capability
            path_query = """
            MATCH path = (start {id: $entity_id, tenant_id: $tenant_id})<-[:ENABLES|BENEFITS|DRIVES*1..$max_depth]-(target {tenant_id: $tenant_id})
            WHERE target.id IS NOT NULL
            RETURN start, target, relationships(path) as rels, nodes(path) as path_nodes,
                   length(path) as path_length
            """

        path_result = await asyncio.wait_for(
            neo4j.execute_query(
                path_query, {"entity_id": entity_id, "max_depth": max_depth, "tenant_id": tenant_id}
            ),
            timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
        )

        # Collect nodes and edges
        nodes_map: dict[str, ValueTreeNode] = {}
        edges_map: dict[str, ValueTreeEdge] = {}
        by_layer: dict[str, int] = {}

        # Add root node
        nodes_map[entity_id] = ValueTreeNode(
            id=entity_id,
            label=root.get("label") or entity_id,
            type=root_type,
            layer=root_layer,
            confidence=root.get("confidence") or 0.8,
            properties={"is_root": True},
        )
        by_layer[str(root_layer)] = by_layer.get(str(root_layer), 0) + 1

        paths = []
        max_path_length = 0

        for r in path_result:
            path_nodes_data = r.get("path_nodes", [])
            rels = r.get("rels", [])
            path_length = r.get("path_length", 0)
            max_path_length = max(max_path_length, path_length)

            # Process nodes in path
            for i, node_data in enumerate(path_nodes_data):
                if not node_data or not node_data.get("id"):
                    continue

                node_id = node_data.get("id")
                node_type = node_data.get("type", "Unknown")
                node_layer = layer_map.get(node_type, 1)

                if node_id not in nodes_map:
                    by_layer[str(node_layer)] = by_layer.get(str(node_layer), 0) + 1
                    nodes_map[node_id] = ValueTreeNode(
                        id=node_id,
                        label=node_data.get("name") or node_id,
                        type=node_type,
                        layer=node_layer,
                        confidence=node_data.get("confidence") or 0.8,
                        properties={},
                    )

            # Process relationships
            for rel in rels:
                start_id = rel.get("start_node", {}).get("id")
                end_id = rel.get("end_node", {}).get("id")
                rel_type = rel.get("type", "RELATED_TO")

                if start_id and end_id:
                    edge_key = f"{start_id}-{end_id}-{rel_type}"
                    if edge_key not in edges_map:
                        edges_map[edge_key] = ValueTreeEdge(
                            source=start_id,
                            target=end_id,
                            type=rel_type,
                            weight=rel.get("weight", 1.0),
                        )

            # Build path structure
            if path_length > 0:
                paths.append(
                    {
                        "length": path_length,
                        "nodes": [n.get("id") for n in path_nodes_data if n],
                    }
                )

        nodes = list(nodes_map.values())
        edges = list(edges_map.values())

        stats = ValueTreeStats(
            total_nodes=len(nodes),
            total_edges=len(edges),
            by_layer=by_layer,
            max_depth=max_path_length,
        )

        return ValueTreeResponse(
            root_entity_id=entity_id,
            direction=direction,
            nodes=nodes,
            edges=edges,
            paths=paths,
            stats=stats,
        )

    except HTTPException:
        raise
    except CypherDepthLimitExceeded as exc:
        logger.warning("Cypher depth limit exceeded: %s", exc)
        raise ValidationError(message = "Query depth limit exceeded (code: CYPHER_DEPTH_LIMIT_EXCEEDED)") from exc
    except TimeoutError:
        raise ValidationError(message = "Query timed out after 30s (code: CYPHER_TIMEOUT)")
    except Exception as e:
        logger.error("Failed to retrieve value tree: %s", e)
        raise ServiceUnavailableError(message="Failed to retrieve value tree") from e


@router.get(
    "/value-trees/{entity_id}/paths",
    response_model=list[dict[str, Any]],
    tags=["Value Trees"],
    summary="Get Value Tree Paths",
    description="Returns all paths from the entity to value drivers (upward) or capabilities (downward).",
)
async def get_value_tree_paths(
    entity_id: str,
    direction: Literal["upward", "downward"] = "upward",
    max_depth: int = 4,
    app_state: AppState = Depends(get_app_state),
    request: Request = None,
) -> list[dict[str, Any]]:
    """Get all value tree paths from a starting entity."""
    try:
        neo4j = app_state.neo4j_driver
        if not neo4j:
            raise ServiceUnavailableError(message = "Neo4j not available")

        # Extract tenant_id for multi-tenant security
        tenant_id = _extract_tenant_id(request)
        if not tenant_id:
            raise ValidationError(message = "tenant_id is required for value tree access")

        max_depth = sanitize_query_depth(max_depth, default_depth=4)

        if direction == "upward":
            query = """
            MATCH path = (start {id: $entity_id, tenant_id: $tenant_id})-[:ENABLES|BENEFITS|DRIVES*1..$max_depth]->(target:ValueDriver {tenant_id: $tenant_id})
            RETURN [node in nodes(path) | {id: node.id, name: node.name, type: node.type}] as path_nodes,
                   length(path) as path_length
            """
        else:
            query = """
            MATCH path = (start {id: $entity_id, tenant_id: $tenant_id})<-[:ENABLES|BENEFITS|DRIVES*1..$max_depth]-(target:Capability {tenant_id: $tenant_id})
            RETURN [node in nodes(path) | {id: node.id, name: node.name, type: node.type}] as path_nodes,
                   length(path) as path_length
            """

        result = await asyncio.wait_for(
            neo4j.execute_query(
                query, {"entity_id": entity_id, "max_depth": max_depth, "tenant_id": tenant_id}
            ),
            timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS),
        )

        paths = []
        for r in result:
            paths.append(
                {
                    "nodes": r.get("path_nodes", []),
                    "length": r.get("path_length", 0),
                }
            )

        return paths

    except HTTPException:
        raise
    except CypherDepthLimitExceeded as exc:
        logger.warning("Cypher depth limit exceeded: %s", exc)
        raise ValidationError(message = "Query depth limit exceeded (code: CYPHER_DEPTH_LIMIT_EXCEEDED)") from exc
    except TimeoutError:
        raise ValidationError(message = "Query timed out after 30s (code: CYPHER_TIMEOUT)")
    except Exception as e:
        logger.error("Failed to retrieve value tree paths: %s", e)
        raise ServiceUnavailableError(message="Failed to retrieve paths") from e
