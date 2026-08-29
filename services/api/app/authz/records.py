"""Durable decision records and a durable-fail-closed outbox.

Every decision produced by the authorization facade is recorded. Protected
decisions for the "critical four" transitions are written through an outbox:
if the exporter fails, the record is retained and retried rather than dropped.
This module uses only the standard library so it adds no runtime dependency.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.authz.schemas import AuthzDecision

MAX_OUTBOX_ATTEMPTS = 8


@dataclass(frozen=True)
class DecisionRecord:
    """A persisted authorization decision."""

    decision_id: str
    tenant_id: str
    principal_id: str
    principal_type: str
    action: str
    resource_type: str
    resource_id: str
    allowed: bool
    reason_codes: tuple[str, ...]
    deny_code: str | None
    obligations: tuple[dict[str, Any], ...]
    policy_version: str
    input_fingerprint: str
    revisions: tuple[dict[str, Any], ...] = ()
    recorded_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def from_decision(
        cls,
        *,
        decision: AuthzDecision,
        tenant_id: str,
        principal_id: str,
        principal_type: str,
        resource_type: str,
        resource_id: str,
        action: str = "",
        revisions: tuple[dict[str, Any], ...] = (),
    ) -> DecisionRecord:
        return cls(
                decision_id=decision.decision_id,
                tenant_id=tenant_id,
                principal_id=principal_id,
                principal_type=principal_type,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
            allowed=decision.allow,
            reason_codes=tuple(sorted(code.value for code in decision.reason_codes)),
            deny_code=decision.deny_code.value if decision.deny_code else None,
            obligations=tuple(ob.model_dump(mode="json") for ob in decision.obligations),
            policy_version=decision.policy_version,
            input_fingerprint=decision.input_fingerprint,
            revisions=revisions,
            recorded_at=decision.evaluated_at.isoformat(),
        )

    def to_row(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "tenant_id": self.tenant_id,
            "principal_id": self.principal_id,
            "principal_type": self.principal_type,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "allowed": int(self.allowed),
            "reason_codes": json.dumps(list(self.reason_codes)),
            "deny_code": self.deny_code,
            "obligations": json.dumps(list(self.obligations)),
            "policy_version": self.policy_version,
            "input_fingerprint": self.input_fingerprint,
            "revisions": json.dumps(list(self.revisions)),
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> DecisionRecord:
        return cls(
            decision_id=row["decision_id"],
            tenant_id=row["tenant_id"],
            principal_id=row["principal_id"],
            principal_type=row["principal_type"],
            action=row.get("action", ""),
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            allowed=bool(row["allowed"]),
            reason_codes=tuple(json.loads(row["reason_codes"])),
            deny_code=row.get("deny_code"),
            obligations=tuple(json.loads(row["obligations"])) if row.get("obligations") else (),
            policy_version=row["policy_version"],
            input_fingerprint=row["input_fingerprint"],
            revisions=tuple(json.loads(row["revisions"])) if row.get("revisions") else (),
            recorded_at=row["recorded_at"],
        )


class DecisionRecordStore:
    """Persist decision records.

    Defaults to an in-memory store (suitable for tests). When ``path`` is given,
    persists to an embedded SQLite database (stdlib only). All writes are
    tenant-scoped; reads are filtered by tenant.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._lock = threading.Lock()
        self._memory: list[DecisionRecord] = []
        self._path = Path(path) if path is not None else None
        self._conn: sqlite3.Connection | None = None
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS authz_decisions (
                    decision_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    principal_id TEXT NOT NULL,
                    principal_type TEXT NOT NULL,
                    action TEXT NOT NULL DEFAULT '',
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    allowed INTEGER NOT NULL,
                    reason_codes TEXT NOT NULL,
                    deny_code TEXT,
                    obligations TEXT NOT NULL DEFAULT '[]',
                    policy_version TEXT NOT NULL,
                    input_fingerprint TEXT NOT NULL,
                    revisions TEXT NOT NULL DEFAULT '[]',
                    recorded_at TEXT NOT NULL
                )
                """
            )
            self._conn.commit()

    def append(self, record: DecisionRecord) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO authz_decisions (
                        decision_id, tenant_id, principal_id, principal_type, action,
                        resource_type, resource_id, allowed, reason_codes, deny_code,
                        obligations, policy_version, input_fingerprint, revisions, recorded_at
                    ) VALUES (
                        :decision_id, :tenant_id, :principal_id, :principal_type, :action,
                        :resource_type, :resource_id, :allowed, :reason_codes, :deny_code,
                        :obligations, :policy_version, :input_fingerprint, :revisions, :recorded_at
                    )
                    """,
                    record.to_row(),
                )
                self._conn.commit()
                return
            self._memory.append(record)

    def list_by_tenant(self, tenant_id: str, *, limit: int = 500) -> list[DecisionRecord]:
        with self._lock:
            records: list[DecisionRecord] = []
            if self._conn is not None:
                rows = self._conn.execute(
                    "SELECT * FROM authz_decisions WHERE tenant_id = ? ORDER BY recorded_at DESC LIMIT ?",
                    (tenant_id, limit),
                ).fetchall()
                cols = [c[0] for c in self._conn.execute("SELECT * FROM authz_decisions LIMIT 0").description]
                records = [DecisionRecord.from_row(dict(zip(cols, row))) for row in rows]
            else:
                records = [
                    r for r in reversed(self._memory) if r.tenant_id == tenant_id
                ][:limit]
            return records

    def get_by_decision_id(self, decision_id: str) -> DecisionRecord | None:
        with self._lock:
            if self._conn is not None:
                row = self._conn.execute(
                    "SELECT * FROM authz_decisions WHERE decision_id = ?", (decision_id,)
                ).fetchone()
                if row is None:
                    return None
                cols = [c[0] for c in self._conn.execute("SELECT * FROM authz_decisions LIMIT 0").description]
                return DecisionRecord.from_row(dict(zip(cols, row)))
            return next((r for r in self._memory if r.decision_id == decision_id), None)

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


