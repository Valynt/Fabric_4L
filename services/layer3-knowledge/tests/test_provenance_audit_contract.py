"""Contract and tenant fail-closed tests for provenance_audit routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.provenance_audit import (
    _fetch_provenance_steps,
    _parse_audit_details,
    _record_to_audit_log_entry,
    _require_tenant_id_from_context,
)
from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    ValidationError,
)


@pytest.mark.unit
def test_parse_audit_details_variants():
    """Verify deserialization handles dicts, valid JSON strings, invalid JSON, and non-strings."""
    # Dict returns as is
    assert _parse_audit_details({"key": "val"}) == {"key": "val"}

    # Valid JSON string
    assert _parse_audit_details('{"action": "extracted"}') == {"action": "extracted"}

    # Invalid JSON string wraps in raw
    assert _parse_audit_details("plain-text") == {"raw": "plain-text"}

    # Non-string, non-dict returns empty dict
    assert _parse_audit_details(12345) == {}
    assert _parse_audit_details(None) == {}


@pytest.mark.unit
def test_record_to_audit_log_entry_mapping():
    """Verify record fields are mapped cleanly to AuditLogEntry model."""
    now = datetime.now(UTC)
    raw = {
        "id": "evt-123",
        "timestamp": now,
        "event_type": "entity_extracted",
        "entity_id": "ent-1",
        "entity_type": "Capability",
        "action": "upsert",
        "agent": "ExtractionAgent",
        "details": '{"confidence": 0.95}',
    }
    entry = _record_to_audit_log_entry(raw)
    assert entry.id == "evt-123"
    assert entry.timestamp == now
    assert entry.event_type == "entity_extracted"
    assert entry.entity_id == "ent-1"
    assert entry.entity_type == "Capability"
    assert entry.action == "upsert"
    assert entry.agent == "ExtractionAgent"
    assert entry.details == {"confidence": 0.95}


@pytest.mark.asyncio
async def test_fetch_provenance_steps_fallback_when_empty():
    """Verify default creation step is returned when entity has no AuditEvent relations."""
    mock_neo4j = MagicMock()
    mock_neo4j.execute_query = AsyncMock(return_value=[])

    created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    steps = await _fetch_provenance_steps(
        neo4j=mock_neo4j,
        entity_id="ent-42",
        tenant_id="tenant-123",
        entity_created_at=created_at,
    )

    assert len(steps) == 1
    assert steps[0].step == 1
    assert steps[0].label == "Entity Created"
    assert steps[0].entity_id == "ent-42"
    assert steps[0].timestamp == created_at


@pytest.mark.unit
def test_require_tenant_id_from_context_missing():
    """Verify fail-closed error when request has no governance context."""
    mock_request = MagicMock()
    mock_request.state = MagicMock(spec=[])  # no governance_context

    with pytest.raises(AuthenticationError, match="Authentication context is required"):
        _require_tenant_id_from_context(mock_request, missing_tenant_detail="tenant missing")


@pytest.mark.unit
def test_provenance_and_audit_unauthenticated_reject():
    """Verify endpoint calls without auth/tenant context return 401/403."""
    client = TestClient(app)

    res_prov = client.get("/v1/provenance/ent-1")
    assert res_prov.status_code in (401, 403)

    res_audit = client.get("/v1/audit/logs")
    assert res_audit.status_code in (401, 403)
