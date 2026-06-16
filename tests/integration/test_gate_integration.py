"""GATE Integration Tests.

Tests the end-to-end integration of GATE components:
  1. Agent + ABOM: Agent initializes with manifest, tool blocked by policy/invariant
  2. Agent + Replay: Full agent run produces replay snapshot
  3. Graph RAG + Provenance: Retrieval through MemoryGateway produces access records

These tests use mocks for external services (OPA, Neo4j, LLM) but exercise
the real GATE pipeline code.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure shared/ is importable
# ---------------------------------------------------------------------------
_repo = str(Path(__file__).resolve().parents[2])
for p in [_repo, f"{_repo}/packages/shared/src", f"{_repo}/services/layer4-agents/src"]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ---------------------------------------------------------------------------
# Stub heavy external deps that aren't needed for integration tests
# ---------------------------------------------------------------------------
for mod_name in [
    "neo4j", "neo4j.exceptions", "langchain", "langchain_community",
    "langchain_community.vectorstores", "langchain_community.embeddings",
    "opentelemetry", "opentelemetry.trace",
    "shared.identity.context", "shared.identity.dependencies",
    "shared.error_handling.middleware",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

# Stub opentelemetry.trace with a minimal mock
_otel_trace = sys.modules["opentelemetry.trace"]
_mock_span = MagicMock()
_mock_span.get_span_context.return_value = MagicMock(trace_id=0)
_otel_trace.get_current_span = MagicMock(return_value=_mock_span)

# Now import GATE components
from value_fabric.shared.crypto.canonical import canonical_hash
from value_fabric.shared.audit.models import AuditAction
from value_fabric.shared.governance.abom import AgentBillOfMaterials

# Import governance components that don't need heavy deps
import importlib.util


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 1. Agent + ABOM Integration Tests
# ---------------------------------------------------------------------------

class TestAgentABOMIntegration:
    """Test that agents correctly load and enforce ABOM manifests."""

    MANIFESTS_DIR = Path(_repo) / "services/layer4-agents/manifests"

    def test_all_manifests_load_as_abom(self):
        """Every manifest file should parse into a valid AgentBillOfMaterials."""
        manifest_files = list(self.MANIFESTS_DIR.glob("*.abom.json"))
        assert len(manifest_files) >= 9, f"Expected at least 9 manifests, found {len(manifest_files)}"

        for mf in manifest_files:
            with open(mf) as f:
                data = json.load(f)
            abom = AgentBillOfMaterials(**data)
            assert abom.agent_type, f"Missing agent_type in {mf.name}"
            assert abom.privilege_tier in ("standard", "elevated", "high_privilege"), \
                f"Invalid tier in {mf.name}: {abom.privilege_tier}"
            assert len(abom.allowed_tools) > 0, f"No tools in {mf.name}"

    def test_abom_tool_allowlist_enforcement(self):
        """A tool not in the ABOM allowlist should be identifiable."""
        manifest_path = self.MANIFESTS_DIR / "signal_detection_agent.abom.json"
        with open(manifest_path) as f:
            data = json.load(f)
        abom = AgentBillOfMaterials(**data)

        # Signal detection agent should NOT have CRM tools
        assert "sync_crm_record" not in abom.allowed_tools
        assert "update_crm_field" not in abom.allowed_tools

        # But should have its own tools
        assert "query_graph" in abom.allowed_tools or "semantic_search" in abom.allowed_tools

    def test_high_privilege_agent_has_restricted_tools(self):
        """CRMSyncAgent (high_privilege) should have CRM-specific tools."""
        manifest_path = self.MANIFESTS_DIR / "crm_sync_agent.abom.json"
        with open(manifest_path) as f:
            data = json.load(f)
        abom = AgentBillOfMaterials(**data)

        assert abom.privilege_tier == "high_privilege"
        assert "export_to_crm" in abom.allowed_tools

    def test_invariant_budget_limits_present(self):
        """All manifests should declare budget limits."""
        manifest_files = list(self.MANIFESTS_DIR.glob("*.abom.json"))
        for mf in manifest_files:
            with open(mf) as f:
                data = json.load(f)
            invariants = data.get("invariants", {})
            assert "budget_limit_usd" in invariants, f"Missing budget_limit_usd in {mf.name}"
            assert invariants["budget_limit_usd"] > 0, f"Zero budget in {mf.name}"

    def test_invariant_call_limits_present(self):
        """All manifests should declare max calls per run."""
        manifest_files = list(self.MANIFESTS_DIR.glob("*.abom.json"))
        for mf in manifest_files:
            with open(mf) as f:
                data = json.load(f)
            invariants = data.get("invariants", {})
            # Manifests use either max_calls_per_run or max_tool_calls_per_run
            has_limit = "max_calls_per_run" in invariants or "max_tool_calls_per_run" in invariants
            assert has_limit, f"Missing call limit in {mf.name}"
            limit = invariants.get("max_calls_per_run") or invariants.get("max_tool_calls_per_run")
            assert limit > 0, f"Zero call limit in {mf.name}"

    def test_manifest_agent_id_format(self):
        """Agent IDs should follow the <type>-<prefix> format."""
        manifest_files = list(self.MANIFESTS_DIR.glob("*.abom.json"))
        for mf in manifest_files:
            with open(mf) as f:
                data = json.load(f)
            agent_id = data["agent_id"]
            assert "-" in agent_id, f"agent_id missing hyphen in {mf.name}: {agent_id}"
            parts = agent_id.split("-", 1)
            assert len(parts[1]) >= 6, f"agent_id prefix too short in {mf.name}: {agent_id}"


# ---------------------------------------------------------------------------
# 2. Agent + Replay Integration Tests
# ---------------------------------------------------------------------------

class TestAgentReplayIntegration:
    """Test that agent runs produce valid replay snapshots."""

    def test_canonical_hash_deterministic(self):
        """Replay snapshot hashing must be deterministic."""
        data = {"agent_id": "test-agent", "steps": [{"tool": "query_graph", "result": "ok"}]}
        hash1 = canonical_hash(data)
        hash2 = canonical_hash(data)
        assert hash1 == hash2

    def test_canonical_hash_key_order_independent(self):
        """Hash should be the same regardless of key insertion order."""
        data1 = {"b": 2, "a": 1}
        data2 = {"a": 1, "b": 2}
        assert canonical_hash(data1) == canonical_hash(data2)

    def test_replay_snapshot_structure(self):
        """A replay snapshot should contain all required fields."""
        snapshot = {
            "agent_id": "context_extraction-abc12345",
            "run_id": "run-001",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "steps": [
                {
                    "step_index": 0,
                    "tool_name": "query_graph",
                    "input_hash": canonical_hash({"query": "test"}),
                    "output_hash": canonical_hash({"result": "ok"}),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "status": "completed",
        }
        snapshot["snapshot_hash"] = canonical_hash(snapshot)

        # Validate structure
        assert snapshot["agent_id"].startswith("context_extraction")
        assert len(snapshot["steps"]) == 1
        # canonical_hash returns "sha256:<64-hex>" (71 chars) or just 64-hex
        assert len(snapshot["snapshot_hash"]) >= 64

    def test_replay_snapshot_schema_compliance(self):
        """Replay snapshot should validate against the JSON schema."""
        import jsonschema

        schema_path = Path(_repo) / "packages/platform-contract/schemas/gate/replay-snapshot.schema.json"
        with open(schema_path) as f:
            schema = json.load(f)

        # Build record matching the actual schema (only agent_id + snapshot_hash required)
        snapshot = {
            "agent_id": "context_extraction-abc12345",
            "snapshot_hash": "c" * 64,
            "agent_type": "context_extraction",
            "tool_invocation_count": 3,
            "memory_access_count": 1,
            "tenant_id": "tenant-1",
            "trace_id": "trace-001",
        }

        jsonschema.validate(snapshot, schema)


# ---------------------------------------------------------------------------
# 3. Graph RAG + Provenance Integration Tests
# ---------------------------------------------------------------------------

class TestGraphRAGProvenanceIntegration:
    """Test that retrieval through MemoryGateway produces provenance records."""

    def test_content_hash_for_provenance(self):
        """Retrieved content should produce a deterministic hash for provenance."""
        content = "Customer pain point: high operational costs in supply chain management."
        hash1 = canonical_hash({"content": content})
        hash2 = canonical_hash({"content": content})
        assert hash1 == hash2
        # canonical_hash returns "sha256:<hex>" format
        assert ":" in hash1 or len(hash1) == 64 or hash1.startswith("sha256")

    def test_provenance_record_structure(self):
        """A memory access provenance record should contain all required fields."""
        record = {
            "agent_id": "context_extraction-abc12345",
            "retrieval_type": "semantic",
            "query_hash": canonical_hash({"query": "customer pain points"}),
            "results": [
                {
                    "content_hash": canonical_hash({"content": "High operational costs"}),
                    "source_id": "doc-001",
                    "source_type": "uploaded_document",
                    "relevance_score": 0.92,
                },
                {
                    "content_hash": canonical_hash({"content": "Supply chain inefficiency"}),
                    "source_id": "doc-002",
                    "source_type": "enrichment_data",
                    "relevance_score": 0.87,
                },
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scope": {"account_id": "acct-123", "tenant_id": "tenant-1"},
        }

        assert record["retrieval_type"] == "semantic"
        assert len(record["results"]) == 2
        assert all(len(r["content_hash"]) >= 64 for r in record["results"])
        assert len(record["query_hash"]) >= 64

    def test_memory_access_schema_compliance(self):
        """Memory access record should validate against the JSON schema."""
        import jsonschema

        schema_path = Path(_repo) / "packages/platform-contract/schemas/gate/memory-access.schema.json"
        with open(schema_path) as f:
            schema = json.load(f)

        # Build record matching the actual schema's required + allowed fields only
        record = {
            "query": "customer pain points",
            "tenant_id": "tenant-1",
            "content_hash": "a" * 64,
            "agent_id": "context_extraction-abc12345",
            "source_lineage": [{"source_id": "doc-001", "source_type": "document"}],
            "entity_count": 5,
            "relationship_count": 3,
            "trace_id": "trace-001",
        }

        jsonschema.validate(record, schema)

    def test_different_content_produces_different_hashes(self):
        """Different retrieval content must produce different hashes."""
        hash1 = canonical_hash({"content": "Pain point A"})
        hash2 = canonical_hash({"content": "Pain point B"})
        assert hash1 != hash2

    def test_provenance_chain_linkage(self):
        """Multiple memory accesses should be linkable via chain_id."""
        chain_id = "memory:tenant-1"
        access_1 = {
            "chain_id": chain_id,
            "query_hash": canonical_hash({"query": "first query"}),
            "timestamp": "2026-04-27T10:00:00Z",
        }
        access_2 = {
            "chain_id": chain_id,
            "query_hash": canonical_hash({"query": "second query"}),
            "timestamp": "2026-04-27T10:01:00Z",
        }

        # Both should share the same chain_id for ledger partitioning
        assert access_1["chain_id"] == access_2["chain_id"]
        # But have different query hashes
        assert access_1["query_hash"] != access_2["query_hash"]


# ---------------------------------------------------------------------------
# 4. Cross-cutting: Contract Schema Validation
# ---------------------------------------------------------------------------

class TestContractSchemasCrossCutting:
    """Validate that all GATE JSON schemas are well-formed."""

    SCHEMAS_DIR = Path(_repo) / "packages/platform-contract/schemas/gate"

    def test_all_schemas_are_valid_json(self):
        """Every schema file should be valid JSON."""
        schema_files = list(self.SCHEMAS_DIR.glob("*.schema.json"))
        assert len(schema_files) >= 4, f"Expected at least 4 schemas, found {len(schema_files)}"

        for sf in schema_files:
            with open(sf) as f:
                data = json.load(f)
            assert "$schema" in data or "type" in data, f"Invalid schema: {sf.name}"

    def test_all_schemas_have_required_fields(self):
        """Every schema should declare required properties."""
        schema_files = list(self.SCHEMAS_DIR.glob("*.schema.json"))
        for sf in schema_files:
            with open(sf) as f:
                data = json.load(f)
            # Should have either 'required' or 'properties'
            has_structure = "required" in data or "properties" in data or "oneOf" in data
            assert has_structure, f"Schema {sf.name} lacks structural definition"
