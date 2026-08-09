from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from typing import Any

from ...db.audited_mutation import AuditedGraphMutation
from ...ingestion.validators import RequiredFieldValidator
from ...schema.constraints import RELATIONSHIP_TYPES
from .protocols import MutationGateway, SessionLike
from .tenant import validate_ingestion_tenant_id

logger = logging.getLogger(__name__)


class EntityBatchWriter:
    """Tenant-scoped batch node writes via an audited mutation gateway."""

    def __init__(
        self,
        validator: RequiredFieldValidator | None = None,
        mutation_gateway: Callable[..., MutationGateway] = AuditedGraphMutation,
    ):
        self._validator = validator or RequiredFieldValidator()
        self._mutation_gateway = mutation_gateway

    async def write(
        self,
        session: SessionLike,
        entity_type: str,
        entities: list[dict[str, Any]],
        source_id: str | None,
        extraction_job_id: str | None,
        tenant_id: str | None,
    ) -> int:
        """Load a batch of entities into Neo4j."""
        if not entities:
            return 0

        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)

        for entity in entities:
            entity_id = entity.get("id", "unknown")
            self._validator.validate_and_raise(
                entity_type=entity_type,
                data=entity,
                entity_id=entity_id,
                source_id=source_id,
            )

        for entity in entities:
            entity["tenant_id"] = validated_tenant_id
            entity["source_id"] = source_id
            entity["extraction_job_id"] = extraction_job_id
            entity["loaded_at"] = datetime.utcnow().isoformat()

        mutation = self._mutation_gateway(
            tenant_id=validated_tenant_id,
            session=session,
            operation_source="neo4j_loader._load_entities_batch",
        )

        try:
            result = await mutation.write_nodes_batch(entity_type, entities)
            return result.get("count", 0)
        except Exception as e:
            logger.error("Failed to load %s entities: %s", entity_type, e)
            return 0


class RelationshipBatchWriter:
    """Tenant-scoped batch relationship writes."""

    def __init__(
        self,
        mutation_gateway: Callable[..., MutationGateway] = AuditedGraphMutation,
        use_apoc: bool = False,
    ):
        self._mutation_gateway = mutation_gateway
        self.use_apoc = use_apoc

    @staticmethod
    def _normalize_predicate(predicate: str) -> str:
        return predicate.lower().replace("-", "_").replace(" ", "_")

    async def write(
        self,
        session: SessionLike,
        relationships: dict[str, list[dict[str, Any]]],
        source_id: str | None,
        extraction_job_id: str | None,
        tenant_id: str | None,
    ) -> int:
        """Load relationships into Neo4j via bulk relationship writes."""
        all_relationships: list[dict[str, Any]] = []
        for rel_list in relationships.values():
            all_relationships.extend(rel_list)

        if not all_relationships:
            return 0

        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)

        for rel in all_relationships:
            rel["tenant_id"] = validated_tenant_id

        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        loaded_at = datetime.utcnow().isoformat()
        for rel in all_relationships:
            predicate = self._normalize_predicate(rel.get("predicate", ""))
            if predicate in RELATIONSHIP_TYPES:
                by_type[predicate].append(
                    {
                        "src_id": rel.get("source_id"),
                        "tgt_id": rel.get("target_id"),
                        "properties": {
                            "source_id": source_id,
                            "source_entity_id": rel.get("source_id"),
                            "target_entity_id": rel.get("target_id"),
                            "extraction_job_id": extraction_job_id,
                            "loaded_at": loaded_at,
                            "confidence": rel.get("confidence"),
                            "raw_predicate": rel.get("raw_predicate"),
                            "impact_level": rel.get("impact_level"),
                            "strength": rel.get("strength"),
                            "enablement_type": rel.get("enablement_type"),
                            "benefit_type": rel.get("benefit_type"),
                            "driver_type": rel.get("driver_type"),
                            "contribution_weight": rel.get("contribution_weight"),
                            "influence_weight": rel.get("influence_weight"),
                        },
                    }
                )
            else:
                logger.warning(
                    "Skipping unknown relationship type '%s' (source=%s -> target=%s)",
                    predicate,
                    rel.get("source_id"),
                    rel.get("target_id"),
                )

        total_loaded = 0
        mutation = self._mutation_gateway(
            tenant_id=validated_tenant_id,
            session=session,
            operation_source="neo4j_loader._load_relationships_batch",
        )

        for rel_type, triples in by_type.items():
            try:
                result = await mutation.write_relationships_batch(rel_type, triples)
                total_loaded += result.get("count", 0)
            except Exception as e:
                logger.error("Failed to load %s relationships: %s", rel_type, e)

        return total_loaded

    async def write_native(
        self,
        session: SessionLike,
        relationships: list[dict[str, Any]],
        source_id: str | None,
        extraction_job_id: str | None,
        tenant_id: str | None,
    ) -> int:
        """Load relationships using native Cypher (no APOC required).

        Kept for backward compatibility with existing tests.
        """
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)

        for rel in relationships:
            predicate = self._normalize_predicate(rel.get("predicate", ""))
            if predicate in RELATIONSHIP_TYPES:
                by_type[predicate].append(rel)
            else:
                logger.warning(
                    "Skipping unknown relationship type '%s' (source=%s -> target=%s)",
                    predicate,
                    rel.get("source_id"),
                    rel.get("target_id"),
                )

        total_loaded = 0
        loaded_at = datetime.utcnow().isoformat()
        mutation = self._mutation_gateway(
            tenant_id=validated_tenant_id,
            session=session,
            operation_source="neo4j_loader._load_relationships_native",
        )

        for rel_type, rels in by_type.items():
            try:
                for rel in rels:
                    await mutation.write_relationship(
                        rel["source_id"],
                        rel_type,
                        rel["target_id"],
                        properties={
                            "source_id": source_id,
                            "source_entity_id": rel["source_id"],
                            "target_entity_id": rel["target_id"],
                            "extraction_job_id": extraction_job_id,
                            "loaded_at": loaded_at,
                            "confidence": rel.get("confidence"),
                            "raw_predicate": rel.get("raw_predicate"),
                            "impact_level": rel.get("impact_level"),
                            "strength": rel.get("strength"),
                            "enablement_type": rel.get("enablement_type"),
                            "benefit_type": rel.get("benefit_type"),
                            "driver_type": rel.get("driver_type"),
                            "contribution_weight": rel.get("contribution_weight"),
                            "influence_weight": rel.get("influence_weight"),
                        },
                    )
                    total_loaded += 1
            except Exception as exc:
                logger.error("Failed to load %s relationships: %s", rel_type, exc)

        return total_loaded
