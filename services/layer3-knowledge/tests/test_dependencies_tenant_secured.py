"""Characterization and fail-closed tests for Layer 3 tenant-secured dependencies."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.isolation import QueryScope, ScopedQuery

from src.api.dependencies_tenant_secured import (
    Neo4jTenantSessionSecured,
    create_neo4j_tenant_session,
    get_neo4j_secured,
    get_neo4j_with_optional_tenant,
    get_neo4j_with_tenant,
    get_neo4j_with_validation,
    require_request_tenant_id,
    require_tenant_header_for_internal,
)
from src.security import UnscopedQueryError


@pytest.mark.asyncio
async def test_session_properties_and_lifecycle():
    driver = MagicMock()
    mock_session = AsyncMock()
    driver.session.return_value = mock_session

    session_wrapper = Neo4jTenantSessionSecured(driver, tenant_id="tenant-123")
    assert session_wrapper.tenant_id == "tenant-123"
    assert session_wrapper.is_bypass is False

    async with session_wrapper as s:
        assert s._session is not None
    assert session_wrapper._session is None

    # Test explicit close
    session_wrapper2 = Neo4jTenantSessionSecured(driver, tenant_id="tenant-123", session=mock_session)
    await session_wrapper2.close()
    assert session_wrapper2._session is None
    mock_session.close.assert_awaited()


@pytest.mark.asyncio
async def test_session_run_uninitialized_raises_500():
    driver = MagicMock()
    session_wrapper = Neo4jTenantSessionSecured(driver, tenant_id="tenant-123")
    with pytest.raises(HTTPException) as exc_info:
        await session_wrapper.run("MATCH (n:Entity {tenant_id: $tenant_id}) RETURN n")
    assert exc_info.value.status_code == 500
    assert "Neo4j session not initialized" in exc_info.value.detail


@pytest.mark.asyncio
async def test_session_run_broad_match_rejected_fail_closed():
    driver = MagicMock()
    mock_session = AsyncMock()
    session_wrapper = Neo4jTenantSessionSecured(driver, tenant_id="tenant-123", session=mock_session)

    # Broad match without tenant predicate
    with pytest.raises(UnscopedQueryError):
        await session_wrapper.run("MATCH (n) RETURN n")


@pytest.mark.asyncio
async def test_session_run_scoped_query_fail_closed_without_tenant():
    driver = MagicMock()
    mock_session = AsyncMock()
    session_wrapper = Neo4jTenantSessionSecured(driver, tenant_id="", session=mock_session)

    scoped_query = ScopedQuery(
        cypher="MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) RETURN e",
        params={"id": "entity-1"},
        scope=QueryScope.TENANT,
        tenant_id="",
    )
    with pytest.raises(UnscopedQueryError):
        await session_wrapper.run(scoped_query)


@pytest.mark.asyncio
async def test_get_neo4j_secured_requires_valid_tenant():
    request = MagicMock()

    # Missing context entirely
    with pytest.raises(ValidationError):
        await get_neo4j_secured(request, None)

    # Context with empty tenant
    empty_ctx = RequestContext(tenant_id="")
    with pytest.raises(ValidationError):
        await get_neo4j_secured(request, empty_ctx)


@pytest.mark.asyncio
async def test_get_neo4j_with_optional_tenant_fail_closed():
    request = MagicMock()

    # Missing context
    with pytest.raises(ValidationError):
        await get_neo4j_with_optional_tenant(request, None)

    # Super admin context must use reviewed admin dependency
    super_admin_ctx = RequestContext(tenant_id="", roles=["super_admin"])
    with pytest.raises(AuthorizationError):
        await get_neo4j_with_optional_tenant(request, super_admin_ctx)


@pytest.mark.asyncio
async def test_require_request_tenant_id():
    request = MagicMock()
    request.state.governance_context = None
    with pytest.raises(ValidationError):
        require_request_tenant_id(request)

    request.state.governance_context = MagicMock(tenant_id="tenant-abc")
    assert require_request_tenant_id(request) == "tenant-abc"


@pytest.mark.asyncio
async def test_require_tenant_header_for_internal():
    checker = require_tenant_header_for_internal()
    request = MagicMock()
    request.headers = {}
    request.state.governance_context = None

    # No tenant context in request
    with pytest.raises((AuthenticationError, ValidationError)):
        await checker(request)


@pytest.mark.asyncio
async def test_create_neo4j_tenant_session_requires_tenant_id():
    with pytest.raises(ValueError, match="tenant_id is required"):
        await create_neo4j_tenant_session("")
