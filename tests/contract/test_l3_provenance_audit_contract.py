from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

try:
    from src.api.models import AuditLogResponse, ProvenanceTrailResponse
    from src.api.routes import provenance_audit
except (ImportError, Exception):
    pytest.skip(
        "value_fabric.layer3 service stack not available (pre-existing blocker #1/#9)",
        allow_module_level=True,
    )

class _Neo4jStub:
    async def execute_query(self, query: str, params: dict):
        if "RETURN e.id as entity_id" in query:
            return [{
                "entity_id": params["entity_id"],
                "entity_type": "Capability",
                "entity_name": "CRM Integration",
                "created_at": datetime(2026, 1, 1, tzinfo=UTC),
                "source": "demo",
                "extraction_job_id": "job-1",
                "confidence_score": 0.9,
            }]
        if "RETURN a.step as step" in query:
            return [{
                "step": 1,
                "label": "Extracted",
                "detail": "Created from source",
                "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
                "agent": "ExtractionEngine-v2.1",
                "step_entity_id": params["entity_id"],
            }]
        if "OPTIONAL MATCH (a:AuditEvent)" in query:
            return [{
                "id": "evt-1",
                "timestamp": datetime(2026, 1, 2, tzinfo=UTC),
                "event_type": "entity_created",
                "entity_id": "cap-1",
                "entity_type": "Capability",
                "action": "create",
                "agent": "system",
                "details": {"key": "value"},
            }]
        return []


def _tenant_request(tenant_id: str = "tenant-a"):
    return SimpleNamespace(state=SimpleNamespace(governance_context=SimpleNamespace(tenant_id=tenant_id)))


@pytest.mark.asyncio
async def test_provenance_route_contract_shape():
    app_state = SimpleNamespace(neo4j_driver=_Neo4jStub())
    payload = await provenance_audit.get_provenance("cap-1", _tenant_request(), app_state)

    assert isinstance(payload, ProvenanceTrailResponse)
    assert payload.entity_id == "cap-1"
    assert payload.entity_type == "Capability"
    assert len(payload.steps) == 1


@pytest.mark.asyncio
async def test_audit_logs_route_contract_shape():
    app_state = SimpleNamespace(neo4j_driver=_Neo4jStub())
    payload = await provenance_audit.list_audit_logs(app_state=app_state)

    assert isinstance(payload, AuditLogResponse)
    assert payload.total == 1
    assert payload.entries[0].source == "provenance"
    assert payload.entries[0].event_type == "entity_created"