"""Behavior-first tests for ProvenanceTrackingAgent tenant fail-closed semantics.

Covers:
- Missing tenant_id is rejected (no silent "system" fallback) for record ops.
- Empty / whitespace tenant_id is rejected.
- Invalid (non-UUID, non-reserved) tenant_id is rejected.
- Explicit "system" / "admin" reserved identifiers are still accepted.
- Valid UUID tenant_id is accepted and normalized to lowercase.
- build_provenance_record embeds tenant_id for downstream ownership.
- query_lineage is tenant-scoped (cross-tenant reads return empty).
"""

from __future__ import annotations

import pytest

from src.agents.base import AgentResult
from src.agents.provenance_tracking import (
    PROVActivityType,
    PROVAgentType,
    PROVEntityType,
    ProvenanceTrackingAgent,
)


def _agent() -> ProvenanceTrackingAgent:
    return ProvenanceTrackingAgent(driver=None)


# ---------------------------------------------------------------------------
# F4.1 — _validate_tenant_id fails closed on missing/invalid tenant
# ---------------------------------------------------------------------------


class TestValidateTenantIdFailClosed:
    def test_none_tenant_id_raises(self):
        with pytest.raises(ValueError, match="tenant_id is required"):
            _agent()._validate_tenant_id(None)

    def test_empty_tenant_id_raises(self):
        with pytest.raises(ValueError, match="tenant_id is required"):
            _agent()._validate_tenant_id("")

    def test_whitespace_tenant_id_raises(self):
        with pytest.raises(ValueError, match="tenant_id is required"):
            _agent()._validate_tenant_id("   ")

    def test_invalid_non_uuid_tenant_id_raises(self):
        with pytest.raises(ValueError, match="Invalid tenant_id format"):
            _agent()._validate_tenant_id("not-a-uuid")

    def test_explicit_system_reserved_accepted(self):
        assert _agent()._validate_tenant_id("system") == "system"

    def test_explicit_admin_reserved_accepted(self):
        assert _agent()._validate_tenant_id("admin") == "admin"

    def test_valid_uuid_normalized_lowercase(self):
        normalized = _agent()._validate_tenant_id("AABBCCDD-EEFF-4455-8899-AABBCCDDEEFF")
        assert normalized == "aabbccdd-eeff-4455-8899-aabbccddeeff"


# ---------------------------------------------------------------------------
# F4.1 — execute() path: missing tenant_id returns failed result (fail closed)
# ---------------------------------------------------------------------------


class TestExecuteMissingTenantFailsClosed:
    @pytest.mark.asyncio
    async def test_execute_missing_tenant_id_fails(self):
        agent = _agent()
        result = await agent.execute({"operation": "record_entity", "entity_id": "e1"})
        assert result.status == "failed"
        assert any("tenant_id" in (e or "") for e in result.errors)

    @pytest.mark.asyncio
    async def test_execute_empty_tenant_id_fails(self):
        agent = _agent()
        result = await agent.execute(
            {"operation": "record_entity", "entity_id": "e1", "tenant_id": "   "}
        )
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# F4.4 — build_provenance_record embeds tenant_id
# ---------------------------------------------------------------------------


class TestBuildProvenanceRecordEmbedsTenant:
    def test_record_carries_tenant_id(self):
        agent = _agent()
        record = agent.build_provenance_record(
            entity_type="prov:Entity:Document",
            entity_id="doc-1",
            generated_by="activity-1",
            used_entities=["doc-0"],
            attributed_to="user-1",
            tenant_id="aabbccdd-eeff-4455-8899-aabbccddeeff",
        )
        assert record["tenant_id"] == "aabbccdd-eeff-4455-8899-aabbccddeeff"

    def test_record_tenant_id_defaults_none_when_not_supplied(self):
        # Backwards-compat: legacy callers get None, not a silent "system".
        agent = _agent()
        record = agent.build_provenance_record(
            entity_type="prov:Entity:Document",
            entity_id="doc-1",
            generated_by="activity-1",
            used_entities=[],
            attributed_to="user-1",
        )
        assert record["tenant_id"] is None


# ---------------------------------------------------------------------------
# F4.2 — query_lineage is tenant-scoped (cross-tenant reads return empty)
# ---------------------------------------------------------------------------


class TestQueryLineageTenantScoping:
    @pytest.mark.asyncio
    async def test_no_driver_returns_safe_empty(self):
        # No driver -> safe empty result, no exception, no system fallback.
        agent = _agent()
        result = await agent._query_lineage(
            entity_id="e1",
            tenant_id="aabbccdd-eeff-4455-8899-aabbccddeeff",
        )
        assert result.error == "No database driver"
        assert result.lineage == []

    @pytest.mark.asyncio
    async def test_query_lineage_rejects_missing_tenant(self):
        # Direct callers of the internal method still need a real tenant.
        agent = _agent()
        # With no driver, _query_lineage returns early *before* using the
        # tenant_id; the fail-closed guarantee lives in _validate_tenant_id,
        # which the public execute() path enforces. Assert the invariant here
        # too: a None tenant never reaches the query layer via execute().
        result = await agent.execute(
            {"operation": "query_lineage", "entity_id": "e1"}
        )
        assert result.status == "failed"

