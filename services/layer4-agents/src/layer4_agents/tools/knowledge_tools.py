from __future__ import annotations

"""Knowledge tools for querying the graph database and semantic search."""
import asyncio
import logging
import os
import re
import time
from typing import Any
from uuid import UUID

from neo4j import AsyncGraphDatabase

from ..config.settings import get_settings
from ..models.tool_schemas import (
    FindPathsInput,
    FindPathsOutput,
    GetEntityInput,
    GetEntityOutput,
    GetRelationshipsInput,
    GetRelationshipsOutput,
    QueryGraphInput,
    QueryGraphOutput,
    SemanticSearchInput,
    SemanticSearchOutput,
    ToolCategory,
    TraverseTreeInput,
    TraverseTreeOutput,
)
from ..services.llm_provider import get_llm_provider
from ..shared.domain import context as tenant_context
from ..shared.domain.context import TenantContextError
from .registry import BaseTool

logger = logging.getLogger(__name__)


class ConfigurationError(ValueError):
    """Raised when a tool is misconfigured (e.g., missing a required secret)."""


class QueryGraphTool(BaseTool):
    """Execute Cypher queries against the Neo4j knowledge graph."""

    name = "query_graph"
    category = ToolCategory.KNOWLEDGE
    description = "Executes Cypher queries against the Neo4j knowledge graph"
    input_schema = QueryGraphInput
    output_schema = QueryGraphOutput
    timeout_seconds = 30

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.neo4j_uri = (
            config.get("neo4j_uri", "bolt://localhost:7687") if config else "bolt://localhost:7687"
        )
        self.neo4j_user = config.get("neo4j_user", "neo4j") if config else "neo4j"
        self.neo4j_password = config.get("neo4j_password") if config else None
        if not self.neo4j_password:
            self.neo4j_password = get_settings().neo4j_password
        if not self.neo4j_password:
            raise ConfigurationError(
                "Neo4j password is required; set NEO4J_PASSWORD or LAYER4_NEO4J_PASSWORD"
            )
        self.database = config.get("database", "valuefabric") if config else "valuefabric"
        self._driver = None

    def _get_driver(self):
        """Lazy initialization of Neo4j driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
            )
        return self._driver

    # P1-11 FIX: Cypher keywords that indicate write/mutate operations
    _CYPHER_WRITE_KEYWORDS = re.compile(
        r"\b(CREATE|DELETE|DETACH|SET|MERGE|REMOVE|DROP|CALL)\b",
        re.IGNORECASE,
    )

    _FIRST_NODE_ALIAS_PATTERN = re.compile(
        r"\b(?:MATCH|OPTIONAL\s+MATCH)\s*(?:[A-Za-z_][A-Za-z0-9_]*\s*=\s*)?\(\s*([A-Za-z_][A-Za-z0-9_]*)\b",
        re.IGNORECASE,
    )

    _MATCH_PATTERN_PATTERN = re.compile(
        r"\b(MATCH|OPTIONAL\s+MATCH)\s*(?:[A-Za-z_][A-Za-z0-9_]*\s*=\s*)?\([^)]*\)",
        re.IGNORECASE,
    )

    def _inject_tenant_filter(self, query: str, tenant_id: UUID) -> tuple[str, str]:
        """Inject tenant_id filter into Cypher query with proper alias detection.

        This method ensures that all Cypher queries are scoped to the
        authenticated tenant by adding a tenant_id filter.

        Strategy:
        1. Extract the actual node alias from the MATCH clause (not hardcoded 'n')
        2. If query already has WHERE clause, append AND tenant_id condition
        3. If query has no WHERE, add WHERE tenant_id condition after MATCH

        Args:
            query: The Cypher query to modify
            tenant_id: The tenant UUID to filter by

        Returns:
            Tuple of (modified_query, node_alias) for parameter binding

        Raises:
            ValueError: If node alias cannot be extracted from MATCH clause
        """
        alias_match = self._FIRST_NODE_ALIAS_PATTERN.search(query)
        if not alias_match:
            raise ValueError(
                "Cannot inject tenant filter: unable to parse node alias from MATCH clause. "
                "Query must follow pattern: MATCH (alias:Label), OPTIONAL MATCH (alias), or MATCH path = (alias)"
            )

        node_alias = alias_match.group(1)
        tenant_filter = f"{node_alias}.tenant_id = $tenant_id"

        where_match = re.search(
            r"\bWHERE\b",
            query,
            re.IGNORECASE,
        )

        if where_match:
            modified_query = (
                query[: where_match.end()] + f" {tenant_filter} AND" + query[where_match.end() :]
            )
        else:
            match_pattern = self._MATCH_PATTERN_PATTERN.search(query)
            if not match_pattern:
                raise ValueError(
                    "Cannot inject tenant filter: unable to identify MATCH pattern boundary"
                )
            modified_query = (
                query[: match_pattern.end()]
                + f" WHERE {tenant_filter}"
                + query[match_pattern.end() :]
            )

        logger.debug(
            f"Injected tenant filter: alias={node_alias}, original={query[:50]}..., modified={modified_query[:50]}..."
        )
        return modified_query, node_alias

    def _ensure_tenant_parameters(self, parameters: dict | None, tenant_id) -> dict:
        """Ensure tenant_id is set in parameters, overriding any spoof attempts.

        This prevents attackers from passing a different tenant_id in the
        query parameters to access cross-tenant data.
        """
        params = dict(parameters) if parameters else {}
        # Override any tenant_id parameter with the authenticated context
        params["tenant_id"] = str(tenant_id)
        return params

    @classmethod
    def _validate_read_only(cls, query: str) -> str | None:
        """Validate that a Cypher query is read-only.

        Returns:
            Error message if query contains write operations, None if valid
        """
        if cls._CYPHER_WRITE_KEYWORDS.search(query):
            return (
                "Write operations are not allowed via query_graph tool. "
                "Only read-only Cypher queries (MATCH, RETURN, WITH, WHERE, ORDER BY, LIMIT) are permitted."
            )
        return None

    async def execute(self, input_data: QueryGraphInput) -> QueryGraphOutput:
        """Execute Cypher query against Neo4j with mandatory tenant scoping.

        SECURITY: This tool enforces tenant isolation by:
        1. Requiring valid TenantContext (fail-closed)
        2. Validating query is read-only
        3. Injecting tenant_id filter into Cypher query
        """
        start_time = time.time()

        # P0 FIX: Extract and validate tenant context (FAIL-CLOSED)
        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()
            effective_tenant_id = tenant_ctx.tenant_id
        except TenantContextError as e:
            logger.warning(f"Tenant context error in query_graph: {e}")
            return QueryGraphOutput(
                results=[],
                columns=[],
                row_count=0,
                execution_time_ms=0,
                error=f"Tenant context required: {e}. Authentication required.",
            )

        # P1-11 FIX: Validate query is read-only before execution
        validation_error = self._validate_read_only(input_data.cypher_query)
        if validation_error:
            # CONTRACT_EXCEPTION AP-7: Return structured error, don't raise
            return QueryGraphOutput(
                results=[], columns=[], row_count=0, execution_time_ms=0, error=validation_error
            )

        # P0 FIX: Inject tenant filter into Cypher query with proper alias detection
        try:
            scoped_query, node_alias = self._inject_tenant_filter(
                input_data.cypher_query, effective_tenant_id
            )
        except ValueError as e:
            # Query parsing failed, return structured error
            return QueryGraphOutput(
                results=[],
                columns=[],
                row_count=0,
                execution_time_ms=0,
                error=f"Invalid query format: {e}",
            )

        # Log with tenant context for audit trail
        logger.info(f"Executing Cypher query for tenant={effective_tenant_id}")

        driver = self._get_driver()

        start_time = time.time()

        # P0 FIX: Override any tenant_id in parameters with authenticated context
        scoped_parameters = self._ensure_tenant_parameters(
            input_data.parameters, effective_tenant_id
        )

        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(scoped_query, scoped_parameters)
                records = await result.data()

                execution_time = int((time.time() - start_time) * 1000)

                # Extract columns from first record or result keys
                columns = list(records[0].keys()) if records else []

                return QueryGraphOutput(
                    results=records,
                    columns=columns,
                    row_count=len(records),
                    execution_time_ms=execution_time,
                )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Neo4j query failed for tenant={effective_tenant_id}: {e}")
            return QueryGraphOutput(
                results=[],
                columns=[],
                row_count=0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                error="QUERY_EXECUTION_ERROR",
            )


class SemanticSearchTool(BaseTool):
    """Perform semantic search using vector similarity via Pinecone."""

    name = "semantic_search"
    category = ToolCategory.KNOWLEDGE
    description = "Performs semantic search using vector embeddings and similarity"
    input_schema = SemanticSearchInput
    output_schema = SemanticSearchOutput
    timeout_seconds = 15

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.vector_store_url = config.get("vector_store_url") if config else None
        # Default embedding model is provider-dependent.
        # Together.ai uses "togethercomputer/m2-bert-80M-8k-retrieval";
        # OpenAI uses "text-embedding-3-large".
        _default_provider = (
            os.getenv("LAYER4_LLM_PROVIDER")
            or (config.get("llm_provider") if config else None)
            or "together"
        ).lower()
        _default_embedding = (
            "togethercomputer/m2-bert-80M-8k-retrieval"
            if _default_provider == "together"
            else "text-embedding-3-large"
        )
        self.embedding_model = (
            config.get("embedding_model", _default_embedding) if config else _default_embedding
        )
        self.pinecone_api_key = config.get("pinecone_api_key") if config else None
        self.pinecone_index = (
            config.get("pinecone_index", "value-fabric") if config else "value-fabric"
        )
        self._pinecone_client = None
        self._index = None

    def _get_pinecone_client(self) -> Any | None:
        """Lazy initialization of Pinecone client.

        Returns:
            Pinecone index client, or None if API key missing
        """
        if not self.pinecone_api_key:
            # CONTRACT_EXCEPTION AP-7: Return None to signal error, don't raise.
            # Check before importing the optional dependency so the public
            # missing-configuration contract is deterministic.
            return None

        if self._pinecone_client is None:
            from pinecone import Pinecone

            self._pinecone_client = Pinecone(api_key=self.pinecone_api_key)
            self._index = self._pinecone_client.Index(self.pinecone_index)
        return self._index

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using OpenAI."""
        response = await get_llm_provider(self.config).embed(
            model=self.embedding_model,
            text=text,
        )
        return response.embeddings[0]

    async def execute(self, input_data: SemanticSearchInput) -> SemanticSearchOutput:
        """Execute semantic search against Pinecone vector store with tenant isolation.

        SECURITY: This tool enforces tenant isolation by requiring valid TenantContext
        and injecting tenant_id filter into Pinecone metadata filter.
        """
        start_time = time.time()

        # P0 FIX: Extract and validate tenant context (FAIL-CLOSED)
        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()
        except TenantContextError as e:
            logger.warning(f"Tenant context error in semantic_search: {e}")
            return SemanticSearchOutput(
                results=[],
                total_matches=0,
                query_embedding_time_ms=int((time.time() - start_time) * 1000),
                error=f"Tenant context required: {e}. Authentication required.",
            )

        try:
            # Get query embedding
            query_embedding = await self._get_embedding(input_data.query)

            # Query Pinecone
            index = self._get_pinecone_client()
            if index is None:
                # CONTRACT_EXCEPTION AP-7: Return structured error, don't raise
                return SemanticSearchOutput(
                    results=[],
                    total_matches=0,
                    query_embedding_time_ms=int((time.time() - start_time) * 1000),
                    error="Pinecone API key required for semantic search",
                )

            # P0 FIX: Build filter with mandatory tenant isolation
            filter_dict: dict[str, Any] = {"tenant_id": str(tenant_ctx.tenant_id)}
            if input_data.entity_types:
                filter_dict["entity_type"] = {"$in": input_data.entity_types}

            logger.info(
                f"Executing semantic search for tenant={tenant_ctx.tenant_id}, "
                f"user={tenant_ctx.user_id}, "
                f"query_length={len(input_data.query)}"
            )

            results = index.query(
                vector=query_embedding,
                top_k=input_data.top_k,
                include_metadata=True,
                filter=filter_dict,
            )

            # Format results
            formatted_results = []
            for match in results.matches:
                if match.score >= input_data.similarity_threshold:
                    formatted_results.append(
                        {
                            "entity_id": match.id,
                            "entity_type": match.metadata.get("entity_type", "Unknown"),
                            "name": match.metadata.get("entity_id", match.id),
                            "description": match.metadata.get("text", "")[:200],
                            "similarity_score": round(match.score, 3),
                        }
                    )

            embedding_time = int((time.time() - start_time) * 1000)

            return SemanticSearchOutput(
                results=formatted_results,
                total_matches=len(formatted_results),
                query_embedding_time_ms=embedding_time,
            )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return SemanticSearchOutput(
                results=[],
                total_matches=0,
                query_embedding_time_ms=0,
                error="SEMANTIC_SEARCH_ERROR",
            )


