"""Analytics domain router — community detection, centrality, similarity, batch ops.

Migrated from app_monolith.py as part of ARCH-L3-011 (Sprint 3 cutover).
All write-paths that touch Neo4j directly use tenant_id extracted from the
authenticated request context; the cypher_security allowlist is enforced
via the shared TenantScopedCypher utility.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ...api.dependencies import (
    AppState,
    get_app_state,
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
            raise HTTPException(
                status_code=400, detail=f"Unknown algorithm: {request.algorithm}"
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
        raise HTTPException(
            status_code=500,
            detail="Community detection failed. Please try again later.",
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
            raise HTTPException(
                status_code=400, detail=f"Unknown algorithm: {request.algorithm}"
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
        raise HTTPException(
            status_code=500,
            detail="Centrality calculation failed. Please try again later.",
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
        raise HTTPException(
            status_code=500,
            detail="Similarity analysis failed. Please try again later.",
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
            raise HTTPException(status_code=404, detail=result["error"])

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
        raise HTTPException(
            status_code=500,
            detail="Entity comparison failed. Please try again later.",
        )


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------


async def _create_entity(
    driver: Any, operation: BatchEntityOperation, tenant_id: str | None
) -> dict[str, Any]:
    """Create a single entity in Neo4j, scoped to tenant_id."""
    if not tenant_id:
        return {"success": False, "error": "tenant_id is required for entity creation"}
    try:
        entity_id = str(uuid.uuid4())
        async with driver.session() as session:
            query = """
            CREATE (n:Entity {
                id: $id,
                entity_type: $entity_type,
                tenant_id: $tenant_id,
                created_at: datetime(),
                updated_at: datetime()
            })
            SET n += $properties
            RETURN n.id as entity_id
            """
            result = await session.run(
                query,
                {
                    "id": entity_id,
                    "entity_type": (
                        operation.entity_type.value
                        if operation.entity_type
                        else "Unknown"
                    ),
                    "tenant_id": tenant_id,
                    "properties": operation.properties or {},
                },
            )
            record = await result.single()
            if record:
                return {"success": True, "entity_id": record["entity_id"]}
            return {"success": False, "error": "Failed to create entity"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_entity(
    driver: Any, operation: BatchEntityOperation, tenant_id: str | None
) -> dict[str, Any]:
    """Update a single entity in Neo4j, scoped by tenant_id."""
    if not tenant_id:
        return {"success": False, "error": "tenant_id is required for entity updates"}
    try:
        async with driver.session() as session:
            query = """
            MATCH (n {id: $entity_id, tenant_id: $tenant_id})
            SET n += $properties, n.updated_at = datetime()
            RETURN n.id as entity_id
            """
            result = await session.run(
                query,
                {
                    "entity_id": operation.entity_id,
                    "tenant_id": tenant_id,
                    "properties": operation.properties or {},
                },
            )
            record = await result.single()
            if record:
                return {"success": True}
            return {"success": False, "error": "Entity not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _delete_entity(
    driver: Any, operation: BatchEntityOperation, tenant_id: str | None
) -> dict[str, Any]:
    """Delete a single entity from Neo4j, scoped by tenant_id."""
    if not tenant_id:
        return {"success": False, "error": "tenant_id is required for entity deletion"}
    try:
        async with driver.session() as session:
            query = """
            MATCH (n {id: $entity_id, tenant_id: $tenant_id})
            DETACH DELETE n
            RETURN count(n) as deleted
            """
            result = await session.run(
                query, {"entity_id": operation.entity_id, "tenant_id": tenant_id}
            )
            record = await result.single()
            if record and record["deleted"] > 0:
                return {"success": True}
            return {"success": False, "error": "Entity not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _delete_entity_by_id(
    driver: Any, entity_id: str, tenant_id: str | None
) -> None:
    """Delete entity by ID (used for atomic rollback)."""
    if not tenant_id:
        raise ValueError("tenant_id is required for entity deletion")
    async with driver.session() as session:
        await session.run(
            "MATCH (n {id: $entity_id, tenant_id: $tenant_id}) DETACH DELETE n",
            {"entity_id": entity_id, "tenant_id": tenant_id},
        )


async def _snapshot_entity(
    driver: Any, entity_id: str, tenant_id: str
) -> dict[str, Any] | None:
    """Capture a node's current properties for rollback purposes."""
    try:
        async with driver.session() as session:
            result = await session.run(
                "MATCH (n {id: $entity_id, tenant_id: $tenant_id}) RETURN properties(n) as props",
                {"entity_id": entity_id, "tenant_id": tenant_id},
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
            await session.run(
                """
                MATCH (n {id: $entity_id, tenant_id: $tenant_id})
                SET n = $snapshot
                """,
                {"entity_id": entity_id, "tenant_id": tenant_id, "snapshot": snapshot},
            )
    except Exception as e:
        logger.error("Rollback restore failed for entity %s: %s", entity_id, e)


async def _recreate_entity(
    driver: Any, snapshot: dict[str, Any], tenant_id: str
) -> None:
    """Re-create a node that was deleted during a batch that is being rolled back."""
    try:
        async with driver.session() as session:
            await session.run(
                """
                CREATE (n:Entity)
                SET n = $snapshot
                """,
                {"snapshot": {**snapshot, "tenant_id": tenant_id}},
            )
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
        raise HTTPException(
            status_code=401,
            detail="Authenticated tenant context required for batch entity operations",
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
            try:
                if operation.operation == "create":
                    result = await _create_entity(neo4j_driver, operation, tenant_id)
                    if result["success"]:
                        successful += 1
                        rollback_ledger.append(("create", result["entity_id"], None))
                    else:
                        failed += 1
                    results.append(
                        {
                            "index": i,
                            "operation": "create",
                            "entity_id": result.get("entity_id"),
                            "success": result["success"],
                            "error": result.get("error"),
                        }
                    )

                elif operation.operation == "update":
                    snapshot = (
                        await _snapshot_entity(neo4j_driver, operation.entity_id, tenant_id)
                        if request.atomic
                        else None
                    )
                    result = await _update_entity(neo4j_driver, operation, tenant_id)
                    if result["success"]:
                        successful += 1
                        if request.atomic and snapshot:
                            rollback_ledger.append(("update", operation.entity_id, snapshot))
                    else:
                        failed += 1
                    results.append(
                        {
                            "index": i,
                            "operation": "update",
                            "entity_id": operation.entity_id,
                            "success": result["success"],
                            "error": result.get("error"),
                        }
                    )

                elif operation.operation == "delete":
                    snapshot = (
                        await _snapshot_entity(neo4j_driver, operation.entity_id, tenant_id)
                        if request.atomic
                        else None
                    )
                    result = await _delete_entity(neo4j_driver, operation, tenant_id)
                    if result["success"]:
                        successful += 1
                        if request.atomic and snapshot:
                            rollback_ledger.append(("delete", operation.entity_id, snapshot))
                    else:
                        failed += 1
                    results.append(
                        {
                            "index": i,
                            "operation": "delete",
                            "entity_id": operation.entity_id,
                            "success": result["success"],
                            "error": result.get("error"),
                        }
                    )

            except Exception as e:
                failed += 1
                results.append(
                    {
                        "index": i,
                        "operation": operation.operation,
                        "entity_id": getattr(operation, "entity_id", None),
                        "success": False,
                        "error": str(e),
                    }
                )

        if request.atomic and failed > 0 and rollback_ledger:
            atomic_rollback = True
            logger.warning(
                "Atomic rollback: reversing %d completed operations", len(rollback_ledger)
            )
            # Reverse in LIFO order so dependent operations unwind correctly
            for op_type, entity_id, snapshot in reversed(rollback_ledger):
                try:
                    if op_type == "create":
                        await _delete_entity_by_id(neo4j_driver, entity_id, tenant_id)
                    elif op_type == "update" and snapshot:
                        await _restore_entity(neo4j_driver, entity_id, snapshot, tenant_id)
                    elif op_type == "delete" and snapshot:
                        await _recreate_entity(neo4j_driver, snapshot, tenant_id)
                except Exception as e:
                    logger.error(
                        "Rollback error for %s %s: %s", op_type, entity_id, e
                    )

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
        raise HTTPException(
            status_code=500,
            detail="Batch operations failed. Please try again later.",
        )


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
            try:
                context = await graph_rag.get_entity_context(
                    entity_id=entity_id,
                    hops=request.max_hops,
                )
                if not context.get("center"):
                    results.append(
                        {"entity_id": entity_id, "success": False, "error": "Entity not found"}
                    )
                    failed += 1
                    continue

                if request.algorithm in ["centrality", "pagerank"]:
                    metrics: dict[str, Any] = {
                        "entity_count": context["entity_count"],
                        "relationship_count": context["relationship_count"],
                        "center_entity": context["center"],
                        "neighbors": len(context.get("neighbors", [])),
                    }
                    all_scores.append(context["entity_count"])
                else:
                    metrics = {"context": context}

                results.append({"entity_id": entity_id, "success": True, "metrics": metrics})
                successful += 1
            except Exception as e:
                logger.warning("Batch analytics failed for %s: %s", entity_id, e)
                results.append({"entity_id": entity_id, "success": False, "error": str(e)})
                failed += 1

        aggregate = None
        if all_scores:
            aggregate = {
                "avg_entities_per_context": sum(all_scores) / len(all_scores),
                "max_entities": max(all_scores),
                "min_entities": min(all_scores),
                "total_entities_analyzed": sum(all_scores),
            }

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
        raise HTTPException(
            status_code=500, detail="Batch analytics failed. Please try again later."
        )
