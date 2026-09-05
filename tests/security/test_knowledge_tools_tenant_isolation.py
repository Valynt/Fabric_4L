"""P0: Knowledge Tools Tenant Isolation Tests

Validates that knowledge graph query tools enforce tenant boundaries.
These tests address the gap where QueryGraphTool executes Cypher queries
without validating tenant context, potentially allowing cross-tenant data access.

Ship/No-Ship Gate: FAIL on this file blocks release.
"""
from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

os.environ["LAYER1_API_URL"] = "https://layer1"
os.environ["LAYER2_API_URL"] = "https://layer2"
os.environ["LAYER3_API_URL"] = "https://layer3"
os.environ["LAYER4_LAYER5_API_URL"] = "https://layer5"
os.environ["ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT"] = "true"

import pytest


# Lazy import fixtures to avoid import errors at collection time
def _get_knowledge_tools():
    """Import knowledge tools via canonical package imports."""
    from layer4_agents.models.tool_schemas import QueryGraphInput, SemanticSearchInput
    from layer4_agents.tools.knowledge_tools import QueryGraphTool, SemanticSearchTool
    
    return QueryGraphTool, SemanticSearchTool, QueryGraphInput, SemanticSearchInput

# Constants matching conftest.py
TENANT_A_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def mock_tenant_context(monkeypatch):
    """Mock tenant context for testing without real shared.identity."""
    from unittest.mock import MagicMock, patch
    
    # Create a mock TenantContext
    mock_ctx = MagicMock()
    mock_ctx.tenant_id = TENANT_A_ID
    mock_ctx.user_id = "user-123"
    mock_ctx.roles = ["analyst"]
    mock_ctx.source = "jwt"
    mock_ctx.assert_valid = MagicMock()
    
    # Patch get_current_tenant_context to return our mock
    with patch("layer4_agents.shared.domain.context.get_current_tenant_context") as mock_get_ctx:
        mock_get_ctx.return_value = mock_ctx
        yield mock_ctx


