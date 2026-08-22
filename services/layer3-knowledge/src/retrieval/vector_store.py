"""
Neo4j-native vector store for entity embeddings.

Replaces the previous Pinecone-based implementation.  Uses Neo4j 5.x
vector indexes (``CREATE VECTOR INDEX``) with ``db.index.vector.queryNodes``
for ANN search.  No external vector database required.

Embedding model: sentence-transformers/all-MiniLM-L6-v2 (384-dim, fast)
or text-embedding-3-small compatible (1536-dim).  Dimension is read from
config so it can be changed without code changes.

Design notes:
- Embeddings are stored as a Float[] property on each entity node.
- The vector index is created by SchemaInitializer at startup.
- This class is stateless with respect to the driver — it accepts an
  injected driver so it can be tested with a testcontainers Neo4j instance.
- Pinecone dependency has been removed from pyproject.toml.
"""

import logging
from typing import Any

from neo4j import AsyncDriver, Record
from neo4j.exceptions import ClientError, ServiceUnavailable
from value_fabric.shared.identity.context import get_request_context
from value_fabric.shared.identity.isolation import (
    ScopedQuery,
    SystemCypher,
    TenantScopedCypher,
)
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..config import Settings, get_settings
from ..config.embedding_dimension import validate_embedding_dimension
from ..db.driver import get_driver
from ..db.query_execution import run_scoped_query
from ..metrics.prometheus_metrics import get_metrics


class Neo4jVectorStore_index_healthResult(TypedDictModel):
    error: Any
    indexes: dict[str, Any]
    status: str

class Neo4jVectorStore_upsert_batchResult(TypedDictModel):
    failed: list[Any]
    upserted: int

class Neo4jVectorStore_upsert_entityResult(TypedDictModel):
    entity_id: Any
    entity_type: Any
    upserted: Any

logger = logging.getLogger(__name__)

# Supported entity types for vector search
VECTOR_ENTITY_TYPES = ["Capability", "UseCase", "Persona", "ValueDriver"]


class VectorStoreError(Exception):
    """Raised when a vector store operation fails."""


