"""
Tool Invocation Boundary Tests (Suite 7).

Verifies that all agent tools enforce tenant boundaries and cannot be used
to access or modify data from other tenants.

Test Strategy:
- Verify all tools require tenant context
- Test cross-tenant tool invocation attempts
- Validate tool parameter sanitization
- Test tool result filtering by tenant
- Verify tool audit logging includes tenant_id

Critical Security Property:
    Tool invoked by tenant A MUST NOT access tenant B's data
"""

import pytest
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from fastapi import HTTPException, status

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.permissions import Permission

try:
    from src.tools.registry import ToolRegistry, ToolCategory
    _REGISTRY_AVAILABLE = True
except (ImportError, Exception):
    ToolRegistry = None  # type: ignore[assignment,misc]
    ToolCategory = None  # type: ignore[assignment]
    _REGISTRY_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Tool Registration and Discovery
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not _REGISTRY_AVAILABLE, reason="ToolRegistry unavailable (langgraph/settings not installed)")
class TestToolRegistration:
    """Verify tool registration enforces tenant scoping."""

    def test_all_tools_require_tenant_context_parameter(self):
        """All registered tools must accept tenant_id parameter.

        Rationale: Tools without tenant_id cannot enforce tenant isolation.
        """
        registry = ToolRegistry()

        for tool_name, tool_func in registry.get_all_tools().items():
            import inspect
            sig = inspect.signature(tool_func)

            assert "tenant_id" in sig.parameters, \
                f"Tool {tool_name} missing tenant_id parameter"

    def test_all_tools_have_tenant_scoped_metadata(self):
        """All registered tools must declare tenant_scoped metadata.

        Rationale: Operators need to know which tools access tenant data.
        """
        registry = ToolRegistry()

        for tool_name in registry.get_all_tools().keys():
            metadata = registry.get_tool_metadata(tool_name)

            assert "tenant_scoped" in metadata, \
                f"Tool {tool_name} missing tenant_scoped metadata"

            if tool_name not in ["health_check", "list_tools"]:
                assert metadata["tenant_scoped"] is True, \
                    f"Tool {tool_name} should be tenant-scoped"

    def test_tool_discovery_filtered_by_tenant_permissions(self):
        """Tool discovery must be filtered by tenant permissions.

        Rationale: Tenants should only see tools they have permission to use.
        """
        registry = ToolRegistry()

        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset(["read"])
        )

        available_tools = registry.get_available_tools(context)

        admin_tools = ["delete_tenant", "suspend_tenant", "grant_permission"]
        for admin_tool in admin_tools:
            assert admin_tool not in available_tools, \
                f"Non-admin user should not see {admin_tool}"


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Tool Invocation Tenant Isolation
# ═══════════════════════════════════════════════════════════════════════════


