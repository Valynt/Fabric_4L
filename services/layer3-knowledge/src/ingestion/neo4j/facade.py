from __future__ import annotations

from typing import Any

from neo4j import AsyncDriver
from rdflib import Graph

from ...config import Settings, get_settings
from .connection import Neo4jConnectionManager
from .embeddings import EmbeddingGenerator
from .extractors import RDFEntityExtractor, RDFRelationshipExtractor
from .orchestrator import BatchImportOrchestrator
from .tenant import validate_ingestion_tenant_id
from .writers import EntityBatchWriter, RelationshipBatchWriter


class Neo4jLoader:
    """Backward-compatible public facade for Neo4j RDF ingestion.

    New code should prefer `BatchImportOrchestrator` directly; this class
    preserves the historical constructor and method signatures.
    """

    def __init__(
        self,
        driver: AsyncDriver | None = None,
        settings: Settings | None = None,
        batch_size: int = 1000,
    ):
        self.settings = settings or get_settings()
        self.batch_size = batch_size
        self._connection = Neo4jConnectionManager(driver=driver, settings=settings)
        use_apoc = getattr(self.settings, "use_apoc", False)
        self._orchestrator = BatchImportOrchestrator(
            connection=self._connection,
            entity_extractor=RDFEntityExtractor(),
            relationship_extractor=RDFRelationshipExtractor(),
            embedding_generator=EmbeddingGenerator(settings=self.settings),
            entity_writer=EntityBatchWriter(),
            relationship_writer=RelationshipBatchWriter(use_apoc=use_apoc),
        )

    async def _get_driver(self) -> AsyncDriver:
        """Get or create Neo4j driver via the shared singleton factory."""
        return await self._connection.get_driver()

    async def close(self) -> None:
        """Close Neo4j driver if owned."""
        await self._connection.close()

    async def load_rdf_graph(
        self,
        rdf_graph: Graph,
        source_id: str | None = None,
        extraction_job_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Load an RDF graph into Neo4j."""
        return await self._orchestrator.load_rdf_graph(
            rdf_graph, source_id, extraction_job_id, tenant_id
        )

    async def load_turtle_string(
        self,
        turtle_data: str,
        source_id: str | None = None,
        extraction_job_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Load Turtle-formatted RDF string into Neo4j."""
        return await self._orchestrator.load_turtle_string(
            turtle_data, source_id, extraction_job_id, tenant_id
        )

    async def delete_by_source(
        self, source_id: str, tenant_id: str | None = None
    ) -> dict[str, Any]:
        """Delete all entities and relationships from a specific source."""
        return await self._orchestrator.delete_by_source(source_id, tenant_id)

    # Private-method compatibility wrappers used by existing tests.
    def _extract_entities_from_rdf(
        self, graph: Graph
    ) -> dict[str, list[dict[str, Any]]]:
        return self._orchestrator.entity_extractor.extract(graph)

    def _extract_relationships_from_rdf(
        self,
        graph: Graph,
        source_id: str | None = None,
        extraction_job_id: str | None = None,
    ) -> Any:
        return self._orchestrator.relationship_extractor.extract(
            graph, source_id, extraction_job_id
        )

    def _resolve_entity_id(self, graph: Graph, uri: Any) -> str:
        return RDFRelationshipExtractor._resolve_entity_id(graph, uri)

    def _extract_property_name(self, uri: Any) -> str:
        return RDFEntityExtractor._property_name(uri)

    def _convert_literal(self, literal: Any) -> Any:
        return RDFEntityExtractor._convert_literal(literal)

    def _get_embedding_model(self) -> Any:
        return self._orchestrator.embedding_generator._get_model()

    def _build_embedding_text(self, entity: dict[str, Any]) -> str:
        return self._orchestrator.embedding_generator.build_text(entity)

    def _generate_embedding(self, text: str) -> list[float] | None:
        return self._orchestrator.embedding_generator.generate(text)

    def _attach_embeddings(
        self, entity_type: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return self._orchestrator.embedding_generator.attach(entity_type, entities)

    async def _load_entities_batch(
        self,
        session: Any,
        entity_type: str,
        entities: list[dict[str, Any]],
        source_id: str | None,
        extraction_job_id: str | None,
        tenant_id: str | None = None,
    ) -> int:
        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)
        attached = self._orchestrator.embedding_generator.attach(entity_type, entities)
        return await self._orchestrator.entity_writer.write(
            session,
            entity_type,
            attached,
            source_id,
            extraction_job_id,
            validated_tenant_id,
        )

    async def _load_relationships_batch(
        self,
        session: Any,
        relationships: dict[str, list[dict[str, Any]]],
        source_id: str | None,
        extraction_job_id: str | None,
        tenant_id: str | None = None,
    ) -> int:
        return await self._orchestrator.relationship_writer.write(
            session, relationships, source_id, extraction_job_id, tenant_id
        )

    async def _load_relationships_native(
        self,
        session: Any,
        relationships: list[dict[str, Any]],
        source_id: str | None,
        extraction_job_id: str | None,
        tenant_id: str | None = None,
    ) -> int:
        return await self._orchestrator.relationship_writer.write_native(
            session, relationships, source_id, extraction_job_id, tenant_id
        )
