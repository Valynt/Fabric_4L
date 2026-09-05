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
from ..models.embedding_space import resolve_embedding_space
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
from ..shared.security.cypher_security import (
    ALLOWED_REL_TYPES,
    validate_cypher_identifier,
)
from ..shared.security.tenant_guard import enforce_tenant_context
from .registry import BaseTool, TenantSpoofingError

logger = logging.getLogger(__name__)


def _mask_cypher_literals(query: str) -> str:
    """Return ``query`` with all non-code regions blanked out (same length).

    Masks single- and double-quoted string literals (with backslash escapes
    and doubled-quote escapes), backtick-quoted identifiers, and ``//`` /
    ``/* */`` comments, replacing every masked character with a space
    (newlines preserved). Positions are unchanged, so keyword/alias scans on
    the masked text map 1:1 onto the original query. This prevents clause
    keywords such as RETURN/WHERE/WITH/UNION appearing inside literals or
    comments from being mistaken for real Cypher syntax (and vice versa).
    """
    chars = list(query)
    n = len(query)
    i = 0
    while i < n:
        c = query[i]
        if c == "/" and i + 1 < n and query[i + 1] == "/":
            end = query.find("\n", i)
            end = n if end == -1 else end
            for k in range(i, end):
                chars[k] = " "
            i = end
        elif c == "/" and i + 1 < n and query[i + 1] == "*":
            end = query.find("*/", i + 2)
            end = n if end == -1 else end + 2
            for k in range(i, end):
                if chars[k] != "\n":
                    chars[k] = " "
            i = end
        elif c in ("'", '"', "`"):
            quote = c
            start = i
            i += 1
            while i < n:
                ch = query[i]
                if ch == "\\" and quote != "`":
                    i += 2
                    continue
                if ch == quote:
                    # Doubled-quote escape ('', "", ``) stays inside.
                    if i + 1 < n and query[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            for k in range(start, i):
                if chars[k] != "\n":
                    chars[k] = " "
        else:
            i += 1
    return "".join(chars)


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

    _CYPHER_WRITE_KEYWORDS = re.compile(
        r"(?<![\.\:\`])\b(CREATE|DELETE|DETACH|SET|MERGE|REMOVE|DROP|CALL)\b(?!\s*\:)",
        re.IGNORECASE,
    )

    _FIRST_NODE_ALIAS_PATTERN = re.compile(
        r"\b(?:MATCH|OPTIONAL\s+MATCH)\s*(?:[A-Za-z_][A-Za-z0-9_]*\s*=\s*)?\(\s*([A-Za-z_][A-Za-z0-9_]*)\b",
        re.IGNORECASE,
    )

    _NEXT_CLAUSE_PATTERN = re.compile(
        r"\b(RETURN|WITH|MATCH|OPTIONAL\s+MATCH|SET|DELETE|CREATE|MERGE|YIELD|CALL|UNWIND|ORDER\s+BY|LIMIT|SKIP)\b",
        re.IGNORECASE,
    )

    # Reads that still allow an unscoped second query leg or statement: the
    # tenant filter is injected at a single point, so anything that adds a
    # second leg/statement would bypass it and must be rejected (fail closed).
    _CYPHER_MULTI_LEG_KEYWORDS = re.compile(
        r"(?<![\.\:\`])\b(UNION)\b(?!\s*\:)",
        re.IGNORECASE,
    )

    _MATCH_CLAUSE_PATTERN = re.compile(
        r"\b(?:OPTIONAL\s+)?MATCH\b",
        re.IGNORECASE,
    )

    _NODE_ALIAS_IN_PATTERN = re.compile(r"\(\s*([A-Za-z_][A-Za-z0-9_]*)\b")

    # Pattern comprehensions bind fresh node/relationship aliases INSIDE a
    # list projection (e.g. [(n)-->(m) | m.name], [p = (n)-[*1..3]->(m) | p]).
    # The tenant filter only scopes the outer MATCH aliases, so inner aliases
    # would be unrestricted and leak cross-tenant properties. There is no safe
    # single-point injection for them -> reject (fail closed). Detected as
    # '[' ... relationship pattern (paren + dash/arrow) ... '|' on the MASKED
    # query, so brackets/arrows inside string literals and plain list
    # literals ([1,2,3], no relationship pattern) do NOT match.
    _PATTERN_COMPREHENSION = re.compile(
        r"\[(?:[^\[\]]|\[[^\]]*\])*\((?:[^\[\]]|\[[^\]]*\])*[-<>](?:[^\[\]]|\[[^\]]*\])*\|",
        re.IGNORECASE,
    )

    # Subquery forms bind fresh aliases the injected filter cannot scope:
    # exists((n)-->(m)), EXISTS { ... }, COUNT { ... }. Plain count(...)
    # aggregation is unaffected (no '{').
    _SUBQUERY_SYNTAX = re.compile(
        r"\bexists\s*\(|\b(?:EXISTS|COUNT)\s*\{",
        re.IGNORECASE,
    )

    # startNode()/endNode() exist to reach UNALIASED relationship endpoints;
    # those endpoints carry no injected tenant predicate, so the functions
    # would expose cross-tenant nodes. No legitimate single-MATCH read in
    # this tool's surface needs them -> reject (fail closed).
    _ENDPOINT_FUNCTIONS = re.compile(
        r"\b(?:startnode|endnode)\s*\(",
        re.IGNORECASE,
    )

    # Anonymous node `()` in node position within a MATCH pattern: a '(' at
    # pattern start or immediately after ']', '-', '>', '<' or ',' that is
    # NOT followed by an alias character. Function-call parens (preceded by
    # an identifier char) never match. Applied to the masked MATCH pattern
    # region only, so '()' inside string literals is inert.
    _ANONYMOUS_NODE = re.compile(r"(?:[\]\-><,]|^)\s*\(\s*(?![A-Za-z_`])")

    # Variable-length relationship patterns (-[*1..3]->, -[*2]->, -[*1..]->)
    # match intermediate nodes that carry NO injected tenant predicate, so
    # nodes(p)/relationships(p) or endpoint projection can expose other
    # tenants' data. Sibling tools close this with
    # ALL(x IN nodes(path) WHERE x.tenant_id = $tenant_id); this tool fails
    # closed instead.
    # A '*' ANYWHERE inside a relationship bracket is rejected: anonymous
    # -[*1..3]->, named -[r*1..2]->, typed -[:KNOWS*2]->, and spaced
    # -[r *2..]-> forms all produce var-length matches. Detected on the
    # masked query, so '*' inside string literals is inert and plain
    # multiplication (n.score * 2, no bracket) never matches. Documented
    # collateral: list literals containing '*' (e.g. [n.score * 2]) are
    # indistinguishable from rel brackets without a full parser and fail
    # closed too. Map projections n { .* } use braces and are unaffected.
    _VARIABLE_LENGTH_PATTERN = re.compile(r"\[[^\]]*\*")

    # nodes()/relationships() project every node/edge on a path, including
    # unfiltered intermediates; same rationale as startNode()/endNode().
    _PATH_FUNCTIONS = re.compile(
        r"\b(?:nodes|relationships)\s*\(",
        re.IGNORECASE,
    )

    # Path-variable assignment in a MATCH pattern (p = (n)-->(m)): a named
    # path lets nodes(p)/relationships(p) reach edge properties and would
    # also be the vehicle for variable-length traversal, so it is rejected
    # alongside them (belt-and-braces after _VARIABLE_LENGTH_PATTERN).
    _PATH_VARIABLE_ASSIGNMENT = re.compile(
        r"(?:^|,)\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*\("
    )

    def _inject_tenant_filter(self, query: str, tenant_id: UUID) -> tuple[str, str]:
        """Inject tenant_id filter into Cypher query with proper alias detection.

        This method ensures that all Cypher queries are scoped to the
        authenticated tenant by adding a tenant_id filter.

        Strategy:
        1. Extract every node alias bound by the FIRST MATCH clause (all of
           them are in scope for that clause's WHERE). Reject (fail closed)
           when a later MATCH/OPTIONAL MATCH binds a fresh alias, because such
           an alias cannot be safely scoped by a single injection point.
        2. If the query already has a WHERE clause, prepend the tenant
           predicates AND wrap the original predicate in parentheses so a
           hostile top-level ``OR`` cannot escape the tenant filter.
        3. If the query has no WHERE, add ``WHERE <predicates>`` after MATCH.

        Args:
            query: The Cypher query to modify
            tenant_id: The tenant UUID to filter by

        Returns:
            Tuple of (modified_query, node_alias) for parameter binding

        Raises:
            ValueError: If node alias cannot be extracted from MATCH clause or
                the query shape cannot be safely tenant-scoped.
        """
        # Mask string literals, backtick identifiers and comments BEFORE any
        # keyword/alias scanning. All scans run on the masked text (same
        # length, positions preserved); injections splice the ORIGINAL text.
        # This stops clause keywords inside literals/comments (e.g. 'RETURN',
        # 'WITH', 'UNION') from being mistaken for real syntax — in both
        # directions: hostile queries cannot hide or fake clause boundaries,
        # and legitimate literals keep working (V1-TENANCY-012 F1/F2).
        masked = _mask_cypher_literals(query)

        alias_match = self._FIRST_NODE_ALIAS_PATTERN.search(masked)
        if not alias_match:
            raise ValueError(
                "Cannot inject tenant filter: unable to parse node alias from MATCH clause. "
                "Query must follow pattern: MATCH (alias:Label), OPTIONAL MATCH (alias), or MATCH path = (alias)"
            )

        node_alias = alias_match.group(1)

        # Collect every node alias bound by the first MATCH clause; all of
        # them are in scope at that clause's WHERE position.
        match_clauses = list(self._MATCH_CLAUSE_PATTERN.finditer(masked))
        first_clause_end = (
            match_clauses[1].start() if len(match_clauses) > 1 else len(query)
        )
        first_pattern_end = first_clause_end
        next_clause_match = self._NEXT_CLAUSE_PATTERN.search(
            masked, pos=match_clauses[0].end()
        )
        if next_clause_match and next_clause_match.start() < first_pattern_end:
            first_pattern_end = next_clause_match.start()

        # Fail closed on anonymous nodes in the MATCH pattern: an unaliased
        # node carries no injected tenant predicate, so relationships can
        # reach cross-tenant nodes through it (V1-TENANCY-012 F5). Anonymous
        # RELATIONSHIPS remain allowed: without an alias no relationship
        # properties can be projected, both endpoints (when aliased) are
        # filtered, and startNode()/endNode() are rejected separately.
        first_pattern_masked = masked[match_clauses[0].end() : first_pattern_end]
        if self._PATH_VARIABLE_ASSIGNMENT.search(first_pattern_masked):
            # Named paths would let nodes(p)/relationships(p) project edges
            # and intermediate nodes outside the injected tenant predicates.
            raise ValueError(
                "Cannot inject tenant filter: path-variable assignment in "
                "MATCH pattern. Match nodes/relationships directly so every "
                "element carries the tenant filter."
            )
        if self._ANONYMOUS_NODE.search(first_pattern_masked):
            raise ValueError(
                "Cannot inject tenant filter: anonymous node '()' in MATCH "
                "pattern. Alias every node so the tenant filter can be "
                "applied to all of them."
            )

        first_clause_aliases: list[str] = list(
            dict.fromkeys(
                self._NODE_ALIAS_IN_PATTERN.findall(
                    masked[match_clauses[0].end() : first_pattern_end]
                )
            )
        )
        if node_alias not in first_clause_aliases:
            first_clause_aliases.insert(0, node_alias)

        # Fail closed when a later MATCH binds an alias that is not in scope
        # at the injection point (it would bypass the tenant filter).
        for later in match_clauses[1:]:
            later_end_match = self._NEXT_CLAUSE_PATTERN.search(masked, pos=later.end())
            later_end = later_end_match.start() if later_end_match else len(query)
            later_aliases = self._NODE_ALIAS_IN_PATTERN.findall(
                masked[later.end() : later_end]
            )
            unscoped = [a for a in later_aliases if a not in first_clause_aliases]
            if unscoped:
                raise ValueError(
                    "Cannot inject tenant filter: query binds node alias(es) "
                    f"{unscoped} in a later MATCH clause that cannot be "
                    "tenant-scoped safely. Re-issue as a single-MATCH query."
                )

        tenant_filter = " AND ".join(
            f"{alias}.tenant_id = $tenant_id" for alias in first_clause_aliases
        )

        where_match = re.search(
            r"\bWHERE\b",
            masked,
            re.IGNORECASE,
        )

        if where_match:
            # Parenthesise the original predicate so a hostile top-level OR
            # cannot escape the injected tenant predicates.
            predicate_end_match = self._NEXT_CLAUSE_PATTERN.search(
                masked, pos=where_match.end()
            )
            predicate_end = (
                predicate_end_match.start() if predicate_end_match else len(query)
            )
            # Fail closed on unbalanced parentheses in the predicate: a
            # predicate whose parens only balance via string-literal content
            # could close our wrapping parenthesis early and escape the
            # tenant filter with a trailing OR (V1-TENANCY-012 F2).
            predicate_masked = masked[where_match.end() : predicate_end]
            if predicate_masked.count("(") != predicate_masked.count(")"):
                raise ValueError(
                    "Cannot inject tenant filter: unbalanced parentheses in "
                    "WHERE predicate. Simplify the predicate and retry."
                )
            modified_query = (
                query[: where_match.end()]
                + f" {tenant_filter} AND ("
                + query[where_match.end() : predicate_end]
                + ") "
                + query[predicate_end:]
            )
        else:
            match_keyword = re.search(r"\b(MATCH|OPTIONAL\s+MATCH)\b", masked, re.IGNORECASE)
            start_pos = match_keyword.end() if match_keyword else 0

            next_clause_match = self._NEXT_CLAUSE_PATTERN.search(masked, pos=start_pos)
            if next_clause_match:
                insert_pos = next_clause_match.start()
                modified_query = query[:insert_pos] + f"WHERE {tenant_filter} " + query[insert_pos:]
            else:
                modified_query = query + f" WHERE {tenant_filter}"

        logger.debug(
            f"Injected tenant filter: alias={node_alias}, original={query[:50]}..., modified={modified_query[:50]}..."
        )
        return modified_query, node_alias

    def _ensure_tenant_parameters(self, parameters: dict | None, tenant_id) -> dict:
        """Ensure tenant_id is set in parameters, rejecting any spoof attempts.

        This prevents attackers from passing a different tenant_id in the
        query parameters to access cross-tenant data.
        """
        params = dict(parameters) if parameters else {}
        # Detect and reject any tenant_id-like parameter that does not match
        # the authenticated context, then ensure tenant_id is set correctly.
        for key in list(params.keys()):
            if "tenant_id" in key.lower() and str(params[key]) != str(tenant_id):
                raise TenantSpoofingError(
                    "Tenant spoofing detected: parameter tenant_id does not match authenticated context"
                )
        params["tenant_id"] = str(tenant_id)
        return params

    @classmethod
    def _validate_read_only(cls, query: str) -> str | None:
        """Validate that a Cypher query is read-only.

        Returns:
            Error message if query contains write operations, None if valid
        """
        # Scan only real Cypher syntax: keywords inside string literals,
        # backtick identifiers or comments are inert text and must neither
        # trigger false rejections nor smuggle actual syntax past the scan.
        masked = _mask_cypher_literals(query)
        if cls._CYPHER_WRITE_KEYWORDS.search(masked):
            return (
                "Write operations are not allowed via query_graph tool. "
                "Only read-only Cypher queries (MATCH, RETURN, WITH, WHERE, ORDER BY, LIMIT) are permitted."
            )
        if cls._CYPHER_MULTI_LEG_KEYWORDS.search(masked) or ";" in masked:
            # UNION legs and chained statements bypass the single-point tenant
            # filter injection; reject them so the query fails closed.
            return (
                "Multi-leg or chained Cypher queries are not allowed via query_graph tool. "
                "Issue a single MATCH...RETURN statement so the tenant filter can be enforced."
            )
        if cls._PATTERN_COMPREHENSION.search(masked) or cls._SUBQUERY_SYNTAX.search(masked):
            # Pattern comprehensions and exists()/EXISTS{}/COUNT{} subqueries
            # bind fresh aliases the tenant filter cannot scope; fail closed.
            return (
                "Pattern comprehensions and Cypher subqueries are not allowed via query_graph tool. "
                "Express the read as a plain MATCH...WHERE...RETURN so the tenant filter can be enforced."
            )
        if cls._ENDPOINT_FUNCTIONS.search(masked):
            # startNode()/endNode() reach unaliased (unfiltered) endpoints.
            return (
                "startNode()/endNode() are not allowed via query_graph tool. "
                "Alias every relationship endpoint so the tenant filter can be enforced."
            )
        if cls._VARIABLE_LENGTH_PATTERN.search(masked) or cls._PATH_FUNCTIONS.search(masked):
            # Variable-length paths expose unfiltered intermediate nodes via
            # nodes(p)/relationships(p); those functions are banned too.
            return (
                "Variable-length paths and nodes()/relationships() are not allowed via "
                "query_graph tool. Use fixed single-hop patterns so every node carries "
                "the tenant filter."
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


        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()
            effective_tenant_id = tenant_ctx.tenant_id

            enforce_tenant_context(
                getattr(input_data, "tenant_id", None), tenant_ctx.tenant_id
            )
        except TenantContextError as e:
            logger.warning(
                "Tenant context error in query_graph: %s",
                e,
            )
            return QueryGraphOutput(
                results=[],
                columns=[],
                row_count=0,
                error="Invalid tenant context",
            )

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
        # Resolve the embedding space declaratively from an explicit space name,
        # provider, or the ambient LAYER4_LLM_PROVIDER. Anthropic falls back to
        # an approved embedding provider (together), never failing at runtime.
        space_name = config.get("embedding_space") if config else None
        configured_model = config.get("embedding_model") if config else None
        configured_provider = config.get("llm_provider") if config else None

        if space_name:
            self.embedding_space = resolve_embedding_space(space_name=space_name)
        else:
            self.embedding_space = resolve_embedding_space(
                provider=(configured_provider or os.getenv("LAYER4_LLM_PROVIDER"))
            )

        self.embedding_model = configured_model or self.embedding_space.model
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
        """Get embedding for text using the resolved EmbeddingSpace provider."""
        provider_config = dict(self.config) if self.config else {}
        if provider_config.get("llm_provider", "").lower() in ("anthropic", ""):
            provider_config["llm_provider"] = self.embedding_space.provider

        response = await get_llm_provider(provider_config).embed(
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


        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()

            enforce_tenant_context(
                getattr(input_data, "tenant_id", None), tenant_ctx.tenant_id
            )
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


            filter_dict = {"tenant_id": str(tenant_ctx.tenant_id)}
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

        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()

            enforce_tenant_context(
                getattr(input_data, "tenant_id", None), tenant_ctx.tenant_id
            )
        except TenantContextError as e:
            logger.warning(f"Tenant context error in get_entity: {e}")
            return GetEntityOutput(
                found=False, error=f"Tenant context required: {e}. Authentication required."
            )

        driver = self._get_driver()
        entity_id = input_data.entity_id

        try:
            async with driver.session(database=self.database) as session:

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

        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()

            enforce_tenant_context(
                getattr(input_data, "tenant_id", None), tenant_ctx.tenant_id
            )
        except TenantContextError as e:
            logger.warning(f"Tenant context error in get_relationships: {e}")
            return GetRelationshipsOutput(
                relationships=[],
                total_count=0,
                error=f"Tenant context required: {e}. Authentication required.",
            )

        predicate = input_data.predicate
        if predicate:
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", predicate) is None:
                return GetRelationshipsOutput(
                    relationships=[], total_count=0, error="INVALID_PREDICATE"
                )
            # SEC-L3-CYPHER-003: Validate against explicit allowlist
            validate_cypher_identifier(predicate, ALLOWED_REL_TYPES, "relationship type")

        driver = self._get_driver()

        try:
            async with driver.session(database=self.database) as session:

                tenant_id_str = str(tenant_ctx.tenant_id)

                rel_pattern = f"[r:{predicate}]" if predicate else "[r]"  # cypher-dynamic-safe: validated against ALLOWED_REL_TYPES
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

        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()

            enforce_tenant_context(
                getattr(input_data, "tenant_id", None), tenant_ctx.tenant_id
            )
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

        try:
            tenant_ctx = tenant_context.get_current_tenant_context()
            tenant_ctx.assert_valid()

            enforce_tenant_context(
                getattr(input_data, "tenant_id", None), tenant_ctx.tenant_id
            )
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
