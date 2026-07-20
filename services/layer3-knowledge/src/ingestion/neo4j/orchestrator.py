from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from rdflib import Graph

from ...db.audited_mutation import AuditedGraphMutation
from .connection import Neo4jConnectionManager
from .embeddings import EmbeddingGenerator
from .exceptions import RDFLoadError
from .extractors import RDFEntityExtractor, RDFRelationshipExtractor
from .stats import LoadStats, LoadStatsAction, reduce_stats
from .tenant import validate_ingestion_tenant_id
from .writers import EntityBatchWriter, RelationshipBatchWriter

logger = logging.getLogger(__name__)


class BatchImportOrchestrator:
    """Coordinates an RDF-to-Neo4j load using async session-passing and reducer stats."""

    def __init__(
        self,
        connection: Neo4jConnectionManager,
        entity_extractor: RDFEntityExtractor,
        relationship_extractor: RDFRelationshipExtractor,
        embedding_generator: EmbeddingGenerator,
        entity_writer: EntityBatchWriter,
        relationship_writer: RelationshipBatchWriter,
    ):
        self.connection = connection
        self.entity_extractor = entity_extractor
        self.relationship_extractor = relationship_extractor
        self.embedding_generator = embedding_generator
        self.entity_writer = entity_writer
        self.relationship_writer = relationship_writer

    async def load_rdf_graph(
        self,
        rdf_graph: Graph,
        source_id: str | None = None,
        extraction_job_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Load an RDF graph into Neo4j."""
        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)
        stats = reduce_stats(LoadStats(), LoadStatsAction.start())

        async with self.connection.session() as session:
            entities = self.entity_extractor.extract(rdf_graph)
            for entity_type, entity_data in entities.items():
                entities_with_embeddings = self.embedding_generator.attach(
                    entity_type, entity_data
                )
                loaded = await self.entity_writer.write(
                    session,
                    entity_type,
                    entities_with_embeddings,
                    source_id,
                    extraction_job_id,
                    validated_tenant_id,
                )
                stats = reduce_stats(
                    stats, LoadStatsAction.entities_loaded(loaded)
                )

            relationships = self.relationship_extractor.extract(
                rdf_graph, source_id, extraction_job_id
            )
            if isinstance(relationships, list):
                grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for rel in relationships:
                    grouped[rel.get("predicate", "")].append(rel)
                relationships = grouped

            loaded = await self.relationship_writer.write(
                session,
                relationships,
                source_id,
                extraction_job_id,
                validated_tenant_id,
            )
            stats = reduce_stats(
                stats, LoadStatsAction.relationships_loaded(loaded)
            )

            stats = reduce_stats(
                stats, LoadStatsAction.triples_processed(len(rdf_graph))
            )
            stats = reduce_stats(stats, LoadStatsAction.finish())

        logger.info(
            "Loaded %s entities and %s relationships from RDF",
            stats.entities_loaded,
            stats.relationships_loaded,
        )

        return stats.to_dict()

    async def load_turtle_string(
        self,
        turtle_data: str,
        source_id: str | None = None,
        extraction_job_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Load Turtle-formatted RDF string into Neo4j."""
        try:
            g = Graph()
            g.parse(data=turtle_data, format="turtle")
            return await self.load_rdf_graph(
                g, source_id, extraction_job_id, tenant_id
            )
        except Exception as e:
            logger.error("Failed to parse Turtle data: %s", e)
            raise RDFLoadError(f"Turtle parsing failed: {e}") from e

    async def delete_by_source(
        self, source_id: str, tenant_id: str | None = None
    ) -> dict[str, Any]:
        """Delete all entities and relationships from a specific source."""
        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)

        async with self.connection.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=validated_tenant_id,
                session=session,
                operation_source="neo4j_loader.delete_by_source",
            )
            stats = await mutation.delete_by_source(source_id)

        logger.info(
            "Deleted %s entities and %s relationships for source %s in tenant %s",
            stats.get("entities_deleted", 0),
            stats.get("relationships_deleted", 0),
            source_id,
            validated_tenant_id,
        )
        return stats
