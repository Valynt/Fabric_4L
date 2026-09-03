"""Tests for GATE Phase 3: MemoryGateway, ReplayRecorder, and contracts.

Covers:
- MemoryGateway provenance tracking and access log
- ReplayRecorder snapshot building and commit
- ReplayRecorder double-commit prevention
- Phase 3 JSON Schema contract conformance
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import jsonschema
import pytest
from value_fabric.shared.audit.models import MemoryAccessRecord, ReplaySnapshotRecord
from value_fabric.shared.governance.memory_gateway import MemoryGateway
from value_fabric.shared.governance.replay import ReplayRecorder

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "packages" / "platform-contract" / "schemas" / "gate"


def _load_schema(name: str) -> dict:
    path = SCHEMA_DIR / name
    assert path.exists(), f"Schema not found: {path}"
    return json.loads(path.read_text())


def _make_mock_engine() -> MagicMock:
    """Create a mock retrieval engine."""
    engine = MagicMock()
    engine.query = AsyncMock(return_value={
        "query": "test query",
        "entities": [{"id": "e1", "name": "Entity1", "type": "Company"}],
        "relationships": [{"source": "e1", "target": "e2", "type": "COMPETES_WITH"}],
        "context_graph": {},
        "traversal_path": [],
        "confidence_score": 0.95,
        "sources": ["graph_store"],
    })
    engine.get_entity_context = AsyncMock(return_value={
        "entity_id": "e1",
        "entity_count": 3,
        "relationship_count": 5,
        "context": {"neighbors": ["e2", "e3"]},
    })
    return engine


def _make_mock_abom() -> MagicMock:
    """Create a mock ABOM for ReplayRecorder."""
    abom = MagicMock()
    abom.manifest_hash.return_value = "a" * 64
    return abom


def _allow_policy_facade() -> MagicMock:
    facade = MagicMock()
    facade.evaluate_action = AsyncMock(return_value=MagicMock(effect=MagicMock(value="allow"), reason="ok"))
    return facade


# ═══════════════════════════════════════════════════════════════════════════
# MemoryGateway Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMemoryGateway:
    """MemoryGateway provenance tracking tests."""

    @pytest.mark.asyncio
    async def test_query_returns_provenance(self) -> None:
        engine = _make_mock_engine()
        policy = MagicMock()
        policy.evaluate_action = AsyncMock(return_value=MagicMock(effect=MagicMock(value="allow"), reason="ok"))
        gw = MemoryGateway(
            retrieval_engine=engine,
            tenant_id="t-123",
            agent_id="TestAgent-abcd1234",
            policy_facade=policy,
        )
        result = await gw.query("test query")

        assert "_provenance" in result
        assert result["_provenance"]["tenant_id"] == "t-123"
        assert result["_provenance"]["agent_id"] == "TestAgent-abcd1234"
        assert len(result["_provenance"]["content_hash"]) == 64

    @pytest.mark.asyncio
    async def test_query_denies_without_policy_facade(self) -> None:
        engine = _make_mock_engine()
        gw = MemoryGateway(retrieval_engine=engine, tenant_id="t-123")

        with pytest.raises(PermissionError, match="policy enforcement is unavailable"):
            await gw.query("blocked query")

    @pytest.mark.asyncio
    async def test_access_log_populated(self) -> None:
        engine = _make_mock_engine()
        gw = MemoryGateway(retrieval_engine=engine, tenant_id="t-123", policy_facade=_allow_policy_facade())
        await gw.query("first query")
        await gw.query("second query")

        assert len(gw.access_log) == 2
        assert gw.access_log[0]["query"] == "first query"
        assert gw.access_log[1]["query"] == "second query"

    @pytest.mark.asyncio
    async def test_content_hash_deterministic(self) -> None:
        engine = _make_mock_engine()
        gw = MemoryGateway(retrieval_engine=engine, tenant_id="t-123", policy_facade=_allow_policy_facade())
        r1 = await gw.query("test")
        r2 = await gw.query("test")

        assert r1["_provenance"]["content_hash"] == r2["_provenance"]["content_hash"]

    @pytest.mark.asyncio
    async def test_source_lineage_built(self) -> None:
        engine = _make_mock_engine()
        gw = MemoryGateway(retrieval_engine=engine, tenant_id="t-123", policy_facade=_allow_policy_facade())
        result = await gw.query("test")

        lineage = result["_provenance"]["source_lineage"]
        assert len(lineage) > 0
        # Should have graph_source and entity entries
        types = {entry["type"] for entry in lineage}
        assert "graph_source" in types or "entity" in types

    @pytest.mark.asyncio
    async def test_entity_context_provenance(self) -> None:
        engine = _make_mock_engine()
        gw = MemoryGateway(retrieval_engine=engine, tenant_id="t-123", policy_facade=_allow_policy_facade())
        result = await gw.get_entity_context("e1", hops=2)

        assert "_provenance" in result
        assert len(gw.access_log) == 1
        assert gw.access_log[0]["query"] == "entity_context:e1"


# ═══════════════════════════════════════════════════════════════════════════
# ReplayRecorder Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestReplayRecorder:
    """ReplayRecorder snapshot and commit tests."""

    def test_build_snapshot_structure(self) -> None:
        abom = _make_mock_abom()
        recorder = ReplayRecorder(
            agent_id="TestAgent-abcd1234",
            agent_type="TestAgent",
            abom=abom,
            tenant_id="t-123",
            trace_id="trace-001",
        )
        recorder.record_tool_invocations([
            {"tool_name": "tool_a", "request_hash": "a" * 64},
        ])
        recorder.record_memory_accesses([
            {"query": "test", "content_hash": "b" * 64},
        ])

        snapshot = recorder.build_snapshot()

        assert snapshot["agent_id"] == "TestAgent-abcd1234"
        assert snapshot["agent_type"] == "TestAgent"
        assert snapshot["manifest_hash"] == "a" * 64
        assert snapshot["tool_invocation_count"] == 1
        assert snapshot["memory_access_count"] == 1
        assert len(snapshot["snapshot_hash"]) == 64

    def test_snapshot_hash_is_valid_hex(self) -> None:
        """The snapshot hash must be a valid 64-character hex string."""
        abom = _make_mock_abom()

        def _build() -> str:
            r = ReplayRecorder(
                agent_id="TestAgent-abcd1234",
                agent_type="TestAgent",
                abom=abom,
            )
            r.record_tool_invocations([{"tool": "a"}])
            return r.build_snapshot()["snapshot_hash"]

        # Note: timestamps differ between calls, so hashes will differ.
        # This test only validates the hash format, not determinism.
        h = _build()
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    @pytest.mark.asyncio
    async def test_commit_emits_audit_event(self) -> None:
        abom = _make_mock_abom()
        recorder = ReplayRecorder(
            agent_id="TestAgent-abcd1234",
            agent_type="TestAgent",
            abom=abom,
        )
        snapshot = await recorder.commit()

        assert snapshot["agent_id"] == "TestAgent-abcd1234"
        assert len(snapshot["snapshot_hash"]) == 64

    @pytest.mark.asyncio
    async def test_double_commit_raises(self) -> None:
        recorder = ReplayRecorder(
            agent_id="TestAgent-abcd1234",
            agent_type="TestAgent",
        )
        await recorder.commit()

        with pytest.raises(RuntimeError, match="already called"):
            await recorder.commit()

    def test_snapshot_hash_deterministic_with_fixed_clock(self) -> None:
        from value_fabric.shared.testability import FixedClock

        clock = FixedClock()
        abom = _make_mock_abom()

        def _build() -> str:
            r = ReplayRecorder(
                agent_id="TestAgent-abcd1234",
                agent_type="TestAgent",
                abom=abom,
                clock=clock,
            )
            r.record_tool_invocations([{"tool": "a"}])
            r.record_memory_accesses([{"query": "q", "content_hash": "b" * 64}])
            return r.build_snapshot()["snapshot_hash"]

        assert _build() == _build()

    def test_snapshot_includes_memory_accesses(self) -> None:
        abom = _make_mock_abom()
        r = ReplayRecorder(
            agent_id="TestAgent-abcd1234",
            agent_type="TestAgent",
            abom=abom,
        )
        r.record_memory_accesses([{"query": "q", "content_hash": "c" * 64}])
        snapshot = r.build_snapshot()
        assert snapshot["memory_access_count"] == 1
        assert snapshot["memory_accesses"][0]["query"] == "q"


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3 Contract Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPhase3Contracts:
    """JSON Schema contract conformance for Phase 3 records."""

    def test_memory_access_record_conforms(self) -> None:
        schema = _load_schema("memory-access.schema.json")
        record = MemoryAccessRecord(
            query="test query",
            tenant_id="t-123",
            agent_id="TestAgent-abcd1234",
            content_hash="a" * 64,
            source_lineage=[{"source": "graph", "type": "graph_source"}],
            entity_count=5,
            relationship_count=3,
            trace_id="trace-001",
        )
        payload = json.loads(record.model_dump_json())
        jsonschema.Draft202012Validator(schema).validate(payload)

    def test_replay_snapshot_record_conforms(self) -> None:
        schema = _load_schema("replay-snapshot.schema.json")
        record = ReplaySnapshotRecord(
            agent_id="TestAgent-abcd1234",
            agent_type="TestAgent",
            manifest_hash="a" * 64,
            snapshot_hash="b" * 64,
            tool_invocation_count=3,
            memory_access_count=2,
            tenant_id="t-123",
            trace_id="trace-001",
        )
        payload = json.loads(record.model_dump_json())
        jsonschema.Draft202012Validator(schema).validate(payload)

    def test_invalid_snapshot_hash_rejected(self) -> None:
        schema = _load_schema("replay-snapshot.schema.json")
        payload = {
            "agent_id": "TestAgent-abcd1234",
            "snapshot_hash": "not-a-hash",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(payload)

    def test_schema_files_valid(self) -> None:
        for name in ["memory-access.schema.json", "replay-snapshot.schema.json"]:
            schema = _load_schema(name)
            jsonschema.Draft202012Validator.check_schema(schema)
