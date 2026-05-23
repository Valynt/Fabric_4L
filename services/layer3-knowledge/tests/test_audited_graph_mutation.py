"""Tests for the centralized AuditedGraphMutation pipeline."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from value_fabric.layer3.db.audited_mutation import AuditedGraphMutation
from value_fabric.layer3.utils.cypher_security import ALLOWED_REL_TYPES


@pytest.mark.unit
class TestAuditedGraphMutation:
    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def mutation(self, mock_session):
        return AuditedGraphMutation(tenant_id="tenant-a", session=mock_session)

    @pytest.mark.asyncio
    async def test_write_relationship_validates_rel_type(self, mutation):
        with pytest.raises(ValueError, match="Cypher injection guard"):
            await mutation.write_relationship("src-1", "INVALID_REL", "tgt-1")

    @pytest.mark.asyncio
    async def test_delete_relationship_validates_rel_type(self, mutation):
        with pytest.raises(ValueError, match="Cypher injection guard"):
            await mutation.delete_relationship("src-1", "INVALID_REL", "tgt-1")

    @pytest.mark.asyncio
    async def test_write_relationship_interpolates_allowed_rel_type(self, mutation, mock_session):
        allowed = list(ALLOWED_REL_TYPES)[0]
        result = await mutation.write_relationship("src-1", allowed, "tgt-1")

        assert result["status"] == "ok"
        assert result["rel_type"] == allowed

        # run_tenant_query is called at least twice: MERGE + audit
        assert mock_session.run.call_count >= 2
        merge_call = mock_session.run.call_args_list[0]
        query_arg = merge_call[0][0]
        assert f"-[r:{allowed}]->" in query_arg

    @pytest.mark.asyncio
    async def test_write_relationship_creates_audit_event(self, mutation, mock_session):
        allowed = list(ALLOWED_REL_TYPES)[0]
        await mutation.write_relationship("src-1", allowed, "tgt-1", properties={"weight": 1.0})

        # Find the audit CREATE call
        audit_calls = [
            call for call in mock_session.run.call_args_list
            if "CREATE (a:AuditEvent" in call[0][0]
        ]
        assert len(audit_calls) == 1
        params = audit_calls[0][0][1]
        assert params["tenant_id"] == "tenant-a"
        assert params["action"] == "WRITE_RELATIONSHIP"
        assert params["entity_id"] == f"src-1-{allowed}->tgt-1"

    @pytest.mark.asyncio
    async def test_delete_relationship_creates_audit_event(self, mutation, mock_session):
        allowed = list(ALLOWED_REL_TYPES)[0]
        await mutation.delete_relationship("src-1", allowed, "tgt-1")

        audit_calls = [
            call for call in mock_session.run.call_args_list
            if "CREATE (a:AuditEvent" in call[0][0]
        ]
        assert len(audit_calls) == 1
        params = audit_calls[0][0][1]
        assert params["tenant_id"] == "tenant-a"
        assert params["action"] == "DELETE_RELATIONSHIP"

    @pytest.mark.asyncio
    async def test_versioned_write_creates_relationship_version(self, mutation, mock_session):
        allowed = list(ALLOWED_REL_TYPES)[0]
        await mutation.write_relationship("src-1", allowed, "tgt-1", versioned=True)

        version_calls = [
            call for call in mock_session.run.call_args_list
            if "CREATE (v:RelationshipVersion" in call[0][0]
        ]
        assert len(version_calls) == 1
        params = version_calls[0][0][1]
        assert params["tenant_id"] == "tenant-a"
        assert params["src_id"] == "src-1"
        assert params["rel_type"] == allowed
        assert params["tgt_id"] == "tgt-1"

    @pytest.mark.asyncio
    async def test_tenant_id_injected_into_all_queries(self, mutation, mock_session):
        allowed = list(ALLOWED_REL_TYPES)[0]
        await mutation.write_relationship("src-1", allowed, "tgt-1")

        for call in mock_session.run.call_args_list:
            params = call[0][1]
            assert params.get("tenant_id") == "tenant-a", f"Missing tenant_id in call: {call[0][0][:80]}"

    @pytest.mark.asyncio
    async def test_cross_tenant_rejection_via_tenant_id_injection(self, mock_session):
        """AuditedGraphMutation must never pass a different tenant_id to the session."""
        mutation_a = AuditedGraphMutation(tenant_id="tenant-a", session=mock_session)
        allowed = list(ALLOWED_REL_TYPES)[0]
        await mutation_a.write_relationship("src-1", allowed, "tgt-1")

        for call in mock_session.run.call_args_list:
            params = call[0][1]
            tenant = params.get("tenant_id")
            assert tenant == "tenant-a", f"Cross-tenant leak detected: {tenant}"
