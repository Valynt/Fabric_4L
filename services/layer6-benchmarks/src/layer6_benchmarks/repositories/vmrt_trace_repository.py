"""Tenant-scoped Neo4j repository for VMRT trace records."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from neo4j import AsyncDriver
from value_fabric.shared.database import require_tenant_context

from ..models.vmrt_trace import VMRTTraceRecord, VMRTTraceStatus


class VMRTTraceRepository:
    """CRUD operations for persisted Value Modeling Reasoning Traces."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    @staticmethod
    def _require_tenant_scope(tenant_id: str | None, *, operation: str) -> str:
        return require_tenant_context(tenant_id, operation=f"vmrt_trace_repository.{operation}")

    async def save_trace(self, record: VMRTTraceRecord) -> VMRTTraceRecord:
        """Persist a VMRT trace record under the authenticated tenant."""
        self._require_tenant_scope(record.tenant_id, operation="save_trace")
        async with self._driver.session() as session:
            await session.execute_write(self._tx_save_trace, record)
        return record

    @staticmethod
    async def _tx_save_trace(tx, record: VMRTTraceRecord) -> None:
        await tx.run(
            """
            MERGE (t:VMRTTrace {trace_id: $trace_id, tenant_id: $tenant_id})
            ON CREATE SET t.created_at = $created_at
            SET t.schema_version = $schema_version,
                t.status = $status,
                t.trace_json = $trace_json,
                t.quality_score_overall = $quality_score_overall,
                t.production_ready = $production_ready,
                t.errors_json = $errors_json,
                t.reviewer = $reviewer,
                t.promoted_at = $promoted_at,
                t.updated_at = $updated_at
            """,
            **_record_to_params(record),
        )

    async def get_trace(self, trace_id: str, tenant_id: str) -> VMRTTraceRecord | None:
        """Return a tenant-owned VMRT trace record."""
        tenant_id = self._require_tenant_scope(tenant_id, operation="get_trace")
        async with self._driver.session() as session:
            return await session.execute_read(self._tx_get_trace, trace_id, tenant_id)

    @staticmethod
    async def _tx_get_trace(tx, trace_id: str, tenant_id: str) -> VMRTTraceRecord | None:
        records = await tx.run(
            """
            MATCH (t:VMRTTrace {trace_id: $trace_id, tenant_id: $tenant_id})
            RETURN t
            """,
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        record = await records.single()
        if not record:
            return None
        return _node_to_vmrt_trace(record["t"])

    async def promote_trace(
        self, trace_id: str, tenant_id: str, *, reviewer: str
    ) -> VMRTTraceRecord | None:
        """Mark a tenant-owned, production-ready VMRT trace as promoted."""
        tenant_id = self._require_tenant_scope(tenant_id, operation="promote_trace")
        async with self._driver.session() as session:
            return await session.execute_write(
                self._tx_promote_trace,
                trace_id,
                tenant_id,
                reviewer,
                datetime.utcnow().isoformat(),
            )

    @staticmethod
    async def _tx_promote_trace(
        tx, trace_id: str, tenant_id: str, reviewer: str, promoted_at: str
    ) -> VMRTTraceRecord | None:
        records = await tx.run(
            """
            MATCH (t:VMRTTrace {trace_id: $trace_id, tenant_id: $tenant_id})
            WHERE t.production_ready = true
            SET t.status = 'production_ready',
                t.reviewer = $reviewer,
                t.promoted_at = $promoted_at,
                t.updated_at = $promoted_at
            RETURN t
            """,
            trace_id=trace_id,
            tenant_id=tenant_id,
            reviewer=reviewer,
            promoted_at=promoted_at,
        )
        record = await records.single()
        if not record:
            return None
        return _node_to_vmrt_trace(record["t"])


def _record_to_params(record: VMRTTraceRecord) -> dict[str, Any]:
    return {
        "trace_id": record.trace_id,
        "tenant_id": record.tenant_id,
        "schema_version": record.schema_version,
        "status": record.status,
        "trace_json": json.dumps(record.trace, sort_keys=True),
        "quality_score_overall": record.quality_score_overall,
        "production_ready": record.production_ready,
        "errors_json": json.dumps(record.errors, sort_keys=True),
        "reviewer": record.reviewer,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "promoted_at": record.promoted_at.isoformat() if record.promoted_at else None,
    }


def _node_to_vmrt_trace(node: dict[str, Any]) -> VMRTTraceRecord:
    trace_json = node.get("trace_json") or "{}"
    errors_json = node.get("errors_json") or "[]"
    return VMRTTraceRecord(
        trace_id=node["trace_id"],
        tenant_id=node["tenant_id"],
        schema_version=node["schema_version"],
        status=_coerce_status(node.get("status")),
        trace=json.loads(trace_json),
        quality_score_overall=node.get("quality_score_overall"),
        production_ready=bool(node.get("production_ready")),
        errors=list(json.loads(errors_json)),
        reviewer=node.get("reviewer"),
        created_at=_parse_datetime(node.get("created_at")),
        updated_at=_parse_datetime(node.get("updated_at")),
        promoted_at=_parse_optional_datetime(node.get("promoted_at")),
    )


def _coerce_status(value: str | None) -> VMRTTraceStatus:
    if value in {"draft", "validated", "production_ready", "rejected"}:
        return value
    return "draft"


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return _parse_datetime(value)


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
