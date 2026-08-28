from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from layer4_agents.models.tool_schemas import (
    FindPathsInput,
    GetEntityInput,
    GetRelationshipsInput,
    QueryGraphInput,
    SemanticSearchInput,
    TraverseTreeInput,
)
from layer4_agents.tools.knowledge_tools import (
    FindPathsTool,
    GetEntityTool,
    GetRelationshipsTool,
    QueryGraphTool,
    SemanticSearchTool,
    TraverseTreeTool,
)
from layer4_agents.tools.registry import TenantSpoofingError
from value_fabric.shared.identity.context import (
    RequestContext,
    RequestContextManager,
)

TENANT_A_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

NEO4J_CONFIG = {"neo4j_uri": "bolt://localhost:7687", "neo4j_password": "password"}


@pytest.fixture
def mock_neo4j_session():
    session = AsyncMock()
    result = AsyncMock()
    result.data = AsyncMock(return_value=[{"id": "node-1", "tenant_id": str(TENANT_A_ID)}])
    session.run = AsyncMock(return_value=result)
    session.__aenter__.return_value = session
    session.__aexit__.return_value = False
    return session


@pytest.fixture
def mock_tenant_context():
    ctx = MagicMock()
    ctx.tenant_id = TENANT_A_ID
    ctx.user_id = "user-123"
    ctx.roles = ["analyst"]
    ctx.source = "jwt"
    ctx.assert_valid = MagicMock()
    with patch("layer4_agents.shared.domain.context.get_current_tenant_context", return_value=ctx):
        yield ctx


@pytest.mark.asyncio
async def test_query_graph_rejects_spoofed_tenant_parameter(
    mock_neo4j_session,
    mock_tenant_context,
):
    tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_neo4j_session)
    tool._driver = mock_driver

    with pytest.raises(
        ValueError,
        match=(
            "Tenant spoofing detected: parameter tenant_id "
            "does not match authenticated context"
        ),
    ):
        await tool.execute(
            QueryGraphInput(
                cypher_query="MATCH (n:Account {tenant_id: $tenant_id}) RETURN n",
                parameters={"tenant_id": str(TENANT_B_ID)},
            )
        )

@pytest.mark.asyncio
async def test_query_graph_rejects_input_tenant_without_context(mock_neo4j_session):
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
    assert "invalid tenant context" in result.error.lower()
    mock_neo4j_session.run.assert_not_called()


@pytest.mark.asyncio
async def test_query_graph_rejects_tenant_context_input_mismatch(
    mock_neo4j_session,
    mock_tenant_context,
):
    tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_neo4j_session)
    tool._driver = mock_driver

    with pytest.raises(
        ValueError,
        match="Tenant spoofing detected: payload tenant_id does not match authenticated context",
    ):
        await tool.execute(
            QueryGraphInput(
                cypher_query="MATCH (n:Account) RETURN n LIMIT 10",
                parameters={},
                tenant_id=str(TENANT_B_ID),
            )
        )

    mock_neo4j_session.run.assert_not_called()


def test_tenant_filter_detects_path_alias_node_alias():
    tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})

    scoped_query, alias = tool._inject_tenant_filter(
        "MATCH path = (start:Account)-[:OWNS]->(child:UseCase) RETURN path",
        TENANT_A_ID,
    )

    assert alias == "start"
    assert "WHERE start.tenant_id = $tenant_id" in scoped_query


def test_tenant_filter_rejects_query_without_node_alias():
    tool = QueryGraphTool(config={"neo4j_uri": "bolt://localhost:7687"})

    with pytest.raises(ValueError, match="unable to parse node alias"):
        tool._inject_tenant_filter("RETURN 1 AS ok", TENANT_A_ID)


@pytest.mark.parametrize(
    ("tool_cls", "input_data"),
    [
        (
            SemanticSearchTool,
            SemanticSearchInput(query="who are we", tenant_id=str(TENANT_B_ID)),
        ),
        (GetEntityTool, GetEntityInput(entity_id="a", tenant_id=str(TENANT_B_ID))),
        (
            GetRelationshipsTool,
            GetRelationshipsInput(entity_id="a", tenant_id=str(TENANT_B_ID)),
        ),
        (
            TraverseTreeTool,
            TraverseTreeInput(
                start_entity_id="a",
                path_pattern="()-->()",
                tenant_id=str(TENANT_B_ID),
            ),
        ),
        (
            FindPathsTool,
            FindPathsInput(source_id="a", target_id="b", tenant_id=str(TENANT_B_ID)),
        ),
    ],
)
@pytest.mark.asyncio
async def test_other_knowledge_tools_reject_payload_tenant_spoofing(
    tool_cls,
    input_data,
    mock_tenant_context,
):
    tool = tool_cls(NEO4J_CONFIG)

    with pytest.raises(TenantSpoofingError, match="Tenant spoofing detected"):
        await tool.execute(input_data)


@pytest.mark.asyncio
async def test_base_tool_run_maps_tenant_spoofing_to_structured_result(
    mock_tenant_context,
):
    """BaseTool.run must classify tenant spoofing, not return a generic execution error."""
    tool = QueryGraphTool(NEO4J_CONFIG)
    # RequestContext.tenant_id can be a UUID; metadata tenant_id must still be a str.
    request_ctx = RequestContext(
        tenant_id=TENANT_A_ID, user_id="user-1", roles=["analyst"]
    )

    with RequestContextManager(request_ctx):
        result = await tool.run(
            {
                "cypher_query": "MATCH (n:Account) RETURN n LIMIT 10",
                "parameters": {},
                "tenant_id": str(TENANT_B_ID),
            }
        )

    assert result.status == "error"
    assert result.error is not None
    assert result.error["code"] == "TENANT_SPOOFING_DETECTED"
    assert "Tenant spoofing detected" in result.error["message"]
    # trusted_tenant_id is a UUID on request context; metadata tenant_id must be a
    # plain string to satisfy the ToolMetadata contract and avoid serialization drift.
    assert isinstance(result.metadata.get("tenant_id"), str)
    assert result.metadata["tenant_id"] == str(TENANT_A_ID)
