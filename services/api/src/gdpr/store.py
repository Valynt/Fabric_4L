"""
Persistent storage for GDPR deletion jobs.

Deletion reports are stored in PostgreSQL as immutable JSONB records.
An append-only invariant is enforced at the application layer:
  - INSERT only (no UPDATE, no DELETE on gdpr_deletion_jobs rows).
  - A hash chain column (previous_hash) links records for tamper evidence.

This module also supports Redis-based hot caching for status polling.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Tuple, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from value_fabric.db import get_db_session
from value_fabric.cache import get_redis

from .deletion import DeletionReport, DeletionStatus

# ---------------------------------------------------------------------------
# SQL DDL (for reference — applied via Alembic migration)
# ---------------------------------------------------------------------------
GDPR_JOBS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS gdpr_deletion_jobs (
    request_id            UUID PRIMARY KEY,
    tenant_id             TEXT NOT NULL,
    initiated_by          TEXT NOT NULL,
    initiated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at          TIMESTAMPTZ,
    status                TEXT NOT NULL CHECK (status IN ('in_progress','completed','partial','failed')),
    total_records_deleted INT NOT NULL DEFAULT 0,
    verification_passed   BOOLEAN,
    audit_log_hash        TEXT,
    error_summary         TEXT,
    reason                TEXT NOT NULL,
    report_json           JSONB NOT NULL,
    previous_hash         TEXT,          -- hash chain for tamper evidence
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_gdpr_jobs_tenant_status ON gdpr_deletion_jobs(tenant_id, status);
CREATE INDEX idx_gdpr_jobs_initiated_at  ON gdpr_deletion_jobs(initiated_at DESC);

-- Append-only enforcement: no UPDATE / DELETE via trigger
CREATE OR REPLACE FUNCTION _gdpr_jobs_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'gdpr_deletion_jobs is append-only. UPDATE and DELETE are forbidden.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER gdpr_jobs_append_only_trigger
    BEFORE UPDATE OR DELETE ON gdpr_deletion_jobs
    FOR EACH ROW EXECUTE FUNCTION _gdpr_jobs_append_only();
"""

# ---------------------------------------------------------------------------
# Storage operations
# ---------------------------------------------------------------------------

async def save_deletion_job(
    report: DeletionReport,
    reason: str,
    status: Optional[DeletionStatus] = None,
    error: Optional[str] = None,
) -> None:
    """
    Persist a DeletionReport to the append-only gdpr_deletion_jobs table.

    Also writes a hot cache entry (Redis, TTL 24h) for fast status polling.

    Uses the canonical async session lifecycle: the session is borrowed from
    get_db_session(), which commits on successful exit and rolls back on
    exception. Route-level code therefore never calls db.commit()/rollback().
    """
    report_dict = report.to_dict()
    report_json = json.dumps(report_dict, sort_keys=True, default=str)

    effective_status = status.value if status else report.status.value
    effective_error = error or report.error_summary

    stmt = text(
        """
        INSERT INTO gdpr_deletion_jobs (
            request_id, tenant_id, initiated_by, initiated_at,
            completed_at, status, total_records_deleted,
            verification_passed, audit_log_hash, error_summary,
            reason, report_json, previous_hash
        ) VALUES (
            :request_id, :tenant_id, :initiated_by, :initiated_at,
            :completed_at, :status, :total_records_deleted,
            :verification_passed, :audit_log_hash, :error_summary,
            :reason, :report_json, :previous_hash
        )
        """
    )

    async for db in get_db_session():
        # Hash chain: link to previous record for this tenant
        prev_hash = await _get_previous_hash(db, report.tenant_id)
        chain_hash = _compute_chain_hash(report_json, prev_hash)

        await db.execute(
            stmt,
            {
                "request_id": report.request_id,
                "tenant_id": report.tenant_id,
                "initiated_by": report.initiated_by,
                "initiated_at": report.initiated_at,
                "completed_at": report.completed_at,
                "status": effective_status,
                "total_records_deleted": report.total_records_deleted,
                "verification_passed": report.verification_passed,
                "audit_log_hash": report.audit_log_hash or report.compute_hash(),
                "error_summary": effective_error,
                "reason": reason,
                "report_json": report_json,
                "previous_hash": chain_hash,
            },
        )
        break

    # Hot cache for polling (written after the session lifecycle commits)
    redis = await get_redis()
    cache_key = _cache_key(report.request_id)
    await redis.setex(cache_key, 86400, report_json)


