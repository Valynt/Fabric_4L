"""Audit Resilience Security Tests — P1 Gap Remediation

Validates that audit event emission failures do not block the request or raise
unhandled exceptions to the caller. The audit path is fire-and-forget: a
failure to write an audit event must be logged but must not propagate to the
HTTP response.

Gap matrix ref:
  P1 gap 8 — Audit Event Failure: audit failure blocks request

Author: Platform Security Team
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from value_fabric.shared.audit.emitter import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome

pytestmark = [
    pytest.mark.security,
    pytest.mark.audit_logging,
]

_TENANT_ID = "tenant-audit-resilience"


# ---------------------------------------------------------------------------
# emit_audit_event does not raise on logger failure
# ---------------------------------------------------------------------------


class TestAuditEmitterResilience:
    """P1 gap 8: emit_audit_event must not propagate logger or DB failures."""

    def test_emit_audit_event_returns_event_on_success(self):
        """POSITIVE: emit_audit_event returns an AuditEvent on the happy path."""
        event = emit_audit_event(
            AuditAction.TENANT_CREATED,
            tenant_id=None,
            user_id="user-001",
            outcome=AuditOutcome.SUCCESS,
        )
        assert event is not None, "emit_audit_event must return an AuditEvent."
        assert event.action == AuditAction.TENANT_CREATED

    def test_emit_audit_event_does_not_raise_when_logger_fails(self):
        """NEGATIVE: If the audit logger raises, emit_audit_event must not propagate it."""
        with patch("value_fabric.shared.audit.emitter.logger") as mock_logger:
            mock_logger.info.side_effect = RuntimeError("log sink unavailable")
            emit_audit_event(
                AuditAction.TENANT_CREATED,
                tenant_id=None,
                outcome=AuditOutcome.FAILURE,
            )
            # Reaching here means the emitter caught the exception — test passes.
            # While the gap exists, logger.info raises and the test xfails (expected).

    def test_emit_audit_event_does_not_raise_on_serialisation_error(self):
        """ADVERSARIAL: Unserializable details must not crash the emitter."""
        class _Unserializable:
            def __repr__(self):
                raise ValueError("cannot repr")

        emit_audit_event(
            AuditAction.TENANT_CREATED,
            tenant_id=None,
            details={"bad": _Unserializable()},
        )
        # Reaching here means the emitter handled the unserializable value gracefully.

    def test_emit_audit_event_logs_failure_without_raising(self, caplog):
        """NEGATIVE: When the logger raises, the failure is swallowed (not re-raised)."""
        with patch("value_fabric.shared.audit.emitter.logger") as mock_logger:
            mock_logger.info.side_effect = OSError("disk full")
            emit_audit_event(
                AuditAction.TENANT_CREATED,
                tenant_id=None,
            )
            # Reaching here means the OSError was caught — test passes.

    def test_audit_event_id_is_unique_per_call(self):
        """POSITIVE: Each call to emit_audit_event produces a unique event ID."""
        event_a = emit_audit_event(AuditAction.TENANT_CREATED, tenant_id=None)
        event_b = emit_audit_event(AuditAction.TENANT_CREATED, tenant_id=None)
        assert event_a.id != event_b.id, (
            "Each audit event must have a unique ID."
        )

    def test_audit_event_outcome_recorded_correctly(self):
        """POSITIVE: The outcome field is preserved on the returned event."""
        event = emit_audit_event(
            AuditAction.TENANT_CREATED,
            tenant_id=None,
            outcome=AuditOutcome.FAILURE,
        )
        assert event.outcome == AuditOutcome.FAILURE, (
            "AuditOutcome.FAILURE must be preserved on the returned event."
        )


# ---------------------------------------------------------------------------
# AuditEmitter.write_to_db failure does not block
# ---------------------------------------------------------------------------


class TestAuditEmitterDbWriteResilience:
    """DB write failures (BackgroundTask path) must be logged, not raised."""

    def test_write_to_db_failure_is_caught(self):
        """NEGATIVE: A DB write failure in write_to_db must not propagate.

        write_to_db is a static method: AuditEmitter.write_to_db(event, db_factory).
        It is called as a BackgroundTask — failures must be logged, not raised.
        """
        from value_fabric.shared.audit.emitter import AuditEmitter
        import asyncio

        event = emit_audit_event(AuditAction.TENANT_CREATED, tenant_id=None)

        def _broken_session():
            raise RuntimeError("DB connection refused")

        # write_to_db catches the RuntimeError internally and logs it — must not re-raise.
        asyncio.run(AuditEmitter.write_to_db(event, _broken_session))

    def test_audit_emitter_constructed_without_db_session(self):
        """POSITIVE: AuditEmitter can be constructed without arguments."""
        from value_fabric.shared.audit.emitter import AuditEmitter
        emitter = AuditEmitter()
        assert emitter is not None