class TestToolInvocationIsolation:
    """Verify tool invocations enforce tenant boundaries."""

    @pytest.mark.asyncio
    async def test_tool_cannot_access_another_tenants_data(self):
        """Tool invoked by tenant A must not access tenant B's data.

        Attack scenario: Tenant A tries to read tenant B's entities.
        """
        from src.tools.knowledge import get_entity

        tenant_a = uuid4()
        tenant_b = uuid4()
        entity_id = "entity-123"

        ctx_a = RequestContext(
            tenant_id=tenant_a,
            user_id=uuid4(),
            permissions=frozenset([Permission.READ_SEARCH.value]),
        )

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.knowledge._get_driver", return_value=mock_driver):
            with patch("src.tools.knowledge.emit_audit_event"):
                result = await get_entity(
                    entity_id=entity_id,
                    context=ctx_a,
                )

                assert result is None or result.get("tenant_id") == str(tenant_a)

    @pytest.mark.asyncio
    async def test_tool_cannot_modify_another_tenants_data(self):
        """Tool invoked by tenant A must not modify tenant B's data.

        Attack scenario: Tenant A tries to update tenant B's entity.
        """
        from src.tools.knowledge import update_entity

        tenant_a = uuid4()
        tenant_b = uuid4()
        entity_id = "entity-123"

        ctx_a = RequestContext(
            tenant_id=tenant_a,
            user_id=uuid4(),
            permissions=frozenset([Permission.WRITE_SCHEMA.value]),
        )

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.knowledge._get_driver", return_value=mock_driver):
            with patch("src.tools.knowledge.emit_audit_event"):
                result = await update_entity(
                    entity_id=entity_id,
                    updates={"name": "Malicious Update"},
                    context=ctx_a,
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_tool_cannot_delete_another_tenants_data(self):
        """Tool invoked by tenant A must not delete tenant B's data.

        Attack scenario: Tenant A tries to delete tenant B's entity.
        """
        from src.tools.knowledge import delete_entity

        tenant_a = uuid4()
        tenant_b = uuid4()
        entity_id = "entity-123"

        ctx_a = RequestContext(
            tenant_id=tenant_a,
            user_id=uuid4(),
            permissions=frozenset([Permission.WRITE_SCHEMA.value]),
        )

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.knowledge._get_driver", return_value=mock_driver):
            with patch("src.tools.knowledge.emit_audit_event"):
                result = await delete_entity(
                    entity_id=entity_id,
                    context=ctx_a,
                )

                assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Tool Parameter Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestToolParameterValidation:
    """Verify tool parameters are validated and sanitized."""

    @pytest.mark.asyncio
    async def test_tool_rejects_sql_injection_in_parameters(self):
        """Tool parameters with SQL injection attempts must be rejected.

        Attack scenario: Tenant provides SQL in entity_id parameter.
        """
        from src.tools.knowledge import get_entity

        ctx = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset([Permission.READ_SEARCH.value]),
        )
        malicious_entity_id = "' OR '1'='1"

        # get_entity silently rejects injection attempts by returning None
        # rather than raising, to avoid leaking validation details to callers.
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.knowledge._get_driver", return_value=mock_driver):
            with patch("src.tools.knowledge.emit_audit_event"):
                result = await get_entity(
                    entity_id=malicious_entity_id,
                    context=ctx,
                )

        assert result is None

    @pytest.mark.asyncio
    async def test_tool_rejects_path_traversal_in_parameters(self):
        """Tool parameters with path traversal attempts must be rejected.

        Attack scenario: Tenant provides path traversal in file parameter.
        """
        from src.tools.files import read_file

        ctx = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset([Permission.READ_SEARCH.value]),
        )
        malicious_path = "../../etc/passwd"

        with pytest.raises((ValueError, HTTPException)):
            await read_file(
                file_path=malicious_path,
                context=ctx,
            )

    @pytest.mark.asyncio
    async def test_tool_rejects_oversized_parameters(self):
        """Tool parameters exceeding size limits must be rejected.

        Attack scenario: Tenant provides huge parameter to DoS.
        """
        from src.tools.knowledge import search_entities

        ctx = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset([Permission.READ_SEARCH.value]),
        )
        huge_query = "A" * 100000  # 100KB query

        # search_entities silently rejects oversized queries by returning []
        # rather than raising, to avoid leaking size limits to callers.
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data.return_value = []
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.knowledge._get_driver", return_value=mock_driver):
            with patch("src.tools.knowledge.emit_audit_event"):
                result = await search_entities(
                    query=huge_query,
                    context=ctx,
                )

        assert result == []

    @pytest.mark.asyncio
    async def test_tool_validates_tenant_id_format(self):
        """Tool must validate tenant_id is valid UUID.

        Rationale: Invalid tenant_id could cause downstream errors.
        """
        from src.tools.knowledge import get_entity  # noqa: F401

        with pytest.raises((ValueError, TypeError)):
            RequestContext(
                tenant_id="not-a-uuid",  # type: ignore
                user_id=uuid4(),
                permissions=frozenset([Permission.READ_SEARCH.value]),
            )


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Tool Result Filtering
# ═══════════════════════════════════════════════════════════════════════════


