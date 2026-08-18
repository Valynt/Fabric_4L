"""Phase 1 hardening tests for AuditedGraphMutation gateway.

Tests verify:
1. Direct mutation bypass is blocked by runtime guard
2. Audit events are emitted for all mutations
3. Metrics are incremented for mutations
4. Tenant isolation is enforced
5. Context enrichment (request_id, account_id, operation_source)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from neo4j import AsyncDriver

from src.db.audited_mutation import AuditedGraphMutation
from src.db.query_execution import TenantQueryValidationError


def _query_and_params(call):
    return call[0][0], call[0][1]


def _audit_query_and_params(call_args_list):
    for call in call_args_list:
        query, params = _query_and_params(call)
        if "AuditEvent" in query:
            return query, params
    raise AssertionError("AuditEvent query was not executed")


class TestMutationBypassBlocking:
    """Test that direct CREATE/MERGE/DELETE on tenant-owned labels is blocked."""

    @pytest.mark.asyncio
    async def test_direct_create_blocked(self):
        """Direct CREATE on tenant-owned label should be rejected."""
        session = AsyncMock()
        session.run = AsyncMock()
        
        context = MagicMock()
        context.is_bypass = False
        context.allow_system_query = False
        context.tenant_id = "test-tenant"
        
        query = "CREATE (n:Product {id: 'p1', tenant_id: $tenant_id})"
        
        with pytest.raises(TenantQueryValidationError) as exc_info:
            from src.db.query_execution import TenantQueryExecutor
            TenantQueryExecutor._validate(query, {"tenant_id": "test-tenant"}, context)
        
        assert "Direct CREATE/MERGE/DELETE on tenant-owned labels is prohibited" in str(exc_info.value)
        assert "AuditedGraphMutation" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_direct_merge_blocked(self):
        """Direct MERGE on tenant-owned label should be rejected."""
        session = AsyncMock()
        session.run = AsyncMock()
        
        context = MagicMock()
        context.is_bypass = False
        context.allow_system_query = False
        context.tenant_id = "test-tenant"
        
        query = "MERGE (n:ValueDriver {id: 'vd1', tenant_id: $tenant_id})"
        
        with pytest.raises(TenantQueryValidationError) as exc_info:
            from src.db.query_execution import TenantQueryExecutor
            TenantQueryExecutor._validate(query, {"tenant_id": "test-tenant"}, context)
        
        assert "Direct CREATE/MERGE/DELETE on tenant-owned labels is prohibited" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_direct_delete_blocked(self):
        """Direct DELETE on tenant-owned label should be rejected."""
        session = AsyncMock()
        session.run = AsyncMock()
        
        context = MagicMock()
        context.is_bypass = False
        context.allow_system_query = False
        context.tenant_id = "test-tenant"
        
        query = "MATCH (n:Product {id: 'p1', tenant_id: $tenant_id}) DELETE n"
        
        with pytest.raises(TenantQueryValidationError) as exc_info:
            from src.db.query_execution import TenantQueryExecutor
            TenantQueryExecutor._validate(query, {"tenant_id": "test-tenant"}, context)
        
        assert "Direct CREATE/MERGE/DELETE on tenant-owned labels is prohibited" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_system_query_allowed(self):
        """System queries with allow_system_query=True should bypass the check."""
        context = MagicMock()
        context.is_bypass = False
        context.allow_system_query = True
        context.tenant_id = None
        
        query = "CREATE (n:SyncMetadata {id: 's1'})"
        
        from src.db.query_execution import TenantQueryExecutor
        # Should not raise
        TenantQueryExecutor._validate(query, {}, context)


class TestAuditEventEmission:
    """Test that audit events are emitted for all mutations."""

    @pytest.mark.asyncio
    async def test_write_relationship_creates_audit_event(self):
        """write_relationship should create an AuditEvent node."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                request_id="req-123",
                account_id="acc-456",
                operation_source="test_source",
            )
            
            await mutation.write_relationship("src1", "HAS_DRIVER", "tgt1")
            
            # Verify audit event was created
            assert session.run.call_count >= 2  # One for relationship, one for audit
            audit_query, audit_params = _audit_query_and_params(session.run.call_args_list)
            assert "AuditEvent" in audit_query
            assert audit_params["action"] == "WRITE_RELATIONSHIP"

    @pytest.mark.asyncio
    async def test_write_node_creates_audit_event(self):
        """write_node should create an AuditEvent node."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            await mutation.write_node("Product", "p1", {"name": "Test Product"})
            
            # Verify audit event was created
            assert session.run.call_count >= 2
            audit_call = session.run.call_args_list[-1]
            audit_query, audit_params = _query_and_params(audit_call)
            assert "AuditEvent" in audit_query
            assert audit_params["action"] == "WRITE_NODE"

    @pytest.mark.asyncio
    async def test_delete_relationship_creates_audit_event(self):
        """delete_relationship should create an AuditEvent node."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            await mutation.delete_relationship("src1", "HAS_DRIVER", "tgt1")
            
            # Verify audit event was created
            assert session.run.call_count >= 2
            audit_call = session.run.call_args_list[-1]
            audit_query, audit_params = _query_and_params(audit_call)
            assert "AuditEvent" in audit_query
            assert audit_params["action"] == "DELETE_RELATIONSHIP"

    @pytest.mark.asyncio
    async def test_audit_event_contains_context(self):
        """Audit events should contain request_id, account_id, and operation_source."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                request_id="req-123",
                account_id="acc-456",
                operation_source="test_operation",
            )
            
            await mutation.write_relationship("src1", "HAS_DRIVER", "tgt1")
            
            # Verify audit event contains context
            _, audit_params = _audit_query_and_params(session.run.call_args_list)
            assert audit_params["request_id"] == "req-123"
            assert audit_params["account_id"] == "acc-456"
            assert audit_params["operation_source"] == "test_operation"


class TestMetricsIncrement:
    """Test that metrics are incremented for mutations."""

    @pytest.mark.asyncio
    async def test_write_relationship_increments_success_metric(self):
        """write_relationship should increment mutation success metric."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        metrics_mock = MagicMock()
        with patch('src.db.audited_mutation.get_metrics', return_value=metrics_mock):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            await mutation.write_relationship("src1", "HAS_DRIVER", "tgt1")
            
            # Verify success metric was incremented
            metrics_mock.increment_graph_mutation_success.assert_called_once_with(
                operation_type="relationship"
            )

    @pytest.mark.asyncio
    async def test_write_node_increments_success_metric(self):
        """write_node should increment mutation success metric."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        metrics_mock = MagicMock()
        with patch('src.db.audited_mutation.get_metrics', return_value=metrics_mock):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            await mutation.write_node("Product", "p1", {"name": "Test"})
            
            # Verify success metric was incremented
            metrics_mock.increment_graph_mutation_success.assert_called_once_with(
                operation_type="node"
            )

    @pytest.mark.asyncio
    async def test_delete_relationship_increments_success_metric(self):
        """delete_relationship should increment mutation success metric."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        metrics_mock = MagicMock()
        with patch('src.db.audited_mutation.get_metrics', return_value=metrics_mock):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            await mutation.delete_relationship("src1", "HAS_DRIVER", "tgt1")
            
            # Verify success metric was incremented
            metrics_mock.increment_graph_mutation_success.assert_called_once_with(
                operation_type="relationship_delete"
            )

    @pytest.mark.asyncio
    async def test_mutation_failure_increments_failure_metric(self):
        """Mutation failure should increment failure metric."""
        session = AsyncMock()
        session.run = AsyncMock(side_effect=Exception("DB error"))
        
        metrics_mock = MagicMock()
        with patch('src.db.audited_mutation.get_metrics', return_value=metrics_mock):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            with pytest.raises(Exception):
                await mutation.write_relationship("src1", "HAS_DRIVER", "tgt1")
            
            # Verify failure metric was incremented
            metrics_mock.increment_graph_mutation_failure.assert_called_once()