async def get_deletion_job(
    request_id: str,
) -> Tuple[Optional[DeletionReport], str]:
    """
    Retrieve a DeletionReport by request_id.

    Tries Redis hot cache first, falls back to PostgreSQL.
    Returns (report, reason) or (None, "") if not found.
    """
    # Hot cache
    redis = await get_redis()
    cache_key = _cache_key(request_id)
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return _dict_to_report(data), data.get("reason", "")

    # Cold store
    db: AsyncSession = await anext(get_db_session())
    try:
        stmt = text(
            "SELECT report_json, reason FROM gdpr_deletion_jobs WHERE request_id = :rid"
        )
        result = await db.execute(stmt, {"rid": request_id})
        row = result.fetchone()
        if row is None:
            return None, ""
        data = json.loads(row.report_json)
        return _dict_to_report(data), row.reason
    finally:
        await db.close()


async def list_deletion_jobs_for_tenant(
    tenant_id: str,
    status_filter: Optional[str] = None,
    limit: int = 10,
) -> List[DeletionReport]:
    """
    Return recent deletion jobs for a tenant, optionally filtered by status.
    """
    db: AsyncSession = await anext(get_db_session())
    try:
        if status_filter:
            stmt = text(
                """
                SELECT report_json FROM gdpr_deletion_jobs
                WHERE tenant_id = :tenant_id AND status = :status
                ORDER BY initiated_at DESC
                LIMIT :limit
                """
            )
            result = await db.execute(
                stmt,
                {"tenant_id": tenant_id, "status": status_filter, "limit": limit},
            )
        else:
            stmt = text(
                """
                SELECT report_json FROM gdpr_deletion_jobs
                WHERE tenant_id = :tenant_id
                ORDER BY initiated_at DESC
                LIMIT :limit
                """
            )
            result = await db.execute(
                stmt, {"tenant_id": tenant_id, "limit": limit}
            )
        rows = result.fetchall()
        return [_dict_to_report(json.loads(r.report_json)) for r in rows]
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Tamper-evidence helpers
# ---------------------------------------------------------------------------

async def _get_previous_hash(db: AsyncSession, tenant_id: str) -> Optional[str]:
    """Fetch the previous_hash of the most recent job for this tenant."""
    stmt = text(
        """
        SELECT previous_hash FROM gdpr_deletion_jobs
        WHERE tenant_id = :tenant_id
        ORDER BY initiated_at DESC
        LIMIT 1
        """
    )
    result = await db.execute(stmt, {"tenant_id": tenant_id})
    row = result.fetchone()
    return row.previous_hash if row else None


def _compute_chain_hash(report_json: str, previous_hash: Optional[str]) -> str:
    """Compute a hash chain linking this record to the previous one."""
    payload = report_json + (previous_hash or "")
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

_GDPR_CACHE_PREFIX = "gdpr:job:"


def _cache_key(request_id: str) -> str:
    return f"{_GDPR_CACHE_PREFIX}{request_id}"


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------

def _dict_to_report(data: dict) -> DeletionReport:
    """Hydrate a DeletionReport from its serialized dict form."""
    from .deletion import LayerDeletionResult  # local to avoid circular import

    report = DeletionReport(
        tenant_id=data["tenant_id"],
        request_id=data["request_id"],
        initiated_by=data["initiated_by"],
        initiated_at=datetime.fromisoformat(data["initiated_at"]),
    )
    report.completed_at = (
        datetime.fromisoformat(data["completed_at"])
        if data.get("completed_at")
        else None
    )
    report.status = DeletionStatus(data.get("status", "in_progress"))
    report.total_records_deleted = data.get("total_records_deleted", 0)
    report.verification_passed = data.get("verification_passed")
    report.audit_log_hash = data.get("audit_log_hash")
    report.error_summary = data.get("error_summary")

    for layer_data in data.get("layers", []):
        report.add_result(
            LayerDeletionResult(
                layer=layer_data["layer"],
                records_deleted=layer_data["records_deleted"],
                tables_affected=layer_data.get("tables_affected", []),
                duration_ms=layer_data["duration_ms"],
                status=layer_data["status"],
                error=layer_data.get("error"),
            )
        )
    return report
