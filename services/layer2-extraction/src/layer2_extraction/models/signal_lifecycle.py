"""Signal lifecycle and lineage models for Layer 2 operational signals."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SignalLifecycleStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    MERGED = "merged"


class SignalLifecycleActor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)


class SignalLifecycleMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created_by: SignalLifecycleActor
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_by: SignalLifecycleActor
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SignalLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supersedes: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list)
    merged_into: str | None = None


class OperationalSignalLifecycleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    status: SignalLifecycleStatus = SignalLifecycleStatus.ACTIVE
    lineage: SignalLineage = Field(default_factory=SignalLineage)
    lifecycle: SignalLifecycleMetadata