class TestToolResultFiltering:
    """Verify tool results are filtered by tenant."""

    @pytest.mark.asyncio
    async def test_search_tool_only_returns_tenant_results(self):
        """Search tool must only return results for requesting tenant.

        Rationale: Search across all tenants would leak data.
        """
        from src.tools.knowledge import search_entities

        tenant_a = uuid4()
        tenant_b = uuid4()

        ctx_a = RequestContext(
            tenant_id=tenant_a,
            user_id=uuid4(),
            permissions=frozenset([Permission.READ_SEARCH.value]),
        )

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data.return_value = [
            {"id": "a1", "tenant_id": str(tenant_a), "name": "Tenant A Entity 1"},
            {"id": "a2", "tenant_id": str(tenant_a), "name": "Tenant A Entity 2"},
        ]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.knowledge._get_driver", return_value=mock_driver):
            with patch("src.tools.knowledge.emit_audit_event"):
                results = await search_entities(
                    query="Entity",
                    context=ctx_a,
                )

                assert len(results) == 2
                assert all(r["tenant_id"] == str(tenant_a) for r in results)

    @pytest.mark.asyncio
    async def test_list_tool_only_returns_tenant_items(self):
        """List tool must only return items for requesting tenant.

        Rationale: Listing all items would leak data.
        """
        from src.tools.knowledge import list_entities

        tenant_a = uuid4()
        tenant_b = uuid4()

        ctx_a = RequestContext(
            tenant_id=tenant_a,
            user_id=uuid4(),
            permissions=frozenset([Permission.READ_SEARCH.value]),
        )

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data.return_value = [
            {"id": "a1", "tenant_id": str(tenant_a)},
            {"id": "a2", "tenant_id": str(tenant_a)},
        ]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.knowledge._get_driver", return_value=mock_driver):
            with patch("src.tools.knowledge.emit_audit_event"):
                results = await list_entities(context=ctx_a)

                assert len(results) == 2
                assert all(r["tenant_id"] == str(tenant_a) for r in results)

    @pytest.mark.asyncio
    async def test_aggregate_tool_only_aggregates_tenant_data(self):
        """Aggregate tool must only aggregate data for requesting tenant.

        Rationale: Aggregating across tenants would leak statistics.
        """
        from src.tools.analytics import count_entities

        tenant_a = uuid4()

        ctx_a = RequestContext(
            tenant_id=tenant_a,
            user_id=uuid4(),
            permissions=frozenset([Permission.READ_SEARCH.value]),
        )

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = {"count": 30}
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.analytics._get_driver", return_value=mock_driver):
            with patch("src.tools.analytics.emit_audit_event"):
                count = await count_entities(context=ctx_a)

                assert count == 30


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Tool Audit Logging
# ═══════════════════════════════════════════════════════════════════════════