class TestQueryGraphToolTenantEnforcement:
    """P0: Verify query_graph tool enforces tenant isolation."""

    @pytest.fixture
    def mock_neo4j_session(self):
        """Create a mock Neo4j session that captures executed queries."""
        session = AsyncMock()
        
        # Mock result that returns records with tenant_id
        result = AsyncMock()
        result.data = AsyncMock(return_value=[
            {"id": "node-1", "tenant_id": str(TENANT_A_ID), "name": "Entity A"},
            {"id": "node-2", "tenant_id": str(TENANT_A_ID), "name": "Entity B"},
        ])
        result.keys = MagicMock(return_value=["id", "tenant_id", "name"])
        
        session.run = AsyncMock(return_value=result)
        
        # Make session an async context manager
        session.__aenter__.return_value = session
        session.__aexit__.return_value = False
        
        return session

    @pytest.mark.asyncio
    async def test_query_graph_injects_tenant_filter(self, mock_neo4j_session, mock_tenant_context):
        """POSITIVE: Tool injects tenant filter into Cypher query when context available.
        
        When TenantContext is set, the query_graph tool should:
        1. Extract tenant_id from context
        2. Modify query to add tenant filter
        3. Execute modified query
        """
        QueryGraphTool, _, QueryGraphInput, _ = _get_knowledge_tools()
        
        tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
        
        # Patch the driver to return our mock session
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_neo4j_session)
        tool._driver = mock_driver
        
        input_data = QueryGraphInput(
            cypher_query="MATCH (n:Account) RETURN n LIMIT 10",
            parameters={}
        )
        
        result = await tool.execute(input_data)
        
        # Verify the session.run was called
        mock_neo4j_session.run.assert_called_once()
        call_args = mock_neo4j_session.run.call_args
        executed_query = call_args[0][0]  # First positional arg is the query
        
        # Verify tenant filtering was injected
        assert str(TENANT_A_ID) in executed_query or "tenant_id" in executed_query or "$tenant_id" in executed_query, (
            f"Query must include tenant filter. Executed query: {executed_query}"
        )

    @pytest.mark.asyncio
    async def test_query_graph_without_tenant_context_fails_closed(self, mock_neo4j_session):
        """NEGATIVE: Tool fails closed when no tenant context is available.
        
        Without RequestContext, the tool must either:
        1. Reject the query entirely
        2. Require explicit tenant_id in input
        3. Return error response
        
        This is a P0 negative test - it proves the tool doesn't execute
        unscoped queries that could return cross-tenant data.
        """
        QueryGraphTool, _, QueryGraphInput, _ = _get_knowledge_tools()
        
        tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
        
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_neo4j_session)
        tool._driver = mock_driver
        
        input_data = QueryGraphInput(
            cypher_query="MATCH (n:Account) RETURN n LIMIT 10",
            parameters={}
        )
        
        result = await tool.execute(input_data)
        
        # Tool should fail closed with error when no tenant context
        assert result.error is not None, (
            "Tool must fail closed without tenant context. "
            f"Got {result.row_count} rows with no error."
        )
        assert "tenant" in result.error.lower() or "authentication" in result.error.lower(), (
            f"Error should indicate tenant/auth issue: {result.error}"
        )

    @pytest.mark.asyncio
    async def test_cross_tenant_query_blocked(self, mock_neo4j_session, mock_tenant_context):
        """NEGATIVE: Tenant A cannot query Tenant B data via tenant_id spoofing.
        
        Attempting to override tenant_id in query parameters should be blocked.
        The tool must use the authenticated context tenant_id, not the input.
        """
        QueryGraphTool, _, QueryGraphInput, _ = _get_knowledge_tools()
        
        tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
        
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_neo4j_session)
        tool._driver = mock_driver
        
        # Try to spoof tenant_b in parameters
        input_data = QueryGraphInput(
            cypher_query="MATCH (n:Account {tenant_id: $tenant_id}) RETURN n",
            parameters={"tenant_id": str(TENANT_B_ID)}  # Attempted spoof
        )
        
        result = await tool.execute(input_data)
        
        # Verify the actual tenant_id in the executed query
        call_args = mock_neo4j_session.run.call_args
        actual_params = call_args.kwargs.get("parameters") or call_args.args[1]

        # The tool should override spoofed tenant_id with context tenant_id
        assert actual_params.get("tenant_id") == str(TENANT_A_ID), (
            "Tool must reject tenant_id spoofing in query parameters. "
            "Input attempted Tenant B but Tenant A context should override."
        )

    @pytest.mark.asyncio
    async def test_query_graph_rejects_input_tenant_without_context(self, mock_neo4j_session):
        """NEGATIVE: Raw input tenant_id is not an approved execution context."""
        QueryGraphTool, _, QueryGraphInput, _ = _get_knowledge_tools()

        tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_neo4j_session)
        tool._driver = mock_driver

        result = await tool.execute(
            QueryGraphInput(
                cypher_query="MATCH (n:Account) RETURN n LIMIT 10",
                parameters={},
                tenant_id=str(TENANT_A_ID),
            )
        )

        assert result.error is not None
        assert "tenant context required" in result.error.lower()
        mock_neo4j_session.run.assert_not_called()

    def test_tenant_filter_rejects_path_variable_assignment(self):
        """V1-TENANCY-012 F6: named paths are rejected fail-closed.

        Supersedes the previous path-alias acceptance test: a bound path
        variable lets nodes(p)/relationships(p) project edges and
        intermediate nodes that carry no injected tenant predicate, so
        path-variable assignment is now a structured rejection.
        """
        QueryGraphTool, _, _, _ = _get_knowledge_tools()
        tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})

        with pytest.raises(ValueError, match="path-variable assignment"):
            tool._inject_tenant_filter(
                "MATCH path = (start:Account)-[:OWNS]->(child:UseCase) RETURN path",
                TENANT_A_ID,
            )

    def test_tenant_filter_rejects_query_without_node_alias(self):
        QueryGraphTool, _, _, _ = _get_knowledge_tools()
        tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})

        with pytest.raises(ValueError, match="unable to parse node alias"):
            tool._inject_tenant_filter("RETURN 1 AS ok", TENANT_A_ID)


