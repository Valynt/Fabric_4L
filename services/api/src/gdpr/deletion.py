"""
Right-to-be-forgotten implementation for Fabric 4L.

Implements GDPR Article 17 (Right to erasure) and CCPA Section 1798.105
(Deletion request) for complete tenant data removal across all 6 processing
layers. All operations produce an immutable, append-only audit trail suitable
for regulatory inspection.

Design principles:
1. Immutability — deletion audit logs are cryptographically hashed and stored
   in an append-only structure.
2. Verification — every deletion is followed by a zero-count verification pass
   to confirm data is actually gone.
3. Resilience — partial failures are captured per-layer; the overall job does
   not abort unless the system safety check fires.
4. Idempotency — re-running deletion for the same tenant is safe and yields
   the same (already-deleted) result set.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.audit import append_audit_record
from value_fabric.db import get_db_session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# PostgreSQL tenant isolation column name used for RLS
TENANT_COL = "tenant_id"

# Maximum time a single layer deletion is allowed to run (seconds)
LAYER_TIMEOUT_SECONDS = 300

# Tables per layer (defined centrally to support verification pass)
LAYER_TABLES: Dict[str, List[str]] = {
    "L1": ["documents", "document_chunks", "raw_uploads", "ingestion_jobs"],
    "L2": ["entities", "entity_relations", "extraction_jobs", "nlp_outputs"],
    "L3": ["knowledge_nodes", "knowledge_edges", "vector_embeddings", "graph_snapshots"],
    "L4": ["workflow_states", "workflow_checkpoints", "agent_runs", "step_logs"],
    "L5": ["ground_truth_records", "annotations", "evaluation_sets", "label_batches"],
    "L6": ["benchmark_results", "benchmark_runs", "comparison_pairs", "leaderboard_entries"],
}

# Capture the trusted catalog at import time so later mutations of LAYER_TABLES
# cannot expand the set of identifiers permitted in SQL statements.
_KNOWN_TABLES = frozenset(table for tables in LAYER_TABLES.values() for table in tables)
_KNOWN_COLUMNS = frozenset({TENANT_COL})
_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Safe-guard: refuse to delete if tenant has > MAX_RECORDS records
# (prevents accidental mass deletion of large tenants without manual override)
MAX_RECORDS_SAFETY_LIMIT = 10_000_000


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DeletionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class LayerStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LayerDeletionResult:
    """
    Immutable record of deletion work performed against a single layer.

    The frozen=True flag makes instances hashable and protects against
    accidental mutation after the record is committed to the audit log.
    """
    layer: str  # L1-L6
    records_deleted: int
    tables_affected: List[str]
    duration_ms: int
    status: str  # success | partial | failed | skipped
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "records_deleted": self.records_deleted,
            "tables_affected": list(self.tables_affected),
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
        }

    def hash(self) -> str:
        """Return a SHA-256 hash of the canonical JSON representation."""
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class DeletionReport:
    """
    Mutable accumulator for a full tenant-deletion job. Once the job
    completes the report is sealed (via seal()) and written to the audit
    log as an immutable snapshot.
    """
    tenant_id: str
    request_id: str
    initiated_by: str
    initiated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    results: List[LayerDeletionResult] = field(default_factory=list)
    status: DeletionStatus = DeletionStatus.IN_PROGRESS
    total_records_deleted: int = 0
    verification_passed: bool = False
    audit_log_hash: Optional[str] = None
    error_summary: Optional[str] = None

    # Internal mutable tracking
    _sealed: bool = field(default=False, repr=False)

    def add_result(self, result: LayerDeletionResult) -> None:
        if self._sealed:
            raise RuntimeError("Cannot add results to a sealed DeletionReport")
        self.results.append(result)
        self.total_records_deleted += result.records_deleted

    def seal(self) -> None:
        """Freeze the report and compute summary fields."""
        self.completed_at = datetime.now(timezone.utc)
        if any(r.status == LayerStatus.FAILED for r in self.results):
            self.status = DeletionStatus.FAILED
        elif any(r.status == LayerStatus.PARTIAL for r in self.results):
            self.status = DeletionStatus.PARTIAL
        else:
            self.status = DeletionStatus.COMPLETED
        self._sealed = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "request_id": self.request_id,
            "initiated_by": self.initiated_by,
            "initiated_at": self.initiated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": [r.to_dict() for r in self.results],
            "status": self.status.value,
            "total_records_deleted": self.total_records_deleted,
            "verification_passed": self.verification_passed,
            "audit_log_hash": self.audit_log_hash,
            "error_summary": self.error_summary,
        }

    def compute_hash(self) -> str:
        """Compute a cryptographic digest of the sealed report."""
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Layer deletion implementations
# ---------------------------------------------------------------------------

class _LayerDeleter:
    """Internal dispatcher holding deletion logic for each layer."""

    @staticmethod
    async def _delete_from_tables(
        db: AsyncSession,
        tenant_id: str,
        tables: List[str],
        layer_name: str,
    ) -> LayerDeletionResult:
        """
        Generic deletion routine using tenant_id column.

        Uses parameterized SQL to avoid injection. Returns a
        LayerDeletionResult capturing counts and timing.
        """
        start_ms = int(time.time() * 1000)
        total_deleted = 0
        tables_affected: List[str] = []
        errors: List[str] = []

        for table in tables:
            try:
                quoted_table = _quote_sql_identifier(table, allowed=_KNOWN_TABLES)
                quoted_tenant_col = _quote_sql_identifier(
                    TENANT_COL, allowed=_KNOWN_COLUMNS
                )

                stmt = text(
                    f"""
                    DELETE FROM {quoted_table}
                    WHERE {quoted_tenant_col} = :tenant_id
                    RETURNING id
                    """
                )
                result = await db.execute(stmt, {"tenant_id": tenant_id})
                deleted_ids = result.scalars().all()
                count = len(deleted_ids)

                if count > 0:
                    tables_affected.append(table)
                    total_deleted += count

                logger.info(
                    "Layer %s: deleted %d rows from %s for tenant %s",
                    layer_name, count, table, tenant_id,
                )

            except Exception as exc:  # pragma: no cover
                logger.exception(
                    "Layer %s: error deleting from %s for tenant %s: %s",
                    layer_name, table, tenant_id, exc,
                )
                errors.append(f"{table}: {exc}")

        duration_ms = int(time.time() * 1000) - start_ms

        if errors and tables_affected:
            status = LayerStatus.PARTIAL
        elif errors:
            status = LayerStatus.FAILED
        else:
            status = LayerStatus.SUCCESS

        return LayerDeletionResult(
            layer=layer_name,
            records_deleted=total_deleted,
            tables_affected=tables_affected,
            duration_ms=duration_ms,
            status=status.value,
            error="; ".join(errors) if errors else None,
        )

    @classmethod
    async def L1(cls, db: AsyncSession, tenant_id: str) -> LayerDeletionResult:
        """L1 — Raw documents, chunks, uploads, ingestion jobs."""
        return await cls._delete_from_tables(db, tenant_id, LAYER_TABLES["L1"], "L1")

    @classmethod
    async def L2(cls, db: AsyncSession, tenant_id: str) -> LayerDeletionResult:
        """L2 — Extracted entities, relations, NLP outputs."""
        return await cls._delete_from_tables(db, tenant_id, LAYER_TABLES["L2"], "L2")

    @classmethod
    async def L3(cls, db: AsyncSession, tenant_id: str) -> LayerDeletionResult:
        """L3 — Knowledge graph nodes, edges, vector embeddings, snapshots."""
        # Vector embeddings may have trigger-based cascading deletions.
        # We delete knowledge_edges first to avoid FK violations, then nodes.
        ordered = ["knowledge_edges", "vector_embeddings", "graph_snapshots", "knowledge_nodes"]
        return await cls._delete_from_tables(db, tenant_id, ordered, "L3")

    @classmethod
    async def L4(cls, db: AsyncSession, tenant_id: str) -> LayerDeletionResult:
        """L4 — Workflow state, checkpoints, agent runs, step logs."""
        # Checkpoints reference workflow_states FK; delete in dependency order
        ordered = ["step_logs", "workflow_checkpoints", "agent_runs", "workflow_states"]
        return await cls._delete_from_tables(db, tenant_id, ordered, "L4")

    @classmethod
    async def L5(cls, db: AsyncSession, tenant_id: str) -> LayerDeletionResult:
        """L5 — Ground truth records, annotations, evaluation sets, label batches."""
        return await cls._delete_from_tables(db, tenant_id, LAYER_TABLES["L5"], "L5")

    @classmethod
    async def L6(cls, db: AsyncSession, tenant_id: str) -> LayerDeletionResult:
        """L6 — Benchmark results, runs, comparison pairs, leaderboard entries."""
        return await cls._delete_from_tables(db, tenant_id, LAYER_TABLES["L6"], "L6")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def delete_tenant_data(
    tenant_id: str,
    request_id: str,
    initiated_by: str,
    db: AsyncSession | None = None,
) -> DeletionReport:
    """
    Orchestrate complete tenant data deletion across all 6 layers.

    Steps:
      1. Safety check — ensure tenant record count is below threshold.
      2. Delete L1 → L6 in sequence (lower layers may depend on upper).
      3. Verification pass — confirm zero records remain per table.
      4. Seal report and write immutable audit log.

    Args:
        tenant_id: The tenant identifier to erase (RLS-enforced).
        request_id: Unique idempotency key for this deletion request.
        initiated_by: User/admin identifier who triggered deletion.
        db: Optional existing database session (for transaction sharing).

    Returns:
        DeletionReport: Immutable audit trail of all deleted data.
    """
    report = DeletionReport(
        tenant_id=tenant_id,
        request_id=request_id,
        initiated_by=initiated_by,
    )

    own_session = db is None
    db = db or await anext(get_db_session())

    try:
        # Step 1 — Safety guard
        await _safety_check(db, tenant_id)

        # Step 2 — Layer deletions in dependency order
        for layer_fn in (_LayerDeleter.L1, _LayerDeleter.L2, _LayerDeleter.L3,
                         _LayerDeleter.L4, _LayerDeleter.L5, _LayerDeleter.L6):
            result = await layer_fn(db, tenant_id)
            report.add_result(result)

        # Step 3 — Verification pass (data actually gone)
        await _verify_all_deleted(db, tenant_id, report)

        # Step 4 — Seal and audit
        report.seal()
        await _write_deletion_audit_log(report)

    except Exception as exc:
        logger.critical(
            "Tenant deletion failed for %s: %s", tenant_id, exc, exc_info=True
        )
        report.status = DeletionStatus.FAILED
        report.error_summary = str(exc)
        report.completed_at = datetime.now(timezone.utc)
        # Still write audit log — failure itself must be recorded
        await _write_deletion_audit_log(report)
        raise DeletionError(f"Deletion failed for tenant {tenant_id}: {exc}") from exc

    finally:
        if own_session:
            await db.close()

    return report


# ---------------------------------------------------------------------------
# Safety & verification
# ---------------------------------------------------------------------------

async def _safety_check(db: AsyncSession, tenant_id: str) -> None:
    """
    Refuse to proceed if tenant has more records than the safety limit.
    This prevents runaway deletions triggered by automation bugs.
    """
    total = 0
    for tables in LAYER_TABLES.values():
        for table in tables:
            quoted_table = _quote_sql_identifier(table, allowed=_KNOWN_TABLES)
            quoted_tenant_col = _quote_sql_identifier(TENANT_COL, allowed=_KNOWN_COLUMNS)
            stmt = text(
                f"SELECT COUNT(*) FROM {quoted_table} "
                f"WHERE {quoted_tenant_col} = :tenant_id"
            )
            result = await db.execute(stmt, {"tenant_id": tenant_id})
            total += result.scalar() or 0

    if total > MAX_RECORDS_SAFETY_LIMIT:
        raise SafetyLimitExceeded(
            f"Tenant {tenant_id} has {total} records (limit: {MAX_RECORDS_SAFETY_LIMIT}). "
            "Manual override required."
        )

    logger.info("Safety check passed for tenant %s: %d records found", tenant_id, total)


async def _verify_all_deleted(
    db: AsyncSession, tenant_id: str, report: DeletionReport
) -> None:
    """
    Confirm zero records remain for the tenant across all known tables.
    Any remaining records are logged as a critical inconsistency.
    """
    remaining: Dict[str, int] = {}
    for tables in LAYER_TABLES.values():
        for table in tables:
            quoted_table = _quote_sql_identifier(table, allowed=_KNOWN_TABLES)
            quoted_tenant_col = _quote_sql_identifier(TENANT_COL, allowed=_KNOWN_COLUMNS)
            stmt = text(
                f"SELECT COUNT(*) FROM {quoted_table} "
                f"WHERE {quoted_tenant_col} = :tenant_id"
            )
            result = await db.execute(stmt, {"tenant_id": tenant_id})
            count = result.scalar() or 0
            if count > 0:
                remaining[table] = count

    if remaining:
        summary = ", ".join(f"{t}: {c}" for t, c in remaining.items())
        logger.critical(
            "VERIFICATION FAILED for tenant %s — remaining rows: %s",
            tenant_id, summary,
        )
        report.verification_passed = False
        report.error_summary = f"Verification failed: {summary}"
    else:
        report.verification_passed = True
        logger.info("Verification passed for tenant %s", tenant_id)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

async def _write_deletion_audit_log(report: DeletionReport) -> None:
    """
    Write an immutable audit log entry for the deletion report.

    The record is written to:
      1. Append-only audit log table (tamper-evident via hash chain).
      2. Structured JSON stdout for log aggregation (Splunk/Datadog).
    """
    report.audit_log_hash = report.compute_hash()

    record = {
        "event_type": "gdpr.tenant_data_deleted",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": report.tenant_id,
        "request_id": report.request_id,
        "initiated_by": report.initiated_by,
        "status": report.status.value,
        "total_records_deleted": report.total_records_deleted,
        "verification_passed": report.verification_passed,
        "audit_hash": report.audit_log_hash,
        "layers": [r.to_dict() for r in report.results],
    }

    # 1. Database append-only log
    await append_audit_record(record)

    # 2. Structured stdout for external log aggregation
    print(json.dumps(record, sort_keys=True, default=str))

    logger.info(
        "Deletion audit log written for tenant %s (request %s, hash %s)",
        report.tenant_id, report.request_id, report.audit_log_hash,
    )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DeletionError(Exception):
    """Raised when the deletion orchestrator encounters a fatal error."""


class SafetyLimitExceeded(Exception):
    """Raised when the tenant record count exceeds the safety threshold."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quote_sql_identifier(identifier: str, *, allowed: frozenset[str]) -> str:
    """Validate and quote a trusted SQL identifier, rejecting catalog drift."""
    if identifier not in allowed or _SQL_IDENTIFIER_RE.fullmatch(identifier) is None:
        message = f"Unsafe SQL identifier: {identifier!r}"
        raise ValueError(message)
    return f'"{identifier}"'


# Convenience re-exports for layer modules that may provide custom overrides
layer1 = _LayerDeleter
layer2 = _LayerDeleter
layer3 = _LayerDeleter
layer4 = _LayerDeleter
layer5 = _LayerDeleter
layer6 = _LayerDeleter
