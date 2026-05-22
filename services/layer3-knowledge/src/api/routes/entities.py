"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Entity API routes - Canonical Entity Browser endpoints.

This module provides the canonical entity browser API as specified in
the Value Fabric API contract. It exposes endpoints for:
- Listing entities with filtering and search
- Getting detailed entity information
- Querying entities with Cypher-like filters

These endpoints have been refactored from main.py as part of the
architectural decomposition effort (Weakness #3).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from value_fabric.shared.identity import RequestContext, require_authenticated
from value_fabric.shared.identity.isolation import TenantScopedCypher

from logging_config import get_logger

from ...api.dependencies import (
    AppState,
    get_app_state,
    get_graph_rag,
)
from ...api.dependencies_tenant_secured import (
    Neo4jTenantSessionSecured as Neo4jTenantSession,
    get_neo4j_secured as get_neo4j_with_tenant,
)
from ...api.exception_mapping import map_exception_to_http_error
from ...api.exceptions import DatabaseError, ValidationError
from ...api.models import (
    EntityDetail,
    EntityFilterRequest,
    EntityListResponse,
    EntitySummary,
    ValueTreeResponse,
    ValueTreeTraversal,
)

router = APIRouter(prefix="/v1", tags=["Entities"], dependencies=[Depends(require_authenticated)])
logger = get_logger(__name__)
ENTITY_LIST_SORT_CLAUSES = {
    ("confidence", "asc"): "e.confidence_score ASC",
    ("confidence", "desc"): "e.confidence_score DESC",
    ("name", "asc"): "e.name ASC",
    ("name", "desc"): "e.name DESC",
    ("created_at", "asc"): "e.created_at ASC",
    ("created_at", "desc"): "e.created_at DESC",
}

def entity_list_sort_clause(sort_by: str, sort_order: str) -> str:
    """Resolve sort clause from a closed allowlist.

    Cypher does not support parameterised identifiers or direction, so this
    is the only string-substitution point remaining in the query pipeline.
    It is sourced exclusively from ENTITY_LIST_SORT_CLAUSES; any unknown
    combination safely falls back to the default.
    """
    return ENTITY_LIST_SORT_CLAUSES.get((sort_by, sort_order.lower()), "e.confidence_score DESC")


def _map_results_to_summaries(results: list[dict[str, Any]]) -> list[EntitySummary]:
    """Map raw Cypher result rows to canonical EntitySummary objects."""
    return [
        EntitySummary(
            id=row["id"],
            name=row["name"] or "Unnamed Entity",
            description=row["description"],
            entity_type=row["entity_type"],
            confidence=row["confidence_score"] or 0.0,
            updated_at=row["created_at"],
        )
        for row in results
    ]


@router.get("/entities", response_model=EntityListResponse)
async def list_entities(
    search_text: str | None = Query(None, max_length=200, description="Search across name and description"),
    entity_types: list[str] | None = Query(None, description="Filter by entity types"),
    confidence_min: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("confidence", description="Sort field: confidence, name, created_at"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    _ctx: RequestContext = Depends(require_authenticated),
    neo4j: Neo4jTenantSession = Depends(get_neo4j_with_tenant),
) -> EntityListResponse:
    """List entities with optional filtering and pagination.

    This is the canonical entity browser endpoint per the Value Fabric API spec.
    Returns high-quality entity summaries with consistent field naming.
    """
    try:
        sort_clause = entity_list_sort_clause(sort_by, sort_order)

        # Single query: count and paginated data in one round-trip.
        # The CALL {} subquery is evaluated independently; the outer MATCH
        # returns paginated rows each carrying the pre-computed total.
        params: dict[str, Any] = {
            "search_text": search_text,
            "entity_types": entity_types,
            "confidence_min": confidence_min,
            "offset": offset,
            "limit": limit,
        }
        builder = TenantScopedCypher(neo4j.tenant_id or "")
        scoped_query = builder.custom_tenant_query(
            """
            CALL {
                MATCH (e:Entity)
                WHERE e.tenant_id = $_tenant_id
                  AND ($search_text IS NULL OR toLower(e.name) CONTAINS toLower($search_text) OR toLower(e.description) CONTAINS toLower($search_text))
                  AND ($entity_types IS NULL OR e.entity_type IN $entity_types)
                  AND e.confidence_score >= $confidence_min
                RETURN count(e) as total
            }
            MATCH (e:Entity)
            WHERE e.tenant_id = $_tenant_id
              AND ($search_text IS NULL OR toLower(e.name) CONTAINS toLower($search_text) OR toLower(e.description) CONTAINS toLower($search_text))
              AND ($entity_types IS NULL OR e.entity_type IN $entity_types)
              AND e.confidence_score >= $confidence_min
            RETURN e.id as id,
                   e.name as name,
                   e.description as description,
                   e.entity_type as entity_type,
                   e.confidence_score as confidence_score,
                   e.created_at as created_at,
                   total
            ORDER BY __SORT_CLAUSE__
            SKIP $offset
            LIMIT $limit
        """.replace("__SORT_CLAUSE__", sort_clause),
            params=params,
            operation="entity_list",
            labels=("Entity",),
        )
        params = dict(scoped_query.params)

        results = await neo4j.execute_query(scoped_query, params)
        total = results[0]["total"] if results else 0

        return EntityListResponse(
            results=_map_results_to_summaries(results),
            total_count=total,
            filtered_count=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(results)) < total,
            available_domains=[],
            available_sources=[],
        )

    except (ValidationError, DatabaseError) as exc:
        context = {"tenant": getattr(neo4j, "tenant_id", "unknown"), "endpoint": "/v1/entities", "operation": "list_entities"}
        logger.warning("Entity listing mapped exception", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except Exception as exc:
        context = {"tenant": getattr(neo4j, "tenant_id", "unknown"), "endpoint": "/v1/entities", "operation": "list_entities"}
        logger.error("Entity listing failed", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)


@router.get("/entities/{entity_id}", response_model=EntityDetail)
async def get_entity_detail(
    entity_id: str,
    include_provenance: bool = Query(True, description="Include provenance chain"),
    include_relationships: bool = Query(True, description="Include related entities"),
    _ctx: RequestContext = Depends(require_authenticated),
    neo4j: Neo4jTenantSession = Depends(get_neo4j_with_tenant),
    app_state: AppState = Depends(get_app_state),
) -> EntityDetail:
    """Get detailed information about a specific entity.

    Returns complete entity details including properties, provenance,
    and optionally related entities and their relationships.
    """
    try:
        # Get entity node
        entity_query = """
            MATCH (e:Entity {id: $entity_id, tenant_id: $tenant_id})
            RETURN e
        """
        entity_result = await neo4j.execute_query(entity_query, {"entity_id": entity_id})

        if not entity_result:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        entity_node = entity_result[0]["e"]

        # Get properties
        properties = dict(entity_node)

        # Get provenance if requested
        provenance = None
        if include_provenance:
            prov_query = """
                MATCH (e:Entity {id: $entity_id, tenant_id: $tenant_id})-[:DERIVED_FROM]->(source:Source {tenant_id: $tenant_id})
                RETURN source
            """
            prov_result = await neo4j.execute_query(prov_query, {"entity_id": entity_id})
            if prov_result:
                source_node = prov_result[0]["source"]
                provenance = {
                    "source_id": source_node.get("id"),
                    "source_type": source_node.get("source_type"),
                    "extraction_method": source_node.get("extraction_method"),
                    "extracted_at": source_node.get("extracted_at"),
                    "confidence": source_node.get("confidence_score"),
                }

        # Get relationships if requested
        relationships = []
        if include_relationships:
            rel_query = """
                MATCH (e:Entity {id: $entity_id, tenant_id: $tenant_id})-[r]-(other:Entity {tenant_id: $tenant_id})
                RETURN other.id as related_id,
                       other.name as related_name,
                       other.entity_type as related_type,
                       type(r) as relationship_type,
                       r.confidence_score as rel_confidence
                LIMIT 20
            """
            rel_results = await neo4j.execute_query(rel_query, {"entity_id": entity_id})
            relationships = [
                {
                    "entity_id": row["related_id"],
                    "name": row["related_name"],
                    "entity_type": row["related_type"],
                    "relationship": row["relationship_type"],
                    "confidence": row["rel_confidence"] or 0.0,
                }
                for row in rel_results
            ]

        return EntityDetail(
            id=entity_id,
            name=entity_node.get("name", "Unnamed Entity"),
            description=entity_node.get("description"),
            entity_type=entity_node.get("entity_type", "unknown"),
            confidence_score=entity_node.get("confidence_score", 0.0),
            properties=properties,
            provenance=provenance,
            related_entities=relationships,
            created_at=entity_node.get("created_at"),
            updated_at=entity_node.get("updated_at"),
        )

    except HTTPException:
        raise
    except (ValidationError, DatabaseError) as exc:
        context = {"tenant": getattr(neo4j, "tenant_id", "unknown"), "endpoint": f"/v1/entities/{entity_id}", "operation": "get_entity_detail"}
        logger.warning("Entity detail mapped exception", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except Exception as exc:
        context = {"tenant": getattr(neo4j, "tenant_id", "unknown"), "endpoint": f"/v1/entities/{entity_id}", "operation": "get_entity_detail"}
        logger.error("Entity detail retrieval failed", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)


@router.post("/entities/query", response_model=EntityListResponse)
async def query_entities(
    request: EntityFilterRequest,
    _ctx: RequestContext = Depends(require_authenticated),
    neo4j: Neo4jTenantSession = Depends(get_neo4j_with_tenant),
) -> EntityListResponse:
    """Query entities using Cypher-like filter conditions.

    Supports complex filtering with multiple conditions, logical operators,
    and custom sorting.
    """
    try:
        params: dict[str, Any] = {"limit": request.limit or 20, "offset": request.offset or 0}
        params["entity_types"] = request.entity_types
        params["confidence_min"] = request.min_confidence
        params["confidence_max"] = request.max_confidence
        builder = TenantScopedCypher(neo4j.tenant_id or "")
        scoped_count = builder.custom_tenant_query(
            """
            MATCH (e:Entity)
            WHERE e.tenant_id = $_tenant_id
              AND ($entity_types IS NULL OR e.entity_type IN $entity_types)
              AND ($confidence_min IS NULL OR e.confidence_score >= $confidence_min)
              AND ($confidence_max IS NULL OR e.confidence_score <= $confidence_max)
            RETURN count(e) as total
        """,
            params={k: v for k, v in params.items() if k not in ("limit", "offset")},
            operation="entity_query_count",
            labels=("Entity",),
        )

        # Execute count query for accurate pagination metadata
        count_results = await neo4j.execute_query(scoped_count, scoped_count.params)
        total_count = count_results[0]["total"] if count_results else 0

        # Execute paginated data query
        scoped_list = builder.custom_tenant_query(
            """
            MATCH (e:Entity)
            WHERE e.tenant_id = $_tenant_id
              AND ($entity_types IS NULL OR e.entity_type IN $entity_types)
              AND ($confidence_min IS NULL OR e.confidence_score >= $confidence_min)
              AND ($confidence_max IS NULL OR e.confidence_score <= $confidence_max)
            RETURN e.id as id,
                   e.name as name,
                   e.description as description,
                   e.entity_type as entity_type,
                   e.confidence_score as confidence_score,
                   e.created_at as created_at
            ORDER BY e.confidence_score DESC
            SKIP $offset
            LIMIT $limit
        """,
            params=params,
            operation="entity_query_list",
            labels=("Entity",),
        )

        results = await neo4j.execute_query(scoped_list, scoped_list.params)

        return EntityListResponse(
            results=_map_results_to_summaries(results),
            total_count=total_count,
            filtered_count=total_count,
            limit=request.limit or 20,
            offset=request.offset or 0,
            has_more=(request.offset or 0) + len(results) < total_count,
            available_domains=[],
            available_sources=[],
        )

    except (ValidationError, DatabaseError) as exc:
        context = {"tenant": getattr(neo4j, "tenant_id", "unknown"), "endpoint": "/v1/entities/query", "operation": "query_entities"}
        logger.warning("Entity query mapped exception", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except Exception as exc:
        context = {"tenant": getattr(neo4j, "tenant_id", "unknown"), "endpoint": "/v1/entities/query", "operation": "query_entities"}
        logger.error("Entity query failed", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)


@router.post("/entity/traverse", response_model=ValueTreeResponse)
async def traverse_value_tree(
    request: ValueTreeTraversal,
    _ctx: RequestContext = Depends(require_authenticated),
    graph_rag=Depends(get_graph_rag),
) -> ValueTreeResponse:
    """Traverse the value tree starting from a root entity.

    Performs graph traversal to find value-related entities and their
    relationships, returning a structured tree representation.
    """
    try:
        result = await graph_rag.traverse_value_tree(
            root_entity_id=request.root_entity_id,
            max_depth=request.max_depth,
            relationship_types=request.relationship_types,
        )

        return ValueTreeResponse(
            root_id=request.root_entity_id,
            tree_data=result.get("tree_data", {}),
            entities=result.get("entities", []),
            total_value=result.get("total_value"),
        )

    except (ValidationError, DatabaseError) as exc:
        context = {"tenant": getattr(graph_rag, "tenant_id", "unknown"), "endpoint": "/v1/entity/traverse", "operation": "traverse_value_tree"}
        logger.warning("Value tree traversal mapped exception", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except Exception as exc:
        context = {"tenant": getattr(graph_rag, "tenant_id", "unknown"), "endpoint": "/v1/entity/traverse", "operation": "traverse_value_tree"}
        logger.error("Value tree traversal failed for %s", request.root_entity_id, extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
