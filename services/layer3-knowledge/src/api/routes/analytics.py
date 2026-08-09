from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""Analytics domain router — community detection, centrality, similarity, batch ops.

Migrated from app_monolith.py as part of ARCH-L3-011 (Sprint 3 cutover).
All write-paths that touch Neo4j directly use tenant_id extracted from the
authenticated request context; the cypher_security allowlist is enforced
via the shared TenantScopedCypher utility.
"""


import logging
import uuid
from datetime import datetime
from typing import Any

import neo4j
from fastapi import APIRouter, Depends, HTTPException, Request

from ...api.dependencies import (
    get_centrality_analyzer,
    get_community_detector,
    get_graph_rag,
    get_neo4j_driver,
    get_similarity_analyzer,
)
from ...api.models import (
    BatchAnalyticsRequest,
    BatchAnalyticsResponse,
    BatchAnalyticsResult,
    BatchEntityOperation,
    BatchEntityRequest,
    BatchEntityResponse,
    BatchEntityResult,
    CentralityRequest,
    CentralityResponse,
    Community,
    CommunityDetectionRequest,
    CommunityDetectionResponse,
    EntityComparisonRequest,
    EntityComparisonResponse,
    SimilarityRequest,
    SimilarityResponse,
)
from ...db.audited_mutation import AuditedGraphMutation
from ...db.query_execution import run_validated_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Analytics"])


def _extract_tenant_id(request: Request | None) -> str | None:
    """Extract tenant_id from authenticated request context."""
    if not request:
        return None
    ctx = getattr(request.state, "context", None)
    if ctx and getattr(ctx, "tenant_id", None):
        return str(ctx.tenant_id)
    return None


# ---------------------------------------------------------------------------
# Community / Centrality / Similarity
# ---------------------------------------------------------------------------


@router.post("/analytics/communities", response_model=CommunityDetectionResponse)
async def detect_communities(
    request: CommunityDetectionRequest,
    community_detector=Depends(get_community_detector),
) -> CommunityDetectionResponse:
    """Detect communities in the knowledge graph."""
    try:
        if request.algorithm == "louvain":
            result = await community_detector.detect_louvain(
                node_labels=request.entity_types,
                relationship_types=request.relationship_types,
                min_community_size=request.min_community_size,
            )
        elif request.algorithm == "leiden":
            result = await community_detector.detect_leiden(
                node_labels=request.entity_types,
                relationship_types=request.relationship_types,
                min_community_size=request.min_community_size,
            )
        elif request.algorithm == "value_tree":
            result = await community_detector.detect_by_value_tree()
        else:
            raise ValidationError(
                message=str(f"Unknown algorithm: {request.algorithm}")
            )

        return CommunityDetectionResponse(
            algorithm=result["algorithm"],
            total_communities=result["total_communities"],
            valid_communities=result.get(
                "valid_communities", result["total_communities"]
            ),
            total_nodes=result.get("total_nodes", 0),
            communities=[
                Community(id=c["id"], size=c["size"], members=c["members"])
                for c in result["communities"]
            ],
            modularity=result.get("modularity"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Community detection failed: %s", e)
        raise ServiceUnavailableError(
            message="Community detection failed. Please try again later."
        )


@router.post("/analytics/centrality", response_model=CentralityResponse)
async def calculate_centrality(
    request: CentralityRequest,
    centrality_analyzer=Depends(get_centrality_analyzer),
) -> CentralityResponse:
    """Calculate centrality metrics for entities."""
    try:
        if request.algorithm == "pagerank":
            result = await centrality_analyzer.calculate_pagerank(
                node_labels=request.entity_types,
                top_k=request.top_k,
            )
        elif request.algorithm == "betweenness":
            result = await centrality_analyzer.calculate_betweenness(
                node_labels=request.entity_types,
                top_k=request.top_k,
            )
        elif request.algorithm == "degree":
            result = await centrality_analyzer.calculate_degree_centrality(
                node_labels=request.entity_types,
                top_k=request.top_k,
            )
        elif request.algorithm == "value_tree":
            result = await centrality_analyzer.get_value_tree_centrality()
        else:
            raise ValidationError(
                message=str(f"Unknown algorithm: {request.algorithm}")
            )

        return CentralityResponse(
            algorithm=result["algorithm"],
            total_ranked=result["total_ranked"],
            top_entities=result["top_entities"],
            by_layer=result.get("by_layer"),
            key_connectors=result.get("key_connectors"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Centrality calculation failed: %s", e)
        raise ServiceUnavailableError(
            message="Centrality calculation failed. Please try again later."
        )


@router.post("/analytics/similar", response_model=SimilarityResponse)
async def find_similar_entities(
    request: SimilarityRequest,
    similarity_analyzer=Depends(get_similarity_analyzer),
) -> SimilarityResponse:
    """Find similar entities using multiple methods."""
    try:
        if request.target_type:
            results = await similarity_analyzer.find_similar_by_type(
                entity_id=request.entity_id,
                target_type=request.target_type,
                top_k=request.top_k,
            )
        else:
            results = await similarity_analyzer.find_similar(
                entity_id=request.entity_id,
                method=request.method,
                top_k=request.top_k,
            )

        return SimilarityResponse(
            entity_id=request.entity_id,
            method=request.method,
            similar_entities=results,
        )
    except Exception as e:
        logger.error("Similarity analysis failed: %s", e)
        raise ServiceUnavailableError(
            message="Similarity analysis failed. Please try again later."
        )


@router.post("/analytics/compare", response_model=EntityComparisonResponse)
async def compare_entities(
    request: EntityComparisonRequest,
    similarity_analyzer=Depends(get_similarity_analyzer),
) -> EntityComparisonResponse:
    """Compare two entities and return similarity metrics."""
    try:
        result = await similarity_analyzer.compare_entities(
            entity_id1=request.entity_id1,
            entity_id2=request.entity_id2,
        )
        if "error" in result:
            raise NotFoundError(message=str(result["error"]))

        return EntityComparisonResponse(
            entity1=result["entity1"],
            entity2=result["entity2"],
            same_type=result["same_type"],
            jaccard_similarity=result["jaccard_similarity"],
            common_neighbors=result["common_neighbors"],
            path_info=result["path_info"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Entity comparison failed: %s", e)
        raise ServiceUnavailableError(
            message="Entity comparison failed. Please try again later."
        )


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------


async def _create_entity(
    driver: Any, operation: BatchEntityOperation, tenant_id: str | None
) -> dict[str, Any]:
    """Create a single tenant-scoped entity through the audited mutation gateway."""
    if not tenant_id:
        return {"success": False, "error": "tenant_id is required for entity creation"}

    try:
        entity_id = str(uuid.uuid4())
        properties = dict(operation.properties or {})
        properties["entity_type"] = (
            operation.entity_type.value if operation.entity_type else "Unknown"
        )
        properties["created_at"] = datetime.utcnow().isoformat()

        async with driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="analytics._create_entity",
            )
            await mutation.write_node("Entity", entity_id, properties)

        return {"success": True, "entity_id": entity_id}
    except (neo4j.exceptions.DriverError, neo4j.exceptions.DatabaseError, ValueError) as e:
        logger.exception("Entity creation failed", error=str(e))
        return {"success": False, "error": "ENTITY_CREATE_ERROR"}


async def _update_entity(
    driver: Any, operation: BatchEntityOperation, tenant_id: str | None
) -> dict[str, Any]:
    """Update a single tenant-scoped entity and emit audit metadata."""
    if not tenant_id:
        return {"success": False, "error": "tenant_id is required for entity updates"}
    if not operation.entity_id:
        return {"success": False, "error": "entity_id is required for entity updates"}

    try:
        if not await _snapshot_entity(driver, operation.entity_id, tenant_id):
            return {"success": False, "error": "Entity not found"}

        async with driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="analytics._update_entity",
            )
            await mutation.write_node(
                "Entity", operation.entity_id, operation.properties or {}
            )

        return {"success": True}
    except (neo4j.exceptions.DriverError, neo4j.exceptions.DatabaseError, ValueError) as e:
        logger.exception("Entity update failed for %s", operation.entity_id, error=str(e))
        return {"success": False, "error": "ENTITY_UPDATE_ERROR"}


async def _delete_entity(
    driver: Any, operation: BatchEntityOperation, tenant_id: str | None
) -> dict[str, Any]:
    """Delete a single tenant-scoped entity through the audited mutation gateway."""
    if not tenant_id:
        return {"success": False, "error": "tenant_id is required for entity deletion"}
    if not operation.entity_id:
        return {"success": False, "error": "entity_id is required for entity deletion"}

    try:
        if not await _snapshot_entity(driver, operation.entity_id, tenant_id):
            return {"success": False, "error": "Entity not found"}

        async with driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="analytics._delete_entity",
            )
            await mutation.delete_node("Entity", operation.entity_id)

        return {"success": True}
    except (neo4j.exceptions.DriverError, neo4j.exceptions.DatabaseError, ValueError) as e:
        logger.exception("Entity deletion failed for %s", operation.entity_id, error=str(e))
        return {"success": False, "error": "ENTITY_DELETE_ERROR"}


async def _delete_entity_by_id(
    driver: Any, entity_id: str, tenant_id: str | None
) -> None:
    """Delete entity by ID (used for atomic rollback)."""
    if not tenant_id:
        raise ValueError("tenant_id is required for entity deletion")
    async with driver.session() as session:
        mutation = AuditedGraphMutation(
            tenant_id=tenant_id,
            session=session,
            operation_source="analytics._delete_entity_by_id",
        )
        await mutation.delete_node("Entity", entity_id)


async def _snapshot_entity(
    driver: Any, entity_id: str, tenant_id: str
) -> dict[str, Any] | None:
    """Capture a node's current properties for rollback purposes."""
    try:
        async with driver.session() as session:
            result = await run_validated_query(
                session,
                "MATCH (n:Entity {id: $entity_id, tenant_id: $tenant_id}) RETURN properties(n) as props",
                {"entity_id": entity_id, "tenant_id": tenant_id},
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="analytics.snapshot_entity",
            )
            record = await result.single()
            return dict(record["props"]) if record else None
    except Exception as e:
        logger.warning("Could not snapshot entity %s for rollback: %s", entity_id, e)
        return None


