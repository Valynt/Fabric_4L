"""Lifecycle operations for operational signals."""

from __future__ import annotations

from datetime import UTC, datetime

from layer2_extraction.models.signal_lifecycle import (
    OperationalSignalLifecycleRecord,
    SignalLifecycleActor,
    SignalLifecycleMetadata,
    SignalLifecycleStatus,
)


class InvalidLifecycleTransitionError(ValueError):
    """Raised when lifecycle transition is not allowed."""


class SignalLifecycleService:
    """In-memory lifecycle service with tenant/account enforcement."""

    def __init__(self) -> None:
        self._signals: dict[str, OperationalSignalLifecycleRecord] = {}

    def create_signal(self, signal_id: str, tenant_id: str, actor: SignalLifecycleActor) -> OperationalSignalLifecycleRecord:
        now = datetime.now(UTC)
        record = OperationalSignalLifecycleRecord(
            signal_id=signal_id,
            tenant_id=tenant_id,
            account_id=actor.account_id,
            lifecycle=SignalLifecycleMetadata(
                created_by=actor,
                updated_by=actor,
                created_at=now,
                updated_at=now,
            ),
        )
        self._signals[signal_id] = record
        return record

    def get_signal(self, signal_id: str, tenant_id: str, account_id: str) -> OperationalSignalLifecycleRecord:
        record = self._signals[signal_id]
        if record.tenant_id != tenant_id or record.account_id != account_id:
            raise KeyError(signal_id)
        return record

    def supersede_signal(self, source_id: str, replacement_id: str, tenant_id: str, actor: SignalLifecycleActor) -> OperationalSignalLifecycleRecord:
        source = self.get_signal(source_id, tenant_id, actor.account_id)
        replacement = self.get_signal(replacement_id, tenant_id, actor.account_id)
        if source.status != SignalLifecycleStatus.ACTIVE:
            raise InvalidLifecycleTransitionError("Only active signals can be superseded")
        source.status = SignalLifecycleStatus.SUPERSEDED
        source.lineage.superseded_by.append(replacement.signal_id)
        replacement.lineage.supersedes.append(source.signal_id)
        source.lifecycle.updated_by = actor
        source.lifecycle.updated_at = datetime.now(UTC)
        replacement.lifecycle.updated_by = actor
        replacement.lifecycle.updated_at = datetime.now(UTC)
        return source

    def merge_signal(self, source_id: str, canonical_id: str, tenant_id: str, actor: SignalLifecycleActor) -> OperationalSignalLifecycleRecord:
        source = self.get_signal(source_id, tenant_id, actor.account_id)
        canonical = self.get_signal(canonical_id, tenant_id, actor.account_id)
        if source.status != SignalLifecycleStatus.ACTIVE:
            raise InvalidLifecycleTransitionError("Only active signals can be merged")
        source.status = SignalLifecycleStatus.MERGED
        source.lineage.merged_into = canonical.signal_id
        canonical.lineage.supersedes.append(source.signal_id)
        source.lifecycle.updated_by = actor
        source.lifecycle.updated_at = datetime.now(UTC)
        canonical.lifecycle.updated_by = actor
        canonical.lifecycle.updated_at = datetime.now(UTC)
        return source