class TestTenantIsolation:
    """Test that tenant isolation is enforced in mutations."""

    @pytest.mark.asyncio
    async def test_relationship_write_includes_tenant_id(self):
        """Relationship write should include tenant_id in both endpoints."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            await mutation.write_relationship("src1", "HAS_DRIVER", "tgt1")
            
            # Verify tenant_id is in the query
            rel_call = session.run.call_args_list[0]
            rel_query, rel_params = _query_and_params(rel_call)
            assert "tenant_id" in rel_query
            assert rel_params["tenant_id"] == "test-tenant"

    @pytest.mark.asyncio
    async def test_node_write_includes_tenant_id(self):
        """Node write should include tenant_id."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            await mutation.write_node("Product", "p1", {"name": "Test"})
            
            # Verify tenant_id is in the query
            node_call = session.run.call_args_list[0]
            node_query, node_params = _query_and_params(node_call)
            assert "tenant_id" in node_query
            assert node_params["tenant_id"] == "test-tenant"


class TestBulkOperations:
    """Test bulk mutation operations."""

    @pytest.mark.asyncio
    async def test_write_nodes_batch_creates_audit(self):
        """Bulk node write should create audit event."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            nodes = [
                {"id": "p1", "name": "Product 1"},
                {"id": "p2", "name": "Product 2"},
            ]
            await mutation.write_nodes_batch("Product", nodes)
            
            # Verify audit event was created
            audit_call = session.run.call_args_list[-1]
            audit_query, audit_params = _query_and_params(audit_call)
            assert "AuditEvent" in audit_query
            assert audit_params["action"] == "WRITE_NODES_BATCH"

    @pytest.mark.asyncio
    async def test_write_relationships_batch_creates_audit(self):
        """Bulk relationship write should create audit event."""
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=result)
        
        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            triples = [
                {"src_id": "p1", "tgt_id": "vd1"},
                {"src_id": "p2", "tgt_id": "vd2"},
            ]
            await mutation.write_relationships_batch("HAS_DRIVER", triples)
            
            # Verify audit event was created
            audit_call = session.run.call_args_list[-1]
            audit_query, audit_params = _query_and_params(audit_call)
            assert "AuditEvent" in audit_query
            assert audit_params["action"] == "WRITE_RELATIONSHIPS_BATCH"

    @pytest.mark.asyncio
    async def test_write_nodes_batch_reports_database_merged_count(self):
        """Bulk node results must reflect what Neo4j matched and merged."""
        session = AsyncMock()
        merge_result = AsyncMock()
        merge_result.single = AsyncMock(return_value={"merged": 1})
        audit_result = AsyncMock()
        audit_result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(side_effect=[merge_result, audit_result])

        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant", session=session, operation_source="test_source"
            )
            result = await mutation.write_nodes_batch(
                "Product",
                [{"id": "p1", "name": "Product 1"}, {"id": "p2", "name": "Product 2"}],
            )

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_write_relationships_batch_reports_database_merged_count(self):
        """Missing endpoints must not be reported as written relationships."""
        session = AsyncMock()
        merge_result = AsyncMock()
        merge_result.single = AsyncMock(return_value={"merged": 1})
        audit_result = AsyncMock()
        audit_result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(side_effect=[merge_result, audit_result])

        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant", session=session, operation_source="test_source"
            )
            result = await mutation.write_relationships_batch(
                "HAS_DRIVER",
                [{"src_id": "p1", "tgt_id": "vd1"}, {"src_id": "missing", "tgt_id": "vd2"}],
            )

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_write_relationships_batch_propagates_result_consumption_failure(self):
        """Streaming failures must fail the mutation rather than report success."""
        session = AsyncMock()
        merge_result = AsyncMock()
        merge_result.single = AsyncMock(side_effect=RuntimeError("stream failed"))
        session.run = AsyncMock(return_value=merge_result)

        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(tenant_id="test-tenant", session=session)
            with pytest.raises(RuntimeError, match="stream failed"):
                await mutation.write_relationships_batch(
                    "HAS_DRIVER", [{"src_id": "p1", "tgt_id": "vd1"}]
                )

        assert session.run.call_count == 1

    @pytest.mark.asyncio
    async def test_delete_by_source_creates_audit(self):
        """Bulk delete by source should create audit event."""
        session = AsyncMock()
        rel_result = AsyncMock()
        rel_result.single = AsyncMock(return_value={"deleted": 10})
        entity_result = AsyncMock()
        entity_result.single = AsyncMock(return_value={"deleted": 5})
        audit_result = AsyncMock()
        audit_result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(side_effect=[rel_result, entity_result, audit_result])
        
        with patch('src.db.audited_mutation.get_metrics', return_value=None):
            mutation = AuditedGraphMutation(
                tenant_id="test-tenant",
                session=session,
                operation_source="test_source",
            )
            
            await mutation.delete_by_source("source-123")
            
            # Verify audit event was created
            audit_call = session.run.call_args_list[-1]
            audit_query, audit_params = _query_and_params(audit_call)
            assert "AuditEvent" in audit_query
            assert audit_params["action"] == "DELETE_BY_SOURCE"