async def _restore_entity(
    driver: Any, entity_id: str, snapshot: dict[str, Any], tenant_id: str
) -> None:
    """Restore a node to a previously captured snapshot."""
    try:
        async with driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="analytics._restore_entity",
            )
            await mutation.write_node("Entity", entity_id, snapshot)
    except Exception as e:
        logger.error("Rollback restore failed for entity %s: %s", entity_id, e)


async def _recreate_entity(
    driver: Any, snapshot: dict[str, Any], tenant_id: str
) -> None:
    """Re-create an entity deleted earlier in an atomic batch."""
    try:
        node_id = str(snapshot.get("id") or "")
        if not node_id:
            raise ValueError("snapshot id is required to recreate entity")

        async with driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="analytics._recreate_entity",
            )
            await mutation.write_node("Entity", node_id, snapshot)
    except Exception as e:
        logger.error(
            "Rollback re-create failed for entity %s: %s",
            snapshot.get("id"),
            e,
        )


@router.post("/batch/entities", response_model=BatchEntityResponse)
async def batch_entity_operations(
    request: BatchEntityRequest,
    fastapi_request: Request,
    neo4j_driver=Depends(get_neo4j_driver),
) -> BatchEntityResponse:
    """Execute batch entity operations (create/update/delete).

    Supports atomic mode where all operations succeed or all fail.
    In atomic mode, snapshots are taken before each mutation so that
    updates and deletes can be reversed if a later operation fails.
    """
    tenant_id = _extract_tenant_id(fastapi_request)
    if not tenant_id:
        raise AuthenticationError(
            message="Authenticated tenant context required for batch entity operations"
        )

    results: list[dict[str, Any]] = []
    successful = 0
    failed = 0
    atomic_rollback = False

    # Rollback ledger: list of (operation, entity_id, snapshot_or_None)
    # - create  → snapshot is None  (rollback = delete)
    # - update  → snapshot is dict  (rollback = restore)
    # - delete  → snapshot is dict  (rollback = re-create)
    rollback_ledger: list[tuple[str, str, dict[str, Any] | None]] = []

    try:
        for i, operation in enumerate(request.operations):
            result, rollback_entry = await _execute_operation(
                neo4j_driver, operation, tenant_id, request.atomic, i
            )
            results.append(result)

            if result["success"]:
                successful += 1
                if rollback_entry:
                    rollback_ledger.append(rollback_entry)
            else:
                failed += 1

        if request.atomic and failed > 0 and rollback_ledger:
            atomic_rollback = True
            logger.warning(
                "Atomic rollback: reversing %d completed operations",
                len(rollback_ledger),
            )
            await _perform_rollback(neo4j_driver, rollback_ledger, tenant_id)

        return BatchEntityResponse.model_validate(
            {
                "total_operations": len(request.operations),
                "successful": successful if not (request.atomic and failed > 0) else 0,
                "failed": failed,
                "results": [BatchEntityResult.model_validate(r) for r in results],
                "atomic_rollback": atomic_rollback if request.atomic else None,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch entity operations failed: %s", e)
        raise ServiceUnavailableError(
            message="Batch operations failed. Please try again later."
        )


async def _execute_operation(
    driver: Any,
    operation: BatchEntityOperation,
    tenant_id: str,
    atomic: bool,
    index: int,
) -> tuple[dict[str, Any], tuple[str, str, dict[str, Any] | None] | None]:
    """Execute a single batch operation and return result with rollback entry."""
    rollback_entry: tuple[str, str, dict[str, Any] | None] = None

    try:
        if operation.operation == "create":
            result = await _create_entity(driver, operation, tenant_id)
            if result["success"]:
                rollback_entry = ("create", result["entity_id"], None)
            return _build_operation_result(index, "create", result), rollback_entry

        elif operation.operation == "update":
            snapshot = await _snapshot_entity(driver, operation.entity_id, tenant_id) if atomic else None
            result = await _update_entity(driver, operation, tenant_id)
            if result["success"] and atomic and snapshot:
                rollback_entry = ("update", operation.entity_id, snapshot)
            return _build_operation_result(index, "update", result), rollback_entry

        elif operation.operation == "delete":
            snapshot = await _snapshot_entity(driver, operation.entity_id, tenant_id) if atomic else None
            result = await _delete_entity(driver, operation, tenant_id)
            if result["success"] and atomic and snapshot:
                rollback_entry = ("delete", operation.entity_id, snapshot)
            return _build_operation_result(index, "delete", result), rollback_entry

        else:
            return (
                {
                    "index": index,
                    "operation": operation.operation,
                    "entity_id": getattr(operation, "entity_id", None),
                    "success": False,
                    "error": "UNKNOWN_OPERATION",
                },
                None,
            )

    except (neo4j.exceptions.DriverError, neo4j.exceptions.DatabaseError, ValueError) as e:
        logger.error("Batch operation error at index %d: %s", index, str(e))
        return (
            {
                "index": index,
                "operation": operation.operation,
                "entity_id": getattr(operation, "entity_id", None),
                "success": False,
                "error": "BATCH_OPERATION_ERROR",
            },
            None,
        )


def _build_operation_result(
    index: int, operation_type: str, result: dict[str, Any]
) -> dict[str, Any]:
    """Build standardized operation result dictionary."""
    return {
        "index": index,
        "operation": operation_type,
        "entity_id": result.get("entity_id"),
        "success": result["success"],
        "error": result.get("error"),
    }


async def _perform_rollback(
    driver: Any,
    rollback_ledger: list[tuple[str, str, dict[str, Any] | None]],
    tenant_id: str,
) -> None:
    """Perform atomic rollback in LIFO order."""
    # Reverse in LIFO order so dependent operations unwind correctly
    for op_type, entity_id, snapshot in reversed(rollback_ledger):
        try:
            if op_type == "create":
                await _delete_entity_by_id(driver, entity_id, tenant_id)
            elif op_type == "update" and snapshot:
                await _restore_entity(driver, entity_id, snapshot, tenant_id)
            elif op_type == "delete" and snapshot:
                await _recreate_entity(driver, snapshot, tenant_id)
        except Exception as e:
            logger.error("Rollback error for %s %s: %s", op_type, entity_id, e)


@router.post("/batch/analytics", response_model=BatchAnalyticsResponse)
async def batch_analytics(
    request: BatchAnalyticsRequest,
    centrality_analyzer=Depends(get_centrality_analyzer),
    graph_rag=Depends(get_graph_rag),
) -> BatchAnalyticsResponse:
    """Execute batch analytics on multiple entities."""
    results: list[dict[str, Any]] = []
    successful = 0
    failed = 0
    all_scores: list[int] = []

    try:
        for entity_id in request.entity_ids:
            result, score = await _process_entity_analytics(
                graph_rag, entity_id, request.max_hops, request.algorithm
            )
            results.append(result)

            if result["success"]:
                successful += 1
                if score is not None:
                    all_scores.append(score)
            else:
                failed += 1

        aggregate = _calculate_aggregate_metrics(all_scores) if all_scores else None

        return BatchAnalyticsResponse.model_validate(
            {
                "total_analyzed": len(request.entity_ids),
                "successful": successful,
                "failed": failed,
                "results": [BatchAnalyticsResult.model_validate(r) for r in results],
                "aggregate_metrics": aggregate,
            }
        )
    except Exception as e:
        logger.error("Batch analytics failed: %s", e)
        raise ServiceUnavailableError(
            message="Batch analytics failed. Please try again later."
        )


async def _process_entity_analytics(
    graph_rag: Any,
    entity_id: str,
    max_hops: int,
    algorithm: str,
) -> tuple[dict[str, Any], int | None]:
    """Process analytics for a single entity and return result with score."""
    try:
        context = await graph_rag.get_entity_context(
            entity_id=entity_id,
            hops=max_hops,
        )
        if not context.get("center"):
            return (
                {
                    "entity_id": entity_id,
                    "success": False,
                    "error": "Entity not found",
                },
                None,
            )

        if algorithm in ["centrality", "pagerank"]:
            metrics: dict[str, Any] = {
                "entity_count": context["entity_count"],
                "relationship_count": context["relationship_count"],
                "center_entity": context["center"],
                "neighbors": len(context.get("neighbors", [])),
            }
            score = context["entity_count"]
        else:
            metrics = {"context": context}
            score = None

        return (
            {"entity_id": entity_id, "success": True, "metrics": metrics},
            score,
        )
    except Exception as e:
        logger.warning("Batch analytics failed for %s: %s", entity_id, e)
        return (
            {
                "entity_id": entity_id,
                "success": False,
                "error": "BATCH_ANALYTICS_ERROR",
            },
            None,
        )


def _calculate_aggregate_metrics(scores: list[int]) -> dict[str, Any] | None:
    """Calculate aggregate metrics from entity scores."""
    if not scores:
        return None

    return {
        "avg_entities_per_context": sum(scores) / len(scores),
        "max_entities": max(scores),
        "min_entities": min(scores),
        "total_entities_analyzed": sum(scores),
    }
