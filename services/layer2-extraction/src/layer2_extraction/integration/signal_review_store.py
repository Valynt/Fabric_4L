from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class SignalReviewStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewedSignalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    account_id: str
    value_pack_id: str
    extraction_job_id: str
    signal_type: str
    source_text: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_links: list[str] = Field(default_factory=list)
    review_status: SignalReviewStatus = SignalReviewStatus.PENDING_REVIEW
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None


class InMemorySignalReviewStore:
    def __init__(self) -> None:
        self._records: dict[str, ReviewedSignalRecord] = {}

    async def enqueue(self, record: ReviewedSignalRecord) -> ReviewedSignalRecord:
        self._records[record.review_id] = record
        return record

    async def get(self, review_id: str, *, tenant_id: str) -> ReviewedSignalRecord:
        record = self._records[review_id]
        if record.tenant_id != tenant_id:
            raise KeyError(review_id)
        return record

    async def transition(
        self,
        review_id: str,
        *,
        tenant_id: str,
        status: SignalReviewStatus,
        reviewed_by: str,
    ) -> ReviewedSignalRecord:
        record = await self.get(review_id, tenant_id=tenant_id)
        if record.review_status is not SignalReviewStatus.PENDING_REVIEW:
            raise ValueError("Review state transition is only allowed from pending_review")
        updated = record.model_copy(
            update={
                "review_status": status,
                "reviewed_by": reviewed_by,
                "reviewed_at": datetime.now(UTC),
            }
        )
        self._records[review_id] = updated
        return updated

    async def list_pending(self, *, tenant_id: str) -> list[ReviewedSignalRecord]:
        return [
            record
            for record in self._records.values()
            if record.tenant_id == tenant_id and record.review_status is SignalReviewStatus.PENDING_REVIEW
        ]


_signal_review_store = InMemorySignalReviewStore()


def build_signal_review_store() -> InMemorySignalReviewStore:
    return _signal_review_store
