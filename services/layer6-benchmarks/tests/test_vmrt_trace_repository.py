"""Unit tests for VMRT trace repository helpers."""

from datetime import datetime, timezone

from layer6_benchmarks.models.vmrt_trace import VMRTTraceRecord
from layer6_benchmarks.repositories.vmrt_trace_repository import (
    _node_to_vmrt_trace,
    _record_to_params,
)


def test_record_to_params_serializes_trace_payload() -> None:
    created_at = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)
    record = VMRTTraceRecord(
        trace_id="trace-1",
        tenant_id="tenant-1",
        schema_version="1.0.0",
        status="production_ready",
        trace={"trace_id": "trace-1", "schema_version": "1.0.0"},
        quality_score_overall="4.5",
        production_ready=True,
        errors=[],
        reviewer="reviewer@example.com",
        created_at=created_at,
        updated_at=created_at,
        promoted_at=created_at,
    )

    params = _record_to_params(record)

    assert params["trace_id"] == "trace-1"
    assert params["tenant_id"] == "tenant-1"
    assert params["trace_json"] == '{"schema_version": "1.0.0", "trace_id": "trace-1"}'
    assert params["errors_json"] == "[]"
    assert params["production_ready"] is True
    assert params["promoted_at"] == created_at.isoformat()


def test_node_to_vmrt_trace_reconstructs_record() -> None:
    node = {
        "trace_id": "trace-1",
        "tenant_id": "tenant-1",
        "schema_version": "1.0.0",
        "status": "validated",
        "trace_json": '{"trace_id": "trace-1"}',
        "quality_score_overall": "3.8",
        "production_ready": False,
        "errors_json": '["warning"]',
        "reviewer": None,
        "created_at": "2026-06-25T12:00:00+00:00",
        "updated_at": "2026-06-25T12:01:00+00:00",
        "promoted_at": None,
    }

    record = _node_to_vmrt_trace(node)

    assert record.trace_id == "trace-1"
    assert record.tenant_id == "tenant-1"
    assert record.status == "validated"
    assert record.trace == {"trace_id": "trace-1"}
    assert record.errors == ["warning"]
    assert record.promoted_at is None