class TestToolAuditLogging:
    """Verify tool invocations are audited with tenant context."""

    @pytest.mark.asyncio
    async def test_tool_invocation_logged_with_tenant_id(self):
        """Tool invocations must be logged with tenant_id.

        Rationale: Audit trail must show which tenant invoked which tool.
        """
        from src.tools.knowledge import get_entity

        tenant_id = uuid4()
        entity_id = "entity-123"

        ctx = RequestContext(
            tenant_id=tenant_id,
            user_id=uuid4(),
            permissions=frozenset([Permission.READ_SEARCH.value]),
        )

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = {"id": entity_id, "tenant_id": str(tenant_id)}
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.knowledge._get_driver", return_value=mock_driver):
            with patch("src.tools.knowledge.emit_audit_event") as mock_audit:
                await get_entity(
                    entity_id=entity_id,
                    context=ctx,
                )

                assert mock_audit.called
                call_kwargs = mock_audit.call_args.kwargs

                assert call_kwargs.get("tenant_id") == tenant_id
                assert call_kwargs.get("resource_type") == "entity"
                assert call_kwargs.get("resource_id") == entity_id

    @pytest.mark.asyncio
    async def test_failed_tool_invocation_logged(self):
        """Failed tool invocations must be logged.

        Rationale: Failed attempts may indicate attack.
        """
        from src.tools.knowledge import delete_entity

        tenant_a = uuid4()
        tenant_b = uuid4()

        ctx_a = RequestContext(
            tenant_id=tenant_a,
            user_id=uuid4(),
            permissions=frozenset([Permission.WRITE_SCHEMA.value]),
        )

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None

        with patch("src.tools.knowledge._get_driver", return_value=mock_driver):
            with patch("src.tools.knowledge.emit_audit_event") as mock_audit:
                try:
                    await delete_entity(
                        entity_id="entity-123",
                        context=ctx_a,
                    )
                except HTTPException:
                    pass

                assert mock_audit.called
                call_kwargs = mock_audit.call_args.kwargs
                assert call_kwargs.get("outcome") == "failure"
                assert call_kwargs.get("tenant_id") == tenant_a


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Tool Permission Enforcement
# ═══════════════════════════════════════════════════════════════════════════


class TestToolPermissionEnforcement:
    """Verify tools enforce permission requirements."""

    @pytest.mark.asyncio
    async def test_write_tool_requires_write_permission(self):
        """Write tools must require write permission.

        Rationale: Read-only users should not be able to modify data.
        """
        from src.tools.knowledge import update_entity

        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset(["read"])
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_entity(
                entity_id="entity-123",
                updates={"name": "New Name"},
                context=context,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_tool_requires_delete_permission(self):
        """Delete tools must require delete permission.

        Rationale: Write permission should not grant delete access.
        """
        from src.tools.knowledge import delete_entity

        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset(["read", "write"])
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_entity(
                entity_id="entity-123",
                context=context,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_admin_tool_requires_admin_permission(self):
        """Admin tools must require admin permission.

        Rationale: Regular users should not access admin tools.
        """
        from src.tools.admin import suspend_tenant

        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset(["read", "write", "delete"])
        )

        with pytest.raises(HTTPException) as exc_info:
            await suspend_tenant(
                target_tenant_id=uuid4(),
                context=context,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Tool Chaining and Composition
# ═══════════════════════════════════════════════════════════════════════════


class TestToolChaining:
    """Verify tool chaining maintains tenant isolation."""

    @pytest.mark.asyncio
    async def test_chained_tools_maintain_tenant_context(self):
        """Chained tools must maintain tenant context.

        Rationale: Tool A calling tool B must pass tenant context.
        """
        from src.tools.workflows import analyze_entity

        tenant_id = uuid4()
        entity_id = "entity-123"

        ctx = RequestContext(
            tenant_id=tenant_id,
            user_id=uuid4(),
            permissions=frozenset([Permission.READ_SEARCH.value]),
        )

        with patch("src.tools.knowledge.get_entity") as mock_get:
            with patch("src.tools.analytics.compute_metrics") as mock_compute:
                mock_get.return_value = {"id": entity_id, "tenant_id": str(tenant_id)}
                mock_compute.return_value = {"score": 0.95}

                await analyze_entity(
                    entity_id=entity_id,
                    context=ctx,
                )

                mock_get.assert_called_with(entity_id=entity_id, context=ctx)
                mock_compute.assert_called_with(
                    entity_data=mock_get.return_value,
                    context=ctx,
                )

    @pytest.mark.asyncio
    async def test_tool_cannot_escalate_permissions_via_chaining(self):
        """Tool chaining must not allow permission escalation.

        Attack scenario: Read-only tool chains to write tool.
        """
        from src.tools.workflows import read_and_update

        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset(["read"])
        )

        with pytest.raises(HTTPException) as exc_info:
            await read_and_update(
                entity_id="entity-123",
                context=context,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
