from __future__ import annotations

import os
import sqlite3
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from layer2_extraction.validation.artifact_validator import ArtifactValidationError


class QuarantineRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quarantine_id: str
    job_id: str
    tenant_id: str
    source_url: str
    source_hash: str
    model_version: str
    schema_version: str
    prompt_template_version: str
    prompt_template_hash: str | None = None
    payload_json: str
    validation_errors: list[str] = Field(default_factory=list)
    reason: str = "validation_error"
    review_status: str = "pending_review"
    retry_eligible: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QuarantineStore(ABC):
    @abstractmethod
    async def put(self, record: QuarantineRecord) -> None: ...

    @abstractmethod
    async def get_by_job(self, *, tenant_id: str, job_id: str) -> QuarantineRecord | None: ...

    @abstractmethod
    async def list(self, *, tenant_id: str) -> list[QuarantineRecord]: ...


class InMemoryQuarantineStore(QuarantineStore):
    def __init__(self) -> None:
        self._records: dict[str, QuarantineRecord] = {}

    async def put(self, record: QuarantineRecord) -> None:
        # MANDATORY VALIDATION GATE: Validate quarantine record before persistence
        if not record.tenant_id or not record.tenant_id.strip():
            raise ArtifactValidationError(
                missing_fields=["tenant_id"],
                invalid_fields=[],
            )
        if not record.model_version or not record.model_version.strip():
            raise ArtifactValidationError(
                missing_fields=["model_version"],
                invalid_fields=[],
            )
        if not record.schema_version or not record.schema_version.strip():
            raise ArtifactValidationError(
                missing_fields=["schema_version"],
                invalid_fields=[],
            )
        self._records[record.job_id] = record

    async def get_by_job(self, *, tenant_id: str, job_id: str) -> QuarantineRecord | None:
        record = self._records.get(job_id)
        if record is None or record.tenant_id != tenant_id:
            return None
        return record

    async def list(self, *, tenant_id: str) -> list[QuarantineRecord]:
        return [r for r in self._records.values() if r.tenant_id == tenant_id]


class SqliteQuarantineStore(QuarantineStore):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS extraction_quarantine (
                    quarantine_id TEXT PRIMARY KEY,
                    job_id TEXT UNIQUE NOT NULL,
                    tenant_id TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    prompt_template_version TEXT NOT NULL,
                    prompt_template_hash TEXT,
                    payload_json TEXT NOT NULL,
                    validation_errors_json TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    retry_eligible INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    async def put(self, record: QuarantineRecord) -> None:
        # MANDATORY VALIDATION GATE: Validate quarantine record before persistence
        if not record.tenant_id or not record.tenant_id.strip():
            raise ArtifactValidationError(
                missing_fields=["tenant_id"],
                invalid_fields=[],
            )
        if not record.model_version or not record.model_version.strip():
            raise ArtifactValidationError(
                missing_fields=["model_version"],
                invalid_fields=[],
            )
        if not record.schema_version or not record.schema_version.strip():
            raise ArtifactValidationError(
                missing_fields=["schema_version"],
                invalid_fields=[],
            )
        
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO extraction_quarantine
                (quarantine_id, job_id, tenant_id, source_url, source_hash, model_version, schema_version, prompt_template_version, prompt_template_hash, payload_json,
                 validation_errors_json, reason, review_status, retry_eligible, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.quarantine_id,
                    record.job_id,
                    record.tenant_id,
                    record.source_url,
                    record.source_hash,
                    record.model_version,
                    record.schema_version,
                    record.prompt_template_version,
                    record.prompt_template_hash,
                    record.payload_json,
                    __import__('json').dumps(record.validation_errors),
                    record.reason,
                    record.review_status,
                    1 if record.retry_eligible else 0,
                    record.created_at.isoformat(),
                ),
            )

    async def get_by_job(self, *, tenant_id: str, job_id: str) -> QuarantineRecord | None:
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.execute("SELECT * FROM extraction_quarantine WHERE tenant_id=? AND job_id=?", (tenant_id, job_id))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    async def list(self, *, tenant_id: str) -> list[QuarantineRecord]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute("SELECT * FROM extraction_quarantine WHERE tenant_id=? ORDER BY created_at DESC", (tenant_id,)).fetchall()
        return [self._row_to_record(r) for r in rows]

    def _row_to_record(self, row: tuple) -> QuarantineRecord:
        import json
        return QuarantineRecord(
            quarantine_id=row[0], job_id=row[1], tenant_id=row[2], source_url=row[3], source_hash=row[4],
            model_version=row[5], schema_version=row[6], prompt_template_version=row[7], prompt_template_hash=row[8],
            payload_json=row[9], validation_errors=json.loads(row[10]),
            reason=row[11], review_status=row[12], retry_eligible=bool(row[13]), created_at=datetime.fromisoformat(row[14])
        )


def build_quarantine_store() -> QuarantineStore:
    path = os.getenv("L2_QUARANTINE_SQLITE_PATH")
    if path:
        return SqliteQuarantineStore(path)
    return InMemoryQuarantineStore()
