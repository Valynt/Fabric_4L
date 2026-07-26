"""
Validation State Machine for TruthObject lifecycle.

Implements the target truth-governance taxonomy:
  proposed → validated | disputed | rejected
  validated → disputed | superseded | expired
  disputed → validated | rejected
  rejected → (terminal)
  superseded → (terminal)
  expired → (terminal)

Rules
-----
PROPOSED → VALIDATED
  • confidence ≥ settings.min_confidence_for_validated
  • at least min_sources_for_validated distinct TruthSource records

PROPOSED → DISPUTED
  • can be triggered by any actor
  • requires dispute_reason

PROPOSED → REJECTED
  • human actor only
  • requires rejection_reason

VALIDATED → DISPUTED
  • can be triggered by any actor
  • requires dispute_reason

VALIDATED → SUPERSEDED
  • requires superseded_by_id (reference to newer TruthObject)

VALIDATED → EXPIRED
  • triggered by freshness monitor when expires_at is exceeded

DISPUTED → VALIDATED
  • human actor only
  • dispute is resolved

DISPUTED → REJECTED
  • human actor only
  • dispute is rejected
"""

import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from metrics.prometheus_metrics import get_metrics

from ..config import get_settings
from ..models.truth_object import (
    DisputeReason,
    MaturityHistory,
    MaturityLevel,
    RejectionReason,
    TruthObject,
    TruthSource,
    TruthStatus,
    ValidationEvent,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class InvalidTransitionError(ValueError):
    """Raised when a requested state transition is not permitted."""

    pass


class InsufficientEvidenceError(ValueError):
    """Raised when the evidence requirements for a transition are not met."""

    pass


class TransitionConflictError(ValueError):
    """Raised when a concurrent transition already changed the status."""

    pass


# ---------------------------------------------------------------------------
# Allowed transitions map
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS: dict[TruthStatus, set[TruthStatus]] = {
    TruthStatus.PROPOSED: {TruthStatus.VALIDATED, TruthStatus.DISPUTED, TruthStatus.REJECTED},
    TruthStatus.VALIDATED: {TruthStatus.DISPUTED, TruthStatus.SUPERSEDED, TruthStatus.EXPIRED},
    TruthStatus.DISPUTED: {TruthStatus.VALIDATED, TruthStatus.REJECTED, TruthStatus.EXPIRED},
    TruthStatus.REJECTED: set(),
    TruthStatus.SUPERSEDED: set(),
    TruthStatus.EXPIRED: set(),
}

# Status → maturity level mapping (minimum maturity for a given status)
STATUS_TO_MATURITY: dict[TruthStatus, MaturityLevel] = {
    TruthStatus.PROPOSED: MaturityLevel.EXTRACTED,
    TruthStatus.VALIDATED: MaturityLevel.APPROVED,
    TruthStatus.DISPUTED: MaturityLevel.EXTRACTED,
    TruthStatus.REJECTED: MaturityLevel.EXTRACTED,
    TruthStatus.SUPERSEDED: MaturityLevel.APPROVED,
    TruthStatus.EXPIRED: MaturityLevel.APPROVED,
}


# ---------------------------------------------------------------------------
# State machine service
# ---------------------------------------------------------------------------


class ValidationStateMachine:
    """
    Encapsulates all state transition logic for TruthObject validation.

    All public methods accept an open AsyncSession and commit nothing —
    callers are responsible for committing the session. This keeps the
    service testable without needing a real database.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Public transition methods
    # ------------------------------------------------------------------

    async def validate(
        self,
        db: AsyncSession,
        truth_object: TruthObject,
        validated_by: str,
        notes: str | None = None,
    ) -> TruthObject:
        """
        Advance a TruthObject from PROPOSED → VALIDATED.

        Requirements:
          - Current status must be PROPOSED
          - validated_by must be a non-empty string (human reviewer)
          - confidence ≥ min_confidence_for_validated
          - at least min_sources_for_validated distinct sources
        """
        self._assert_transition(truth_object, TruthStatus.VALIDATED)

        if not validated_by or not validated_by.strip():
            raise ValueError("validated_by is required for VALIDATED transition.")

        distinct_count = await self._count_distinct_sources(db, truth_object.id)
        if distinct_count < self._settings.min_sources_for_validated:
            raise InsufficientEvidenceError(
                f"Cannot advance to VALIDATED: need "
                f"{self._settings.min_sources_for_validated} distinct sources, "
                f"found {distinct_count}."
            )
        if truth_object.confidence < self._settings.min_confidence_for_validated:
            raise InsufficientEvidenceError(
                f"Cannot advance to VALIDATED: confidence {truth_object.confidence:.2f} "
                f"is below threshold {self._settings.min_confidence_for_validated:.2f}."
            )

        truth_object.validated_by = validated_by
        truth_object.validated_at = datetime.now(UTC)
        truth_object.validation_notes = notes

        return await self._apply_transition(
            db=db,
            truth_object=truth_object,
            new_status=TruthStatus.VALIDATED,
            actor=validated_by,
            actor_type="human",
            source_count=distinct_count,
            notes=notes,
        )

    async def dispute(
        self,
        db: AsyncSession,
        truth_object: TruthObject,
        reason: DisputeReason,
        disputed_by: str,
        notes: str | None = None,
    ) -> TruthObject:
        """
        Mark a TruthObject as DISPUTED from any non-DISPUTED status.

        Requirements:
          - Current status must not already be DISPUTED
          - reason and disputed_by are required
        """
        self._assert_transition(truth_object, TruthStatus.DISPUTED)

        if not reason:
            raise ValueError("reason is required for DISPUTED transition.")
        if not disputed_by or not disputed_by.strip():
            raise ValueError("disputed_by is required for DISPUTED transition.")

        source_count = await self._count_sources(db, truth_object.id)

        truth_object.dispute_reason = reason.value
        truth_object.dispute_notes = notes
        truth_object.disputed_by = disputed_by
        truth_object.disputed_at = datetime.now(UTC)

        return await self._apply_transition(
            db=db,
            truth_object=truth_object,
            new_status=TruthStatus.DISPUTED,
            actor=disputed_by,
            actor_type="human",
            source_count=source_count,
            notes=notes,
        )

    async def resolve_dispute(
        self,
        db: AsyncSession,
        truth_object: TruthObject,
        resolved_by: str,
        notes: str | None = None,
    ) -> TruthObject:
        """
        Revert a DISPUTED TruthObject back to VALIDATED after resolution.

        Requirements:
          - Current status must be DISPUTED
          - resolved_by is required (human actor)
        """
        self._assert_transition(truth_object, TruthStatus.VALIDATED)

        source_count = await self._count_sources(db, truth_object.id)

        # Clear dispute fields
        truth_object.dispute_reason = None
        truth_object.dispute_notes = None
        truth_object.disputed_by = None
        truth_object.disputed_at = None

        return await self._apply_transition(
            db=db,
            truth_object=truth_object,
            new_status=TruthStatus.VALIDATED,
            actor=resolved_by,
            actor_type="human",
            source_count=source_count,
            notes=notes or "Dispute resolved.",
        )

    async def reject(
        self,
        db: AsyncSession,
        truth_object: TruthObject,
        reason: RejectionReason,
        rejected_by: str,
        notes: str | None = None,
    ) -> TruthObject:
        """
        Mark a TruthObject as REJECTED.

        Requirements:
          - Current status must be PROPOSED or DISPUTED
          - reason and rejected_by are required
          - human actor only
        """
        self._assert_transition(truth_object, TruthStatus.REJECTED)

        if not reason:
            raise ValueError("reason is required for REJECTED transition.")
        if not rejected_by or not rejected_by.strip():
            raise ValueError("rejected_by is required for REJECTED transition.")

        source_count = await self._count_sources(db, truth_object.id)

        truth_object.rejection_reason = reason.value
        truth_object.rejected_by = rejected_by
        truth_object.rejected_at = datetime.now(UTC)

        return await self._apply_transition(
            db=db,
            truth_object=truth_object,
            new_status=TruthStatus.REJECTED,
            actor=rejected_by,
            actor_type="human",
            source_count=source_count,
            notes=notes,
        )

    async def supersede(
        self,
        db: AsyncSession,
        truth_object: TruthObject,
        superseded_by_id: UUID,
        superseded_by: str,
        notes: str | None = None,
    ) -> TruthObject:
        """
        Mark a TruthObject as SUPERSEDED by a newer TruthObject.

        Requirements:
          - Current status must be VALIDATED
          - superseded_by_id must reference a valid TruthObject
          - superseded_by is required (human actor)
        """
        self._assert_transition(truth_object, TruthStatus.SUPERSEDED)

        if not superseded_by or not superseded_by.strip():
            raise ValueError("superseded_by is required for SUPERSEDED transition.")

        source_count = await self._count_sources(db, truth_object.id)

        truth_object.superseded_by_id = superseded_by_id
        truth_object.superseded_at = datetime.now(UTC)

        return await self._apply_transition(
            db=db,
            truth_object=truth_object,
            new_status=TruthStatus.SUPERSEDED,
            actor=superseded_by,
            actor_type="human",
            source_count=source_count,
            notes=notes or f"Superseded by {superseded_by_id}.",
        )

    async def expire(
        self,
        db: AsyncSession,
        truth_object: TruthObject,
        notes: str | None = None,
    ) -> TruthObject:
        """
        Mark a TruthObject as EXPIRED (freshness monitor).

        Requirements:
          - Current status must be VALIDATED or DISPUTED
          - System-triggered only
        """
        self._assert_transition(truth_object, TruthStatus.EXPIRED)

        source_count = await self._count_sources(db, truth_object.id)

        # Also set is_stale for backward compatibility with existing queries
        truth_object.is_stale = True

        return await self._apply_transition(
            db=db,
            truth_object=truth_object,
            new_status=TruthStatus.EXPIRED,
            actor="system:freshness_monitor",
            actor_type="system",
            source_count=source_count,
            notes=notes or f"Automatically expired: expired at {truth_object.expires_at.isoformat() if truth_object.expires_at else 'unknown'}",
        )

    async def mark_operationalized(
        self,
        db: AsyncSession,
        truth_object: TruthObject,
        trigger: str,
        triggered_by: str | None = None,
        context: dict | None = None,
    ) -> TruthObject:
        """
        Advance maturity to OPERATIONALIZED (level 5) without changing status.

        Called when a TruthObject is referenced in an ROI model, board deck,
        or other downstream business artefact.

        Requirements:
          - Current status must be VALIDATED
          - Current maturity must be ≥ APPROVED (4)
        """
        if truth_object.status != TruthStatus.VALIDATED.value:
            raise InvalidTransitionError(
                f"Only VALIDATED truth objects can be operationalized, "
                f"current status: {truth_object.status}"
            )
        if truth_object.maturity_level >= MaturityLevel.OPERATIONALIZED.value:
            logger.debug(
                "TruthObject %s already at OPERATIONALIZED maturity", truth_object.id
            )
            return truth_object

        old_maturity = truth_object.maturity_level
        truth_object.maturity_level = MaturityLevel.OPERATIONALIZED.value
        truth_object.updated_at = datetime.now(UTC)

        history = MaturityHistory(
            truth_object_id=truth_object.id,
            tenant_id=truth_object.tenant_id,
            from_level=old_maturity,
            to_level=MaturityLevel.OPERATIONALIZED.value,
            trigger=trigger,
            triggered_by=triggered_by,
            context=context,
        )
        db.add(history)

        logger.info(
            "TruthObject %s advanced to OPERATIONALIZED via %s",
            truth_object.id,
            trigger,
        )
        return truth_object

    # ------------------------------------------------------------------
    # Auto-advance helper (called after source is added)
    # ------------------------------------------------------------------

    async def auto_advance(
        self,
        db: AsyncSession,
        truth_object: TruthObject,
    ) -> TruthObject:
        """
        Attempt automatic advancement based on current evidence.

        Called after a new TruthSource is added. Will advance from
        PROPOSED → VALIDATED if thresholds are met.
        Does NOT auto-validate if auto_advance is disabled.
        """
        if not self._settings.auto_advance_to_validated:
            return truth_object

        current = TruthStatus(truth_object.status)

        if current == TruthStatus.PROPOSED:
            try:
                truth_object = await self.validate(
                    db, truth_object, validated_by="system:auto_advance"
                )
            except (InvalidTransitionError, InsufficientEvidenceError, ValueError) as e:
                logger.debug(
                    "Auto-advance skipped for TruthObject %s: %s",
                    truth_object.id,
                    str(e),
                )

        return truth_object

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assert_transition(
        self,
        truth_object: TruthObject,
        target: TruthStatus,
    ) -> None:
        """Raise InvalidTransitionError if the transition is not permitted."""
        current = TruthStatus(truth_object.status)
        allowed = ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            metrics = get_metrics()
            transition_name = f"{current.value}->{target.value}"
            if metrics:
                metrics.increment_validation_transition_failure(
                    transition=transition_name,
                    reason="invalid_transition",
                )
            logger.warning(
                "validation transition rejected",
                extra={
                    "request_id": None,
                    "tenant_id": str(truth_object.tenant_id),
                    "truth_object_id": str(truth_object.id),
                    "transition": transition_name,
                    "sync_status": "not_attempted",
                },
            )
            raise InvalidTransitionError(
                f"Transition {current.value} → {target.value} is not permitted. "
                f"Allowed from {current.value}: "
                f"{[s.value for s in allowed] or 'none'}."
            )

    async def _count_sources(
        self,
        db: AsyncSession,
        truth_object_id: UUID,
    ) -> int:
        """Count the number of TruthSource records for a given TruthObject."""
        result = await db.execute(
            select(func.count()).where(TruthSource.truth_object_id == truth_object_id)
        )
        return result.scalar() or 0

    async def _count_distinct_sources(
        self,
        db: AsyncSession,
        truth_object_id: UUID,
    ) -> int:
        """Count distinct sources by (source_type, source_url) pairs.

        Two sources are considered distinct if they have different
        source_type values OR different source_url values.
        """
        # Use a subquery to count distinct (source_type, source_url) pairs
        subq = (
            select(
                TruthSource.source_type,
                TruthSource.source_url,
            )
            .where(TruthSource.truth_object_id == truth_object_id)
            .distinct()
            .subquery()
        )
        count_stmt = select(func.count()).select_from(subq)
        result = await db.execute(count_stmt)
        return result.scalar() or 0

    async def _apply_transition(
        self,
        db: AsyncSession,
        truth_object: TruthObject,
        new_status: TruthStatus,
        actor: str,
        actor_type: str,
        source_count: int,
        notes: str | None = None,
    ) -> TruthObject:
        """Apply a validated status transition and record audit events."""
        old_status = truth_object.status
        start = time.perf_counter()
        old_maturity = truth_object.maturity_level
        new_maturity = max(
            old_maturity,
            STATUS_TO_MATURITY[new_status].value,
        )

        now = datetime.now(UTC)

        # Concurrency guard: only transition if the row is still in the expected state.
        # This behaves like optimistic locking using the old status as the expected version.
        result = await db.execute(
            update(TruthObject)
            .where(
                and_(
                    TruthObject.id == truth_object.id,
                    TruthObject.tenant_id == truth_object.tenant_id,
                    TruthObject.status == old_status,
                    TruthObject.deleted_at.is_(None),
                )
            )
            .values(
                status=new_status.value,
                maturity_level=new_maturity,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if (result.rowcount or 0) != 1:
            raise TransitionConflictError(
                "Concurrent transition conflict: truth object state changed before this transition could be applied."
            )

        # Keep ORM object in sync for caller/response usage.
        truth_object.status = new_status.value
        truth_object.maturity_level = new_maturity
        truth_object.updated_at = now

        # Record validation event (immutable audit)
        event = ValidationEvent(
            truth_object_id=truth_object.id,
            tenant_id=truth_object.tenant_id,
            from_status=old_status,
            to_status=new_status.value,
            from_maturity=old_maturity,
            to_maturity=new_maturity,
            actor=actor,
            actor_type=actor_type,
            confidence_at_transition=truth_object.confidence,
            source_count_at_transition=source_count,
            notes=notes,
        )
        db.add(event)

        # Record maturity history if maturity changed
        if new_maturity != old_maturity:
            history = MaturityHistory(
                truth_object_id=truth_object.id,
                tenant_id=truth_object.tenant_id,
                from_level=old_maturity,
                to_level=new_maturity,
                trigger=f"status_transition:{new_status.value}",
                triggered_by=actor,
            )
            db.add(history)

        logger.info(
            "TruthObject %s transitioned %s → %s (maturity %d → %d) by %s",
            truth_object.id,
            old_status,
            new_status.value,
            old_maturity,
            new_maturity,
            actor,
        )
        metrics = get_metrics()
        transition_name = f"{old_status}->{new_status.value}"
        if metrics:
            metrics.increment_validations(
                from_status=old_status,
                to_status=new_status.value,
            )
            metrics.observe_validation_latency(
                transition=transition_name,
                duration=time.perf_counter() - start,
            )
        logger.info(
            "validation transition applied",
            extra={
                "request_id": None,
                "tenant_id": str(truth_object.tenant_id),
                "truth_object_id": str(truth_object.id),
                "transition": transition_name,
                "sync_status": "pending",
            },
        )
        try:
            await db.flush()  # Persist event and history before returning
        except Exception:
            from .audit_write_monitor import record_audit_write_failure
            record_audit_write_failure()
            raise
        return truth_object