@dataclass
class OutboxEntry:
    """A decision awaiting export to a durable sink."""

    record: DecisionRecord
    attempts: int = 0
    last_error: str | None = None


class DecisionOutbox:
    """Durable-fail-closed outbox for protected decision records.

    ``enqueue`` never raises for a failing exporter; the entry is retained and
    retried. After ``MAX_OUTBOX_ATTEMPTS`` it is marked failed and still kept in
    ``failed`` so a decision is never silently dropped.
    """

    def __init__(self, store: DecisionRecordStore, *, export: Any = None) -> None:
        self._store = store
        self._export = export
        self._pending: list[OutboxEntry] = []
        self._failed: list[OutboxEntry] = []
        self._lock = threading.Lock()

    def enqueue(self, decision: AuthzDecision, *, tenant_id: str, **meta: Any) -> DecisionRecord:
        record = DecisionRecord.from_decision(
            decision=decision,
            tenant_id=tenant_id,
            principal_id=meta.get("principal_id", ""),
            principal_type=meta.get("principal_type", "human"),
            resource_type=meta.get("resource_type", ""),
            resource_id=meta.get("resource_id", ""),
            action=meta.get("action", ""),
            revisions=tuple(meta.get("revisions", ())),
        )
        self._store.append(record)
        entry = OutboxEntry(record=record)
        with self._lock:
            self._pending.append(entry)
        self.flush_once()
        return record

    def flush_once(self) -> None:
        """Attempt to export all pending entries; retain on failure."""
        if self._export is None:
            return
        with self._lock:
            remaining: list[OutboxEntry] = []
            for entry in self._pending:
                try:
                    self._export(entry.record.to_row())
                except Exception as exc:  # pragma: no cover - defensive
                    entry.attempts += 1
                    entry.last_error = str(exc)
                    if entry.attempts >= MAX_OUTBOX_ATTEMPTS:
                        self._failed.append(entry)
                    else:
                        remaining.append(entry)
            self._pending = remaining

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def failed_count(self) -> int:
        with self._lock:
            return len(self._failed)

    def pending_decision_ids(self) -> list[str]:
        with self._lock:
            return [e.record.decision_id for e in self._pending]

    def failed_decision_ids(self) -> list[str]:
        with self._lock:
            return [e.record.decision_id for e in self._failed]
