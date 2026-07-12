"""Contract tests for GATE Phase 1 JSON Schemas.

Validates that:
- Python model serialization conforms to the JSON Schema contracts
- Invalid payloads are rejected
- Schema files themselves are valid JSON Schema
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import jsonschema
import pytest
from value_fabric.shared.audit.models import (
    AuditAction,
    AuditEvent,
    AuditOutcome,
    ToolInvocationRecord,
)
from value_fabric.shared.crypto.canonical import canonical_hash

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "packages" / "platform-contract" / "schemas" / "gate"


def _load_schema(name: str) -> dict:
    """Load a JSON Schema from the contracts directory."""
    path = SCHEMA_DIR / name
    assert path.exists(), f"Schema not found: {path}"
    return json.loads(path.read_text())


# ═══════════════════════════════════════════════════════════════════════════
# Schema validity
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaValidity:
    """JSON Schema files must be valid Draft 2020-12 schemas."""

    @pytest.mark.parametrize(
        "schema_file",
        ["audit-event.schema.json", "tool-invocation-record.schema.json"],
    )
    def test_schema_is_valid(self, schema_file: str) -> None:
        schema = _load_schema(schema_file)
        # jsonschema.Draft202012Validator.check_schema raises on invalid
        jsonschema.Draft202012Validator.check_schema(schema)


# ═══════════════════════════════════════════════════════════════════════════
# Audit Event contract
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditEventContract:
    """AuditEvent model output must conform to audit-event.schema.json."""

    @pytest.fixture
    def schema(self) -> dict:
        return _load_schema("audit-event.schema.json")

    @pytest.fixture
    def validator(self, schema: dict) -> jsonschema.Draft202012Validator:
        return jsonschema.Draft202012Validator(schema)

    def test_minimal_event_conforms(self, validator: jsonschema.Draft202012Validator) -> None:
        """Minimal AuditEvent must validate."""
        event = AuditEvent(
            id=uuid4(),
            timestamp="2026-01-01T00:00:00+00:00",
            action=AuditAction.CREATE,
            outcome=AuditOutcome.SUCCESS,
            resource_type="tool",
        )
        payload = json.loads(event.model_dump_json())
        validator.validate(payload)

    def test_chained_event_conforms(self, validator: jsonschema.Draft202012Validator) -> None:
        """Chained AuditEvent with all GATE fields must validate."""
        event = AuditEvent(
            id=uuid4(),
            timestamp="2026-01-01T00:00:00+00:00",
            action=AuditAction.TOOL_INVOCATION,
            outcome=AuditOutcome.SUCCESS,
            resource_type="tool",
            resource_id="crm_sync",
            chain_id="tenant-1:crm_sync",
            sequence_number=1,
            previous_hash=None,
            event_hash="a" * 64,
            canonical_payload={"chain_id": "tenant-1:crm_sync"},
        )
        payload = json.loads(event.model_dump_json())
        validator.validate(payload)

    def test_invalid_event_hash_rejected(self, validator: jsonschema.Draft202012Validator) -> None:
        """event_hash must be a 64-char hex string."""
        payload = {
            "id": str(uuid4()),
            "timestamp": "2026-01-01T00:00:00+00:00",
            "action": "tool_invocation",
            "outcome": "success",
            "resource_type": "tool",
            "event_hash": "too-short",
        }
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(payload)

    def test_unknown_action_rejected(self, validator: jsonschema.Draft202012Validator) -> None:
        """Unknown action values must be rejected."""
        payload = {
            "id": str(uuid4()),
            "timestamp": "2026-01-01T00:00:00+00:00",
            "action": "unknown_action",
            "outcome": "success",
            "resource_type": "tool",
        }
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(payload)


# ═══════════════════════════════════════════════════════════════════════════
# Tool Invocation Record contract
# ═══════════════════════════════════════════════════════════════════════════


class TestToolInvocationRecordContract:
    """ToolInvocationRecord must conform to tool-invocation-record.schema.json."""

    @pytest.fixture
    def schema(self) -> dict:
        return _load_schema("tool-invocation-record.schema.json")

    @pytest.fixture
    def validator(self, schema: dict) -> jsonschema.Draft202012Validator:
        return jsonschema.Draft202012Validator(schema)

    def test_full_record_conforms(self, validator: jsonschema.Draft202012Validator) -> None:
        """Full ToolInvocationRecord must validate."""
        record = ToolInvocationRecord(
            tool_name="crm_sync",
            tool_version="1.0",
            tool_manifest_hash="b" * 64,
            request_hash=canonical_hash({"tool": "crm_sync"}),
            response_hash=canonical_hash({"status": "ok"}),
            policy_decision="allowed",
            invariant_checks=["budget_cap"],
            execution_time_ms=42,
            tenant_id="t-123",
            actor_id="agent-abc",
            trace_id="trace-001",
        )
        payload = json.loads(record.model_dump_json())
        validator.validate(payload)

    def test_minimal_record_conforms(self, validator: jsonschema.Draft202012Validator) -> None:
        """Minimal ToolInvocationRecord must validate."""
        record = ToolInvocationRecord(
            tool_name="graph_query",
            request_hash=canonical_hash({"q": "test"}),
        )
        payload = json.loads(record.model_dump_json())
        validator.validate(payload)

    def test_missing_tool_name_rejected(self, validator: jsonschema.Draft202012Validator) -> None:
        """tool_name is required."""
        payload = {"request_hash": "a" * 64}
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(payload)

    def test_invalid_request_hash_rejected(self, validator: jsonschema.Draft202012Validator) -> None:
        """request_hash must be a 64-char hex string."""
        payload = {"tool_name": "test", "request_hash": "not-a-hash"}
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(payload)