class Neo4jVectorStore:
    """Neo4j-native vector store using built-in ANN indexes."""

    def __init__(
        self,
        driver: AsyncDriver | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._driver = driver
        self._owned_driver = driver is None
        self._embedding_model = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Driver access
    # ------------------------------------------------------------------

    async def _get_driver(self) -> AsyncDriver:
        if self._driver is None:
            self._driver = await get_driver(self.settings)
        return self._driver

    async def close(self) -> None:
        if self._owned_driver and self._driver is not None:
            await self._driver.close()
            self._driver = None

    # ------------------------------------------------------------------
    # Embedding model (lazy-loaded)
    # ------------------------------------------------------------------

    def _get_embedding_model(self) -> object:
        """Get or initialize the embedding model.

        Production: Requires sentence_transformers installed. Fails hard if unavailable.
        """
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            model_name = getattr(self.settings, "embedding_model", "all-MiniLM-L6-v2")
            self._embedding_model = SentenceTransformer(model_name)
            validate_embedding_dimension(
                configured_dimension=self.settings.embedding_dimension,
                model=self._embedding_model,
                model_name=model_name,
            )
            logger.info("Loaded embedding model: %s", model_name)
        return self._embedding_model

    def _embed(self, text: str) -> list[float]:
        model = self._get_embedding_model()
        embedding = model.encode(text, normalize_embeddings=True).tolist()
        self._validate_vector_length(embedding)
        return embedding

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._get_embedding_model()
        vectors = [
            v.tolist()
            for v in model.encode(texts, normalize_embeddings=True, batch_size=32)
        ]
        for vector in vectors:
            self._validate_vector_length(vector)
        return vectors

    def _validate_vector_length(self, vector: list[float]) -> None:
        if len(vector) != self.settings.embedding_dimension:
            raise VectorStoreError(
                f"VECTOR_DIMENSION_MISMATCH: expected={self.settings.embedding_dimension} actual={len(vector)}"
            )

    def _resolve_tenant_id(self, tenant_id: str | None = None) -> str:
        """Return the explicit or request-context tenant, failing closed if absent."""
        if tenant_id:
            return str(tenant_id)
        ctx = get_request_context()
        if ctx and ctx.tenant_id:
            return str(ctx.tenant_id)
        raise ValueError("tenant_id is required for tenant-scoped vector store operations")

    async def _run_scoped_single(self, scoped: ScopedQuery) -> Record | None:
        """Execute a scoped query and consume the first record inside the session."""
        driver = await self._get_driver()
        async with driver.session(database=self.settings.neo4j_database) as session:
            result = await run_scoped_query(session.run, scoped)
            return await result.single()

    async def _run_scoped_list(self, scoped: ScopedQuery) -> list[Record]:
        """Execute a scoped query and consume all records inside the session."""
        driver = await self._get_driver()
        async with driver.session(database=self.settings.neo4j_database) as session:
            result = await run_scoped_query(session.run, scoped)
            return [record async for record in result]

    @staticmethod
    def _clean_entity_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
        """Filter out tenant IDs and non-primitive values from metadata."""
        return {
            k: v
            for k, v in (metadata or {}).items()
            if k not in {"tenant_id", "tenantId"} and isinstance(v, (str, int, float, bool))
        }

    @staticmethod
    def _build_vector_search_query(
        builder: TenantScopedCypher,
        index_name: str,
        query_embedding: list[float],
        top_k: int,
        min_score: float,
        etype: str,
    ) -> ScopedQuery:
        """Construct scoped vector search Cypher query."""
        return builder.custom_tenant_query(
            """
            CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
            YIELD node, score
            WHERE node.tenant_id = $_tenant_id AND score >= $min_score
            RETURN
                node.id AS entity_id,
                labels(node)[0] AS entity_type,
                score,
                node.name AS name,
                node.description AS description,
                node.confidence AS confidence
            ORDER BY score DESC
            """,
            params={
                "index_name": index_name,
                "top_k": top_k,
                "embedding": query_embedding,
                "min_score": min_score,
            },
            operation="vector_search",
            labels=(etype,),
        )

    @staticmethod
    def _format_search_record(record: Record | dict[str, Any]) -> tuple[str, float, dict[str, Any]]:
        """Format a Neo4j vector search record into standard (id, score, meta) tuple."""
        return (
            record["entity_id"],
            record["score"],
            {
                "entity_type": record["entity_type"],
                "name": record["name"],
                "description": record["description"],
                "confidence": record["confidence"],
            },
        )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def upsert_entity(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Upsert a single entity embedding into Neo4j."""
        if entity_type not in VECTOR_ENTITY_TYPES:
            raise VectorStoreError(
                f"Unknown entity type '{entity_type}'. Supported: {VECTOR_ENTITY_TYPES}"
            )

        tenant = self._resolve_tenant_id(tenant_id if tenant_id is not None else (metadata or {}).get("tenant_id"))
        embedding = self._embed(text)
        clean_metadata = self._clean_entity_metadata(metadata)
        builder = TenantScopedCypher(tenant)
        scoped = builder.custom_tenant_query(
            "MERGE (n:" + entity_type + " {id: $id, tenant_id: $_tenant_id})\n"  # cypher-dynamic-safe: validated against VECTOR_ENTITY_TYPES allowlist  # cypher-mutation-safe: label validated, tenant-scoped upsert
            "            ON CREATE SET n.created_at = datetime()\n"
            "            SET\n"
            "                n.embedding = $embedding,\n"
            "                n.embedding_text = $text,\n"
            "                n.embedding_updated_at = datetime(),\n"
            "                n += $metadata\n"
            "            WITH n\n"
            "            WHERE n.tenant_id = $_tenant_id\n"
            "            RETURN n.id AS entity_id, true AS upserted\n"
            "            ",
            params={
                "id": entity_id,
                "embedding": embedding,
                "text": text[:2000],
                "metadata": clean_metadata,
            },
            operation="vector_upsert_entity",
            labels=(entity_type,),
        )

        try:
            record = await self._run_scoped_single(scoped)
            return Neo4jVectorStore_upsert_entityResult.model_validate({
                "entity_id": record["entity_id"] if record else entity_id,
                "entity_type": entity_type,
                "upserted": record["upserted"] if record else False,
            })


        except (ClientError, ServiceUnavailable) as exc:
            raise VectorStoreError(
                f"Failed to upsert entity {entity_id}: {exc}"
            ) from exc

    async def upsert_batch(
        self,
        entities: list[dict[str, Any]],
        entity_type: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Batch upsert entity embeddings."""
        if not entities:
            return Neo4jVectorStore_upsert_batchResult.model_validate({"upserted": 0, "failed": []})

        if entity_type not in VECTOR_ENTITY_TYPES:
            raise VectorStoreError(
                f"Unknown entity type '{entity_type}'. Supported: {VECTOR_ENTITY_TYPES}"
            )

        tenant = self._resolve_tenant_id(tenant_id if tenant_id is not None else entities[0].get("tenant_id"))
        texts = [e.get("text", e.get("name", "")) for e in entities]
        embeddings = self._embed_batch(texts)

        records = []
        for entity, embedding, text in zip(entities, embeddings, texts):
            records.append(
                {
                    "id": entity["id"],
                    "embedding": embedding,
                    "text": text[:2000],
                    "metadata": {
                            k: v
                            for k, v in entity.items()
                            if k not in ("id", "text", "embedding", "tenant_id", "tenantId")
                            and isinstance(v, (str, int, float, bool))
                    },
                }
            )

        builder = TenantScopedCypher(tenant)
        scoped = builder.custom_tenant_query(
            "UNWIND $records AS rec\n"
            "            MERGE (n:" + entity_type + " {id: rec.id, tenant_id: $_tenant_id})\n"  # cypher-dynamic-safe: validated against VECTOR_ENTITY_TYPES allowlist  # cypher-mutation-safe: label validated, tenant-scoped batch upsert
            "            WITH n, rec\n"
            "            WHERE n.tenant_id = $_tenant_id\n"
            "            SET\n"
            "                n.embedding = rec.embedding,\n"
            "                n.embedding_text = rec.text,\n"
            "                n += rec.metadata,\n"
            "                n.embedding_updated_at = datetime()\n"
            "            RETURN count(n) AS upserted\n"
            "            ",
            params={"records": records},
            operation="vector_upsert_batch",
            labels=(entity_type,),
        )

        try:
            record = await self._run_scoped_single(scoped)
            return Neo4jVectorStore_upsert_batchResult.model_validate({"upserted": record["upserted"] if record else 0, "failed": []})
        except (ClientError, ServiceUnavailable) as exc:
            logger.error("Batch upsert failed for %s: %s", entity_type, exc)
            return Neo4jVectorStore_upsert_batchResult.model_validate({"upserted": 0, "failed": [e["id"] for e in entities]})

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def search(
        self,
        query_text: str,
        entity_type: str | None = None,
        top_k: int = 10,
        min_score: float = 0.0,
        tenant_id: str | None = None,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """ANN vector search using Neo4j native vector index."""
        tenant = self._resolve_tenant_id(tenant_id)
        query_embedding = self._embed(query_text)
        types_to_search = [entity_type] if entity_type else VECTOR_ENTITY_TYPES
        all_results: list[tuple[str, float, dict[str, Any]]] = []

        for etype in types_to_search:
            index_name = f"{etype.lower()}_embedding_idx"
            builder = TenantScopedCypher(tenant)
            scoped = self._build_vector_search_query(
                builder=builder,
                index_name=index_name,
                query_embedding=query_embedding,
                top_k=top_k,
                min_score=min_score,
                etype=etype,
            )
            try:
                records = await self._run_scoped_list(scoped)
                for record in records:
                    all_results.append(self._format_search_record(record))
            except ClientError as exc:
                if (
                    "index does not exist" in str(exc).lower()
                    or "no such index" in str(exc).lower()
                ):
                    logger.warning(
                        "Vector index '%s' not found — falling back for %s",
                        index_name,
                        etype,
                    )
                    continue
                logger.error("Vector search failed for %s: %s", etype, exc)

        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:top_k]

    async def delete_entity(self, entity_id: str, tenant_id: str) -> bool:
        """Remove the embedding property from an entity node with tenant filtering.
        
        Args:
            entity_id: Entity identifier
            tenant_id: Tenant identifier (required for multi-tenant security)
            
        Returns:
            True if embedding was deleted, False otherwise
            
        Raises:
            ValueError: If tenant_id is None or empty
        """
        if not tenant_id:
            raise ValueError("tenant_id is required for delete_entity")
        
        builder = TenantScopedCypher(tenant_id)
        scoped = builder.custom_tenant_query(
            """
            MATCH (n {id: $id})
            WHERE n.tenant_id = $_tenant_id
            REMOVE n.embedding, n.embedding_text, n.embedding_updated_at
            RETURN count(n) AS updated
            """,
            params={"id": entity_id},
            operation="vector_delete_entity",
            labels=("*",),
        )
        try:
            record = await self._run_scoped_single(scoped)
            return bool(record and record["updated"] > 0)
        except (ClientError, ServiceUnavailable) as exc:
            logger.error("Failed to delete embedding for %s: %s", entity_id, exc)  # cypher-mutation-safe: log message, not a Cypher query
            return False

    async def index_health(self) -> dict[str, Any]:
        """Check whether all expected vector indexes exist and are online."""
        driver = await self._get_driver()
        details: dict[str, Any] = {}
        all_online = True
        scoped = SystemCypher.schema_operation(
            "SHOW INDEXES YIELD name, type, state WHERE type = 'VECTOR'",
            reason="Vector index health inspects global Neo4j index metadata",
            allowlist_key="vector_store.index_health",
        )

        try:
            async with driver.session(database=self.settings.neo4j_database) as session:
                result = await run_scoped_query(session, scoped)
                existing = {r["name"]: r["state"] async for r in result}

            for etype in VECTOR_ENTITY_TYPES:
                index_name = f"{etype.lower()}_embedding_idx"
                state = existing.get(index_name)
                online = state == "ONLINE"
                if not online:
                    all_online = False
                    metrics = get_metrics()
                    if metrics:
                        metrics.increment_index_constraint_health_failure(
                            check_type="vector_index", component=index_name
                        )
                details[index_name] = {
                    "entity_type": etype,
                    "state": state or "MISSING",
                    "online": online,
                }

        except (ClientError, ServiceUnavailable):
            metrics = get_metrics()
            if metrics:
                metrics.increment_index_constraint_health_failure(
                    check_type="vector_index_query", component="neo4j_vector_store"
                )
            return Neo4jVectorStore_index_healthResult.model_validate({"status": "unhealthy", "error": "Neo4j vector store health check failed", "error_code": "NEO4J_VECTOR_STORE_ERROR", "indexes": {}})

        return Neo4jVectorStore_index_healthResult.model_validate({
            "status": "healthy" if all_online else "degraded",
            "indexes": details,
        })


# Backwards-compatibility alias
VectorStore = Neo4jVectorStore
