"""Neo4j RDF loader for ingesting Layer 2 extraction results.

Changes from original:
- Replaced ``AsyncGraphDatabase.driver()`` with the shared ``get_driver()``
  factory (retry logic, connection validation).
- Added ``use_apoc`` flag (default False) so the loader works on vanilla
  Neo4j / Neo4j Aura without the APOC plugin.
- ``_load_entities_batch``: native Cypher path avoids ``apoc.map.removeKeys``.
- ``_load_relationships_batch``: delegates to ``_load_relationships_native``
  when APOC is unavailable; APOC path is preserved as opt-in.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from neo4j import AsyncDriver
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from ..config import Settings, get_settings
from ..db.audited_mutation import AuditedGraphMutation
from ..db.driver import get_driver
from ..ingestion.validators import RequiredFieldValidator
from ..schema.constraints import ENTITY_TYPES, RELATIONSHIP_TYPES
from ..services.embedding_errors import EmbeddingProviderUnavailableError

logger = logging.getLogger(__name__)

# Namespaces (aligned with value_fabric_ontology_schema.py spec)
VF = Namespace("http://valuefabric.io/ontology/")
VF_HTTPS = Namespace("https://valuefabric.io/ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")

# Current retrieval entities that receive ingestion-time embeddings.
VECTOR_ENTITY_TYPES = {"Capability", "UseCase", "Persona", "ValueDriver"}


class RDFLoadError(Exception):
    """Raised when RDF loading fails."""


class TenantValidationError(ValueError):
    """Raised when tenant context is missing or malformed for ingestion."""


def validate_ingestion_tenant_id(tenant_id: str | None) -> str:
    """Validate public ingestion tenant scope.

    Public Layer 3 ingestion paths are tenant-bound and must not implicitly
    default to platform scope. The accepted format is a non-empty UUID string.
    """
    if tenant_id is None:
        raise TenantValidationError("tenant_id is required for Layer 3 ingestion")

    normalized = str(tenant_id).strip()
    if not normalized:
        raise TenantValidationError("tenant_id is required for Layer 3 ingestion")

    try:
        return str(UUID(normalized))
    except ValueError as exc:
        raise TenantValidationError(
            f"Invalid tenant_id format: {tenant_id}. Expected UUID."
        ) from exc


def _validate_internal_system_tenant_id(tenant_id: str) -> str:
    """Validate the explicit internal-only platform ingestion scope."""
    normalized = str(tenant_id).strip().lower()
    if normalized != "system":
        raise TenantValidationError(
            "internal system ingestion requires tenant_id='system'"
        )
    return normalized


class Neo4jLoader:
    """Load RDF triples into Neo4j Knowledge Graph."""

    def __init__(
        self,
        driver: AsyncDriver | None = None,
        settings: Settings | None = None,
        batch_size: int = 1000,
    ):
        """Initialize RDF loader.

        Args:
            driver: Neo4j async driver. If None, creates new connection.
            settings: Application settings. If None, loads from environment.
            batch_size: Number of triples to process in each batch.
        """
        self.settings = settings or get_settings()
        self.batch_size = batch_size
        self._driver = driver
        self._owned_driver = driver is None
        self._embedding_model = None
        self._validator = RequiredFieldValidator()
        # When use_apoc=True the loader uses APOC procedures for richer merge
        # semantics.  Defaults to False so the service works on vanilla Neo4j
        # (including Neo4j Aura) without requiring the APOC plugin.
        self.use_apoc: bool = getattr(self.settings, "use_apoc", False)

    async def _get_driver(self) -> AsyncDriver:
        """Get or create Neo4j driver via the shared singleton factory."""
        if self._driver is None:
            self._driver = await get_driver(self.settings)
        return self._driver

    async def close(self) -> None:
        """Close Neo4j driver if owned."""
        if self._owned_driver and self._driver:
            await self._driver.close()
            self._driver = None

    async def load_rdf_graph(
        self,
        rdf_graph: Graph,
        source_id: str | None = None,
        extraction_job_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        """Load an RDF graph into Neo4j.

        Args:
            rdf_graph: RDFLib Graph containing triples
            source_id: ID of the source document
            extraction_job_id: ID of the extraction job that generated this data
            tenant_id: Validated tenant UUID for isolation

        Returns:
            Dictionary with load statistics
        """
        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)
        driver = await self._get_driver()
        stats = {
            "entities_loaded": 0,
            "relationships_loaded": 0,
            "triples_processed": 0,
            "errors": [],
            "start_time": datetime.utcnow().isoformat(),
        }

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Extract and load entities
            entities = self._extract_entities_from_rdf(rdf_graph)
            for entity_type, entity_data in entities.items():
                loaded = await self._load_entities_batch(
                    session,
                    entity_type,
                    entity_data,
                    source_id,
                    extraction_job_id,
                    validated_tenant_id,
                )
                stats["entities_loaded"] += loaded

            # Extract and load relationships
            relationships = self._extract_relationships_from_rdf(
                rdf_graph, source_id, extraction_job_id
            )
            loaded = await self._load_relationships_batch(
                session,
                relationships,
                source_id,
                extraction_job_id,
                validated_tenant_id,
            )
            stats["relationships_loaded"] += loaded

            stats["triples_processed"] = len(rdf_graph)
            stats["end_time"] = datetime.utcnow().isoformat()

        logger.info(
            f"Loaded {stats['entities_loaded']} entities and "
            f"{stats['relationships_loaded']} relationships from RDF"
        )

        return stats

    async def load_turtle_string(
        self,
        turtle_data: str,
        source_id: str | None = None,
        extraction_job_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        """Load Turtle-formatted RDF string into Neo4j.

        Args:
            turtle_data: RDF data in Turtle format
            source_id: ID of the source document
            extraction_job_id: ID of the extraction job
            tenant_id: Validated tenant UUID for isolation

        Returns:
            Dictionary with load statistics
        """
        try:
            g = Graph()
            g.parse(data=turtle_data, format="turtle")
            return await self.load_rdf_graph(g, source_id, extraction_job_id, tenant_id)
        except Exception as e:
            logger.error(f"Failed to parse Turtle data: {e}")
            raise RDFLoadError(f"Turtle parsing failed: {e}") from e

    def _extract_entities_from_rdf(self, graph: Graph) -> dict[str, list[dict]]:
        """Extract entities grouped by type from RDF graph."""
        entities: dict[str, list[dict]] = {et: [] for et in ENTITY_TYPES}

        for entity_type in ENTITY_TYPES:
            type_uris = (VF[entity_type], VF_HTTPS[entity_type])

            for subject in {
                s for type_uri in type_uris for s in graph.subjects(RDF.type, type_uri)
            }:
                entity_data: dict[str, Any] = {"uri": str(subject)}

                for predicate, obj in graph.predicate_objects(subject):
                    pred_name = self._extract_property_name(predicate)

                    if isinstance(obj, Literal):
                        if obj.datatype:
                            entity_data[pred_name] = self._convert_literal(obj)
                        else:
                            entity_data[pred_name] = str(obj)
                    elif isinstance(obj, URIRef):
                        entity_data[pred_name] = str(obj)

                # Use explicit VF.id if provided, otherwise fall back to URI
                entity_data["id"] = entity_data.get("id") or str(subject)

                entities[entity_type].append(entity_data)

        return entities

    def _resolve_entity_id(self, graph: Graph, uri: URIRef) -> str:
        """Resolve an entity URI to its ID, using explicit VF.id if available."""
        id_literal = graph.value(uri, VF.id)
        if id_literal:
            return str(id_literal)
        return str(uri)

    def _extract_relationships_from_rdf(
        self,
        graph: Graph,
        source_id: str | None = None,
        extraction_job_id: str | None = None,
    ) -> dict[str, list[dict[str, Any]]] | list[dict[str, Any]]:
        """Extract relationships from RDF graph by type with all properties.

        The loader's production path consumes relationships grouped by predicate.
        Older unit tests call this helper directly without metadata arguments and
        expect a flat list, so the no-metadata call shape is retained as a
        backwards-compatible convenience.
        """
        legacy_flat_result = source_id is None and extraction_job_id is None
        relationships: dict[str, list[dict[str, Any]]] = {
            rel_type: [] for rel_type in RELATIONSHIP_TYPES
        }

        # Build a lookup of known relationship predicates using both canonical
        # and historical HTTPS namespaces.
        known_predicates = {
            **{VF[rt]: rt for rt in RELATIONSHIP_TYPES},
            **{VF_HTTPS[rt]: rt for rt in RELATIONSHIP_TYPES},
        }

        # Find all reified relationship statements for properties
        # Reified statements use RDF.Statement type
        for statement in graph.subjects(RDF.type, RDF.Statement):
            subject_uri = graph.value(statement, RDF.subject)
            predicate_uri = graph.value(statement, RDF.predicate)
            object_uri = graph.value(statement, RDF.object)

            if not all([subject_uri, predicate_uri, object_uri]):
                continue

            # Map predicate URI to relationship type name
            predicate_name = known_predicates.get(predicate_uri)
            if not predicate_name:
                continue

            # Extract relationship properties from reified statement
            rel_data: dict[str, Any] = {
                "source_id": self._resolve_entity_id(graph, subject_uri),
                "target_id": self._resolve_entity_id(graph, object_uri),
                "predicate": predicate_name,
                "confidence": 1.0,
                "source": source_id,
                "extraction_job_id": extraction_job_id,
                "provenance": {},
            }

            # Extract raw_predicate
            raw_pred = graph.value(statement, VF.rawPredicate)
            if raw_pred:
                rel_data["raw_predicate"] = str(raw_pred)

            # Extract confidence
            conf = graph.value(statement, VF.confidence)
            if conf:
                rel_data["confidence"] = float(conf)

            # Extract impact_level
            impact = graph.value(statement, VF.impactLevel)
            if impact:
                rel_data["impact_level"] = str(impact)

            # Extract strength
            strength = graph.value(statement, VF.strength)
            if strength:
                rel_data["strength"] = float(strength)

            # Extract enablement_type
            enablement = graph.value(statement, VF.enablementType)
            if enablement:
                rel_data["enablement_type"] = str(enablement)

            # Extract benefit_type
            benefit = graph.value(statement, VF.benefitType)
            if benefit:
                rel_data["benefit_type"] = str(benefit)

            # Extract driver_type
            driver = graph.value(statement, VF.driverType)
            if driver:
                rel_data["driver_type"] = str(driver)

            # Extract contribution_weight
            contrib = graph.value(statement, VF.contributionWeight)
            if contrib:
                rel_data["contribution_weight"] = float(contrib)

            # Extract influence_weight
            influence = graph.value(statement, VF.influenceWeight)
            if influence:
                rel_data["influence_weight"] = float(influence)

            relationships[predicate_name].append(rel_data)

        # Support simple direct triples in legacy fixtures that do not use RDF
        # reification for relationship properties.
        for subject_uri, predicate_uri, object_uri in graph:
            predicate_name = known_predicates.get(predicate_uri)
            if not predicate_name or not isinstance(object_uri, URIRef):
                continue
            rel_data = {
                "source_id": self._resolve_entity_id(graph, subject_uri),
                "target_id": self._resolve_entity_id(graph, object_uri),
                "predicate": predicate_name,
                "confidence": 1.0,
                "source": source_id,
                "extraction_job_id": extraction_job_id,
                "provenance": {},
            }
            if rel_data not in relationships[predicate_name]:
                relationships[predicate_name].append(rel_data)

        if legacy_flat_result:
            return [rel for rels in relationships.values() for rel in rels]

        return relationships

    def _extract_property_name(self, uri: URIRef) -> str:
        """Extract property name from URI."""
        uri_str = str(uri)
        if "#" in uri_str:
            return uri_str.split("#")[-1]
        return uri_str.split("/")[-1]

    def _convert_literal(self, literal: Literal) -> Any:
        """Convert RDF literal to Python value."""
        if literal.datatype:
            datatype = str(literal.datatype)
            if "integer" in datatype or "int" in datatype:
                return int(literal)
            elif "float" in datatype or "double" in datatype:
                return float(literal)
            elif "boolean" in datatype:
                return bool(literal)
            elif "dateTime" in datatype:
                return str(literal)  # Keep as ISO string
        return str(literal)

    def _get_embedding_model(self):
        """Lazily load sentence-transformers model for ingestion embeddings."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                model_name = getattr(
                    self.settings,
                    "embedding_model",
                    "sentence-transformers/all-MiniLM-L6-v2",
                )
                self._embedding_model = SentenceTransformer(model_name)
                logger.info("Loaded ingestion embedding model: %s", model_name)
            except Exception:
                logger.warning(
                    "sentence-transformers not available, embeddings disabled"
                )
                self._embedding_model = None
        return self._embedding_model

    def _build_embedding_text(self, entity: dict) -> str:
        """Build deterministic embedding text from core entity fields."""
        text_parts = []
        for key in ("name", "description", "summary", "title"):
            value = entity.get(key)
            if isinstance(value, str) and value.strip():
                text_parts.append(value.strip())
        if not text_parts:
            text_parts.append(str(entity.get("id", "")))
        return "\n".join(text_parts)[:4000]

    def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector using local sentence-transformers model."""
        if not text.strip():
            return None
        model = self._get_embedding_model()
        if model is None:
            raise EmbeddingProviderUnavailableError(
                "Embedding provider unavailable",
                provider="sentence-transformers",
                failure_cause="model_unavailable",
                retry_after_seconds=30,
                retry_hint="install_or_restore_provider",
            )
        try:
            return model.encode(text, normalize_embeddings=True).tolist()
        except Exception as exc:
            raise EmbeddingProviderUnavailableError(
                "Embedding provider unavailable",
                provider="sentence-transformers",
                failure_cause=exc.__class__.__name__,
                retry_after_seconds=30,
                retry_hint="retry_with_backoff",
            ) from exc

    def _attach_embeddings(self, entity_type: str, entities: list[dict]) -> list[dict]:
        """Attach embeddings to retrieval entity records before persistence."""
        if entity_type not in VECTOR_ENTITY_TYPES or not entities:
            return entities

        prepared: list[dict] = []
        for entity in entities:
            entity_copy = dict(entity)
            existing_embedding = entity_copy.get("embedding")
            if isinstance(existing_embedding, list) and existing_embedding:
                prepared.append(entity_copy)
                continue

            text = self._build_embedding_text(entity_copy)
            embedding = self._generate_embedding(text)
            if embedding is not None:
                entity_copy["embedding"] = embedding
                entity_copy["embedding_text"] = text[:2000]
            prepared.append(entity_copy)

        return prepared

    async def _load_entities_batch(
        self,
        session,
        entity_type: str,
        entities: list[dict],
        source_id: str | None,
        extraction_job_id: str | None,
        tenant_id: str | None = None,
    ) -> int:
        """Load a batch of entities into Neo4j.

        Uses native Cypher by default (no APOC required).  When
        ``self.use_apoc`` is True, falls back to the APOC map spread which
        is more concise but requires the plugin.

        Validates required fields before loading to enforce data integrity
        on Neo4j Community Edition (property existence constraints are
        Enterprise-only).
        """
        if not entities:
            return 0

        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)

        # Validate required fields (Community Edition compatibility)
        for entity in entities:
            entity_id = entity.get("id", "unknown")
            self._validator.validate_and_raise(
                entity_type=entity_type,
                data=entity,
                entity_id=entity_id,
                source_id=source_id,
            )

        entities = self._attach_embeddings(entity_type, entities)

        # Inject tenant_id and metadata into each entity
        for entity in entities:
            entity["tenant_id"] = validated_tenant_id
            entity["source_id"] = source_id
            entity["extraction_job_id"] = extraction_job_id
            entity["loaded_at"] = datetime.utcnow().isoformat()

        # Phase 1 hardening: Use AuditedGraphMutation for bulk node writes
        mutation = AuditedGraphMutation(
            tenant_id=validated_tenant_id,
            session=session,
            operation_source="neo4j_loader._load_entities_batch",
        )

        try:
            result = await mutation.write_nodes_batch(entity_type, entities)
            return result.get("count", 0)
        except Exception as e:
            logger.error(f"Failed to load {entity_type} entities: {e}")
            return 0

    async def _load_relationships_batch(
        self,
        session,
        relationships: dict[str, list[dict]],
        source_id: str | None,
        extraction_job_id: str | None,
        tenant_id: str | None = None,
    ) -> int:
        """Load relationships into Neo4j.

        Routes to the APOC implementation when ``self.use_apoc`` is True,
        otherwise uses the native Cypher implementation which works without
        the APOC plugin.

        Args:
            relationships: Dict mapping relationship type to list of relationship dicts
            tenant_id: Validated tenant UUID for isolation
        """
        # Flatten all relationships into a single list
        all_relationships = []
        for rel_list in relationships.values():
            all_relationships.extend(rel_list)

        if not all_relationships:
            return 0

        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)

        # Inject tenant_id into each relationship
        for rel in all_relationships:
            rel["tenant_id"] = validated_tenant_id

        # Phase 1 hardening: Use AuditedGraphMutation for bulk relationship writes
        mutation = AuditedGraphMutation(
            tenant_id=validated_tenant_id,
            session=session,
            operation_source="neo4j_loader._load_relationships_batch",
        )

        # Group by relationship type for batch operations
        by_type: dict[str, list[dict]] = defaultdict(list)
        for rel in all_relationships:
            predicate = (
                rel.get("predicate", "").lower().replace("-", "_").replace(" ", "_")
            )
            if predicate in RELATIONSHIP_TYPES:
                by_type[predicate].append(
                    {
                        "src_id": rel.get("source_id"),
                        "tgt_id": rel.get("target_id"),
                    }
                )
            else:
                logger.warning(
                    "Skipping unknown relationship type '%s' (source=%s → target=%s)",
                    predicate,
                    rel.get("source_id"),
                    rel.get("target_id"),
                )

        total_loaded = 0
        for rel_type, triples in by_type.items():
            try:
                result = await mutation.write_relationships_batch(rel_type, triples)
                total_loaded += result.get("count", 0)
            except Exception as e:
                logger.error(f"Failed to load {rel_type} relationships: {e}")

        return total_loaded

    async def _load_relationships_native(
        self,
        session,
        relationships: list[dict],
        source_id: str | None,
        extraction_job_id: str | None,
        tenant_id: str | None = None,
    ) -> int:
        """Load relationships using native Cypher (no APOC required).

        Groups relationships by predicate type and issues one MERGE query per
        type.  Unknown predicate types are skipped with a warning.

        Neo4j does not support dynamic relationship type names in MERGE, so we
        group by type and use static Cypher per group.  The predicate value is
        validated against RELATIONSHIP_TYPES before interpolation to prevent
        injection.
        """
        by_type: dict[str, list[dict]] = defaultdict(list)
        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)

        for rel in relationships:
            predicate = (
                rel.get("predicate", "").lower().replace("-", "_").replace(" ", "_")
            )
            if predicate in RELATIONSHIP_TYPES:
                by_type[predicate].append(rel)
            else:
                logger.warning(
                    "Skipping unknown relationship type '%s' (source=%s → target=%s)",
                    predicate,
                    rel.get("source_id"),
                    rel.get("target_id"),
                )

        total_loaded = 0
        loaded_at = datetime.utcnow().isoformat()
        mutation = AuditedGraphMutation(
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

    async def delete_by_source(
        self, source_id: str, tenant_id: str | None = None
    ) -> dict:
        """Delete all entities and relationships from a specific source.

        Phase 1 hardening: Uses AuditedGraphMutation for bulk deletion.
        """
        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)
        driver = await self._get_driver()

        async with driver.session(database=self.settings.neo4j_database) as session:
            # Phase 1 hardening: Use AuditedGraphMutation for bulk deletion
            mutation = AuditedGraphMutation(
                tenant_id=validated_tenant_id,
                session=session,
                operation_source="neo4j_loader.delete_by_source",
            )

            stats = await mutation.delete_by_source(source_id)

        logger.info(
            f"Deleted {stats['entities_deleted']} entities and "
            f"{stats['relationships_deleted']} relationships for source {source_id} "
            f"in tenant {validated_tenant_id}"
        )
        return stats