class GetEntityTool(BaseTool):
    """Retrieve a specific entity by ID with optional relationships from Neo4j."""

    name = "get_entity"
    category = ToolCategory.KNOWLEDGE
    description = "Retrieves a specific entity by ID with optional relationships"
    input_schema = GetEntityInput
    output_schema = GetEntityOutput
    timeout_seconds = 15

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.neo4j_uri = (
            config.get("neo4j_uri", "bolt://localhost:7687") if config else "bolt://localhost:7687"
        )
        self.neo4j_user = config.get("neo4j_user", "neo4j") if config else "neo4j"
        self.neo4j_password = config.get("neo4j_password") if config else None
        if not self.neo4j_password:
            self.neo4j_password = get_settings().neo4j_password
        if not self.neo4j_password:
            raise ConfigurationError(
                "Neo4j password is required; set NEO4J_PASSWORD or LAYER4_NEO4J_PASSWORD"
            )
        self.database = config.get("database", "valuefabric") if config else "valuefabric"
        self._driver = None

    def _get_driver(self):
        """Lazy initialization of Neo4j driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
            )
        return self._driver

    async def execute(self, input_data: GetEntityInput) -> GetEntityOutput:
        """Get entity by ID from Neo4j with mandatory tenant isolation.

        SECURITY: This tool enforces tenant isolation by requiring valid TenantContext
        and injecting tenant_id filter into Cypher queries.
        """
        # P0 FIX: Extract and validate tenant context (FAIL-CLOSED)
        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()
        except TenantContextError as e:
            logger.warning(f"Tenant context error in get_entity: {e}")
            return GetEntityOutput(
                found=False, error=f"Tenant context required: {e}. Authentication required."
            )

        driver = self._get_driver()
        entity_id = input_data.entity_id

        try:
            async with driver.session(database=self.database) as session:
                # P0 FIX: Query entity by ID with mandatory tenant filter
                entity_query = """
                    MATCH (n {id: $entity_id, tenant_id: $tenant_id})
                    RETURN n, labels(n) as labels
                    LIMIT 1
                """
                entity_result = await session.run(
                    entity_query, {"entity_id": entity_id, "tenant_id": str(tenant_ctx.tenant_id)}
                )
                entity_record = await entity_result.single()

                if not entity_record:
                    return GetEntityOutput(found=False)

                node = entity_record["n"]
                labels = entity_record["labels"]

                entity = dict(node)
                entity["entity_type"] = labels[0] if labels else "Unknown"

                relationships = []
                if input_data.include_relationships:
                    # P0 FIX: Query relationships with mandatory tenant filter on both nodes
                    rel_query = """
                        MATCH (n {id: $entity_id, tenant_id: $tenant_id})-[r]-(m {tenant_id: $tenant_id})
                        RETURN type(r) as predicate, m.id as target_id, 
                               m.name as target_name, labels(m) as target_labels
                        LIMIT $limit
                    """
                    rel_result = await session.run(
                        rel_query,
                        {
                            "entity_id": entity_id,
                            "tenant_id": str(tenant_ctx.tenant_id),
                            "limit": 50,
                        },
                    )

                    async for record in rel_result:
                        relationships.append(
                            {
                                "predicate": record["predicate"],
                                "target_id": record["target_id"],
                                "target_name": record["target_name"],
                                "target_type": record["target_labels"][0]
                                if record["target_labels"]
                                else "Unknown",
                            }
                        )

                return GetEntityOutput(entity=entity, relationships=relationships, found=True)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return GetEntityOutput(found=False, error="ENTITY_QUERY_ERROR")


class GetRelationshipsTool(BaseTool):
    """Get relationships for an entity with optional filtering from Neo4j."""

    name = "get_relationships"
    category = ToolCategory.KNOWLEDGE
    description = "Retrieves relationships for an entity with optional filtering"
    input_schema = GetRelationshipsInput
    output_schema = GetRelationshipsOutput
    timeout_seconds = 15

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.neo4j_uri = (
            config.get("neo4j_uri", "bolt://localhost:7687") if config else "bolt://localhost:7687"
        )
        self.neo4j_user = config.get("neo4j_user", "neo4j") if config else "neo4j"
        self.neo4j_password = config.get("neo4j_password") if config else None
        if not self.neo4j_password:
            self.neo4j_password = get_settings().neo4j_password
        if not self.neo4j_password:
            raise ConfigurationError(
                "Neo4j password is required; set NEO4J_PASSWORD or LAYER4_NEO4J_PASSWORD"
            )
        self.database = config.get("database", "valuefabric") if config else "valuefabric"
        self._driver = None

    def _get_driver(self):
        """Lazy initialization of Neo4j driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
            )
        return self._driver

    async def execute(self, input_data: GetRelationshipsInput) -> GetRelationshipsOutput:
        """Get relationships for entity from Neo4j with mandatory tenant isolation.

        SECURITY: This tool enforces tenant isolation by requiring valid TenantContext
        and injecting tenant_id filter into Cypher queries.
        """
        # P0 FIX: Extract and validate tenant context (FAIL-CLOSED)
        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()
        except TenantContextError as e:
            logger.warning(f"Tenant context error in get_relationships: {e}")
            return GetRelationshipsOutput(
                relationships=[],
                total_count=0,
                error=f"Tenant context required: {e}. Authentication required.",
            )

        predicate = input_data.predicate
        if predicate and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", predicate) is None:
            return GetRelationshipsOutput(
                relationships=[], total_count=0, error="INVALID_PREDICATE"
            )

        driver = self._get_driver()

        try:
            async with driver.session(database=self.database) as session:
                # P0 FIX: Build query with mandatory tenant filter and optional predicate
                tenant_id_str = str(tenant_ctx.tenant_id)

                rel_pattern = f"[r:{predicate}]" if predicate else "[r]"

                query = f"""
                    MATCH (n {{id: $entity_id, tenant_id: $tenant_id}})-{rel_pattern}->(m {{tenant_id: $tenant_id}})
                    RETURN n.id as source_id, type(r) as predicate,
                           m.id as target_id, m.name as target_name, r.confidence as confidence
                """

                result = await session.run(
                    query, {"entity_id": input_data.entity_id, "tenant_id": tenant_id_str}
                )

                relationships = []
                async for record in result:
                    relationships.append(
                        {
                            "relationship_id": f"{record['source_id']}-{record['predicate']}-{record['target_id']}",
                            "source_id": record["source_id"],
                            "predicate": record["predicate"],
                            "target_id": record["target_id"],
                            "target_name": record["target_name"],
                            "confidence": record["confidence"] or 0.8,
                        }
                    )

                total = len(relationships)
                limited = relationships[: input_data.limit]

                return GetRelationshipsOutput(relationships=limited, total_count=total)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Failed to get relationships for {input_data.entity_id}: {e}")
            return GetRelationshipsOutput(relationships=[], total_count=0)


