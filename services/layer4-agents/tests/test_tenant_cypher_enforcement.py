import pytest

from layer4_agents.services.tenant_cypher import (
    TenantCypherValidationError,
    fetch_tenant_validated_records,
)


async def test_query_missing_tenant_predicate_is_rejected():
    with pytest.raises(TenantCypherValidationError, match="tenant"):
        await fetch_tenant_validated_records(
            driver=None,
            query="MATCH (n:ValueHypothesis) RETURN n",
            params={},
            tenant_id="tenant-123",
            operation="test",
        )


async def test_query_with_tenant_predicate_is_accepted():
    # Driver is None so execution will fail, but validation should pass.
    with pytest.raises(AttributeError):
        await fetch_tenant_validated_records(
            driver=None,
            query="MATCH (n:ValueHypothesis {tenant_id: $tenant_id}) RETURN n",
            params={},
            tenant_id="tenant-123",
            operation="test",
        )


from layer4_agents.tools.knowledge_tools import GetRelationshipsTool
from layer4_agents.models.tool_schemas import GetRelationshipsInput
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_tenant_context():
    ctx = MagicMock()
    ctx.tenant_id = "tenant-123"
    ctx.user_id = "user-123"
    ctx.assert_valid = MagicMock()
    return ctx


async def empty_async_gen():
    for item in []:
        yield item


@pytest.mark.asyncio
@patch("layer4_agents.tools.knowledge_tools.tenant_context.get_current_tenant_context")
async def test_get_relationships_without_predicate_builds_query(mock_get_ctx, mock_tenant_context):
    """
    No predicate should return all relationship types,
    not crash because query is undefined.
    """
    mock_get_ctx.return_value = mock_tenant_context
    tool = GetRelationshipsTool({})

    mock_session = AsyncMock()
    mock_session.run = AsyncMock()
    mock_session.run.return_value.__aiter__.side_effect = lambda: empty_async_gen()

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    tool._driver = mock_driver

    await tool.execute(GetRelationshipsInput(entity_id="entity-1"))

    # Verify query was built and executed
    mock_session.run.assert_called_once()
    query_executed = mock_session.run.call_args[0][0]

    assert "[r]" in query_executed
    assert "tenant_id: $tenant_id" in query_executed


@pytest.mark.asyncio
@patch("layer4_agents.tools.knowledge_tools.tenant_context.get_current_tenant_context")
async def test_get_relationships_with_predicate_filters_relationship_type(
    mock_get_ctx, mock_tenant_context
):
    """
    Predicate should constrain relationship type.
    """
    mock_get_ctx.return_value = mock_tenant_context
    tool = GetRelationshipsTool({})

    mock_session = AsyncMock()
    mock_session.run = AsyncMock()
    mock_session.run.return_value.__aiter__.side_effect = lambda: empty_async_gen()

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    tool._driver = mock_driver

    await tool.execute(GetRelationshipsInput(entity_id="entity-1", predicate="ENABLES"))

    # Verify query was built and executed
    mock_session.run.assert_called_once()
    query_executed = mock_session.run.call_args[0][0]

    assert "[r:ENABLES]" in query_executed


@pytest.mark.asyncio
@patch("layer4_agents.tools.knowledge_tools.tenant_context.get_current_tenant_context")
async def test_get_relationships_always_applies_tenant_filter(mock_get_ctx, mock_tenant_context):
    """
    Tenant filter must exist regardless of predicate.
    """
    mock_get_ctx.return_value = mock_tenant_context
    tool = GetRelationshipsTool({})

    mock_session = AsyncMock()
    mock_session.run = AsyncMock()
    mock_session.run.return_value.__aiter__.side_effect = lambda: empty_async_gen()

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    tool._driver = mock_driver

    await tool.execute(GetRelationshipsInput(entity_id="entity-1"))

    # Verify query was built and executed
    mock_session.run.assert_called_once()
    query_executed = mock_session.run.call_args[0][0]

    # Check that tenant filter is on both n and m nodes
    assert "MATCH (n {id: $entity_id, tenant_id: $tenant_id})" in query_executed
    assert "(m {tenant_id: $tenant_id})" in query_executed