class TestSemanticSearchToolTenantIsolation:
    """P1: Verify semantic_search tool enforces tenant boundaries."""

    @pytest.fixture
    def mock_pinecone_index(self):
        """Create mock Pinecone index that captures query filters."""
        index = MagicMock()
        index.query = MagicMock(return_value={
            "matches": [
                {"id": "vec-1", "score": 0.95, "metadata": {"tenant_id": str(TENANT_A_ID)}},
            ]
        })
        return index

    @pytest.mark.asyncio
    async def test_semantic_search_applies_tenant_filter(self, mock_pinecone_index, monkeypatch):
        """POSITIVE: Semantic search includes tenant_id in metadata filter."""
        from layer4_agents.models.tool_schemas import SemanticSearchInput
        from layer4_agents.tools.knowledge_tools import SemanticSearchTool
        from value_fabric.shared.identity.context import RequestContext, set_request_context
        from value_fabric.shared.identity.permissions import Permission
        
        # Set tenant context
        ctx = RequestContext(
            tenant_id=TENANT_A_ID,
            user_id="user-123",
            roles=["analyst"],
            api_key_id=None,
            permissions=frozenset({Permission.READ_GRAPHRAG}),
            source="jwt",
            raw={},
        )
        token = set_request_context(ctx)
        
        try:
            tool = SemanticSearchTool(config={"pinecone_api_key": "test-key"})
            tool._pinecone_client = True  # Prevent lazy init
            tool._index = mock_pinecone_index
            
            # Mock the embeddings method to avoid OpenAI dependency
            with patch.object(tool, '_get_embedding', new_callable=AsyncMock) as mock_embeddings:
                mock_embeddings.return_value = [0.1] * 1536
                
                input_data = SemanticSearchInput(
                    query="sales forecasting methodology",
                    top_k=5
                )
                
                result = await tool.execute(input_data)
            
            # Verify query was called with tenant filter
            mock_pinecone_index.query.assert_called_once()
            call_kwargs = mock_pinecone_index.query.call_args.kwargs
            
            filter_metadata = call_kwargs.get("filter", {})
            assert "tenant_id" in filter_metadata, (
                "Semantic search must include tenant_id in metadata filter"
            )
            assert filter_metadata["tenant_id"] == str(TENANT_A_ID), (
                f"Filter must use context tenant_id, got {filter_metadata.get('tenant_id')}"
            )
        finally:
            from value_fabric.shared.identity.context import _current_context
            _current_context.reset(token)