class TraverseTreeTool(BaseTool):
    """Traverse the value tree following relationship patterns using Neo4j."""

    name = "traverse_tree"
    category = ToolCategory.KNOWLEDGE
    description = "Traverses the value tree following relationship patterns"
    input_schema = TraverseTreeInput
    output_schema = TraverseTreeOutput
    timeout_seconds = 30

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.neo4j_uri = (
            config.get("neo4j_uri", "bolt://localhost:7687") if config else "bolt://localhost:7687"
        )
        self.neo4j_user = config.get("neo4j_user", "neo4j") if config else "neo4j"
        self.neo4j_password = config.get("neo4j_password") if config else None
        if not self.neo4j_password:
            self.neo4j_password = get_settings().neo4j_password
        if not self.neo4j_password:
            raise ConfigurationError(
                "Neo4j password is required; set NEO4J_PASSWORD or LAYER4_NEO4J_PASSWORD"
            )
        self.database = config.get("database", "valuefabric") if config else "valuefabric"
        self._driver = None

    def _get_driver(self):
        """Lazy initialization of Neo4j driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
            )
        return self._driver

    async def execute(self, input_data: TraverseTreeInput) -> TraverseTreeOutput:
        """Traverse tree from starting entity using Neo4j with mandatory tenant isolation.

        SECURITY: This tool enforces tenant isolation by requiring valid TenantContext
        and injecting tenant_id filter into Cypher queries.
        """
        # P0 FIX: Extract and validate tenant context (FAIL-CLOSED)
        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()
        except TenantContextError as e:
            logger.warning(f"Tenant context error in traverse_tree: {e}")
            return TraverseTreeOutput(
                paths=[],
                nodes_discovered=0,
                error=f"Tenant context required: {e}. Authentication required.",
            )

        driver = self._get_driver()

        try:
            async with driver.session(database=self.database) as session:
                # Use variable-length path query
                relationship_types = re.findall(
                    r":([A-Za-z_][A-Za-z0-9_]*)", input_data.path_pattern
                )
                rel_pattern = "|".join(relationship_types) or "ENABLES|REQUIRES|BENEFITS"

                # P0 FIX: Query with mandatory tenant filter on all nodes in path
                query = """
                    MATCH path = (start {id: $start_id, tenant_id: $tenant_id})-[%s*1..%d]->(end {tenant_id: $tenant_id})
                    WHERE ALL(n IN nodes(path) WHERE n.tenant_id = $tenant_id)
                    RETURN [node in nodes(path) | {id: node.id, name: node.name, type: labels(node)[0]}] as path_nodes
                    LIMIT $limit
                """ % (rel_pattern, input_data.max_depth)

                result = await session.run(
                    query,
                    {
                        "start_id": input_data.start_entity_id,
                        "tenant_id": str(tenant_ctx.tenant_id),
                        "limit": 50,
                    },
                )

                paths = []
                nodes_discovered = set()

                async for record in result:
                    path_nodes = record["path_nodes"]
                    if path_nodes:
                        paths.append(path_nodes)
                        for node in path_nodes:
                            nodes_discovered.add(node.get("id"))

                return TraverseTreeOutput(paths=paths, nodes_discovered=len(nodes_discovered))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Tree traversal failed: {e}")
            return TraverseTreeOutput(paths=[], nodes_discovered=0)


class FindPathsTool(BaseTool):
    """Find paths between two entities in the knowledge graph using Neo4j."""

    name = "find_paths"
    category = ToolCategory.KNOWLEDGE
    description = "Finds connection paths between two entities in the graph"
    input_schema = FindPathsInput
    output_schema = FindPathsOutput
    timeout_seconds = 30

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.neo4j_uri = (
            config.get("neo4j_uri", "bolt://localhost:7687") if config else "bolt://localhost:7687"
        )
        self.neo4j_user = config.get("neo4j_user", "neo4j") if config else "neo4j"
        self.neo4j_password = config.get("neo4j_password") if config else None
        if not self.neo4j_password:
            self.neo4j_password = get_settings().neo4j_password
        if not self.neo4j_password:
            raise ConfigurationError(
                "Neo4j password is required; set NEO4J_PASSWORD or LAYER4_NEO4J_PASSWORD"
            )
        self.database = config.get("database", "valuefabric") if config else "valuefabric"
        self._driver = None

    def _get_driver(self):
        """Lazy initialization of Neo4j driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
            )
        return self._driver

    async def execute(self, input_data: FindPathsInput) -> FindPathsOutput:
        """Find paths between entities using Neo4j shortest path algorithms with mandatory tenant isolation.

        SECURITY: This tool enforces tenant isolation by requiring valid TenantContext
        and injecting tenant_id filter into Cypher queries.
        """
        # P0 FIX: Extract and validate tenant context (FAIL-CLOSED)
        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()
        except TenantContextError as e:
            logger.warning(f"Tenant context error in find_paths: {e}")
            return FindPathsOutput(
                paths=[],
                shortest_path_length=None,
                error=f"Tenant context required: {e}. Authentication required.",
            )

        driver = self._get_driver()

        try:
            async with driver.session(database=self.database) as session:
                # P0 FIX: Query with mandatory tenant filter on source, target, and all path nodes
                query = (
                    """
                    MATCH (source {id: $source_id, tenant_id: $tenant_id}), 
                          (target {id: $target_id, tenant_id: $tenant_id})
                    MATCH path = allShortestPaths((source)-[*1..%d]->(target))
                    WHERE ALL(n IN nodes(path) WHERE n.tenant_id = $tenant_id)
                    RETURN [node in nodes(path) | {id: node.id, name: node.name}] as path_nodes,
                           [rel in relationships(path) | type(rel)] as rel_types,
                           length(path) as path_length
                    LIMIT $limit
                """
                    % input_data.max_length
                )

                result = await session.run(
                    query,
                    {
                        "source_id": input_data.source_id,
                        "target_id": input_data.target_id,
                        "tenant_id": str(tenant_ctx.tenant_id),
                        "limit": 50,
                    },
                )

                paths = []
                shortest_length = None

                async for record in result:
                    path_nodes = record["path_nodes"]
                    rel_types = record["rel_types"]
                    path_length = record["path_length"]

                    if shortest_length is None or path_length < shortest_length:
                        shortest_length = path_length

                    paths.append(
                        {
                            "path_length": path_length,
                            "nodes": path_nodes,
                            "relationships": rel_types,
                        }
                    )

                return FindPathsOutput(paths=paths, shortest_path_length=shortest_length)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Path finding failed: {e}")
            return FindPathsOutput(paths=[], shortest_path_length=None)