class TestKnowledgeToolsRateLimiting:
    """P1: Knowledge tools respect rate limiting."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Rate limiting is not implemented at the tool layer, but at the API layer.")
    async def test_query_graph_respects_rate_limit(self, monkeypatch):
        """NEGATIVE: Tool fails gracefully when rate limit exceeded."""
        from layer4_agents.models.tool_schemas import QueryGraphInput
        from layer4_agents.tools.knowledge_tools import QueryGraphTool
        
        # Mock rate limiter that always blocks
        mock_limiter = MagicMock()
        mock_limiter.check = AsyncMock(return_value=MagicMock(
            allowed=False,
            retry_after=60
        ))
        
        monkeypatch.setattr(
            "shared.identity.rate_limiter.RedisRateLimiter",
            lambda **kwargs: mock_limiter
        )
        
        tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
        
        input_data = QueryGraphInput(
            cypher_query="MATCH (n) RETURN n LIMIT 1",
            parameters={}
        )
        
        result = await tool.execute(input_data)
        
        # Should return error indicating rate limit
        assert result.error is not None, "Rate limited request must return error"
        assert "rate" in result.error.lower() or "limit" in result.error.lower(), (
            f"Error should indicate rate limiting: {result.error}"
        )


class TestKnowledgeToolsInputValidation:
    """P0: Knowledge tools validate input to prevent injection attacks."""

    @pytest.mark.asyncio
    async def test_query_graph_blocks_write_operations(self):
        """NEGATIVE: Cypher write operations are blocked (read-only enforcement)."""
        from layer4_agents.models.tool_schemas import QueryGraphInput
        from layer4_agents.tools.knowledge_tools import QueryGraphTool
        
        tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
        
        malicious_queries = [
            "MATCH (n) DELETE n",  # DELETE
            "MATCH (n) SET n.prop = 'value'",  # SET
            "CREATE (n:Node {id: 1})",  # CREATE
            "MATCH (n) MERGE (m:Node)",  # MERGE
            "MATCH (n) REMOVE n.prop",  # REMOVE
            "DROP INDEX test",  # DROP
        ]
        
        for query in malicious_queries:
            input_data = QueryGraphInput(cypher_query=query, parameters={})
            result = await tool.execute(input_data)
            
            assert result.error is not None, (
                f"Write operation must be blocked: {query}"
            )
            assert result.row_count == 0, (
                f"Write operation must return 0 rows: {query}"
            )

    @pytest.mark.asyncio
    async def test_query_graph_allows_read_operations(self):
        """POSITIVE: Read-only Cypher queries are permitted."""
        from layer4_agents.models.tool_schemas import QueryGraphInput
        from layer4_agents.tools.knowledge_tools import QueryGraphTool
        
        tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
        
        read_queries = [
            "MATCH (n:Account) RETURN n LIMIT 10",
            "MATCH (n)-[r]->(m) RETURN n, r, m",
            "MATCH (n) WHERE n.name = 'test' RETURN n",
            "MATCH (n) RETURN n ORDER BY n.created_at DESC",
            "MATCH (n) RETURN count(n) as total",
        ]
        
        # Mock the driver to avoid actual DB calls
        with patch.object(tool, '_get_driver') as mock_get_driver:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.data = AsyncMock(return_value=[])
            mock_session.run = AsyncMock(return_value=mock_result)
            
            mock_driver = MagicMock()
            mock_driver.session = MagicMock(return_value=mock_session)
            mock_get_driver.return_value = mock_driver
            
            for query in read_queries:
                input_data = QueryGraphInput(cypher_query=query, parameters={})
                result = await tool.execute(input_data)
                
                assert result.error is None or "write" not in result.error.lower(), (
                    f"Read query should be allowed: {query}. Error: {result.error}"
                )


class TestKnowledgeToolsAuditLogging:
    """P1: Knowledge tools generate audit logs for security events."""

    @pytest.mark.asyncio
    async def test_query_graph_logs_executed_queries(self, caplog, mock_tenant_context):
        """POSITIVE: Executed queries are logged for audit trail."""
        import logging

        from layer4_agents.models.tool_schemas import QueryGraphInput
        from layer4_agents.tools.knowledge_tools import QueryGraphTool
        
        # Set log level to capture query logs
        with caplog.at_level(logging.INFO):
            tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
            
            with patch.object(tool, '_get_driver') as mock_get_driver:
                mock_session = AsyncMock()
                mock_result = AsyncMock()
                mock_result.data = AsyncMock(return_value=[])
                mock_session.run = AsyncMock(return_value=mock_result)
                
                mock_driver = MagicMock()
                mock_driver.session = MagicMock(return_value=mock_session)
                mock_get_driver.return_value = mock_driver
                
                input_data = QueryGraphInput(
                    cypher_query="MATCH (n:Account) RETURN n",
                    parameters={}
                )
                
                await tool.execute(input_data)
                
                # Verify query was logged
                log_messages = " ".join([rec.message for rec in caplog.records])
                assert "MATCH" in log_messages or "cypher" in log_messages.lower(), (
                    "Query execution should be logged for audit trail"
                )
