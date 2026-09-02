"""Unit tests for the EventOutbox model and dispatch_outbox_event Celery task.

Covers:
- EventOutbox model field defaults and constraints
- notification_stage creates outbox rows after successful storage
- No outbox row is created if storage has not produced an output
- dispatch_outbox_event marks event as dispatched on success
- dispatch_outbox_event increments attempts and records last_error on failure
- After MAX_DISPATCH_ATTEMPTS, status becomes dead_letter
- Duplicate dispatch is idempotent (already-dispatched rows are skipped)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from layer1_ingestion.shared.models import (
    AccountIntelligencePacket,
    EventOutbox,
    OutboxStatus,
    SourceCorpus,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_outbox_row(
    *,
    status: str = OutboxStatus.PENDING.value,
    attempts: int = 0,
    event_type: str = "layer1.source_corpus.ready",
    tenant_id: UUID | None = None,
) -> EventOutbox:
    return EventOutbox(
        id=uuid4(),
        tenant_id=tenant_id or uuid4(),
        event_type=event_type,
        aggregate_type="SourceCorpus",
        aggregate_id=str(uuid4()),
        payload={
            "event_type": event_type,
            "tenant_id": str(uuid4()),
            "job_id": str(uuid4()),
            "output_contract": "SourceCorpus",
            "output_id": str(uuid4()),
            "skill_name": "licensing_company_intake",
            "emitted_at": datetime.now(UTC).isoformat(),
        },
        status=status,
        attempts=attempts,
        created_at=datetime.now(UTC),
    )


def _dispatch_event(dispatch_outbox_event, row_or_event_id):
    event_id = row_or_event_id.id if hasattr(row_or_event_id, "id") else row_or_event_id
    tenant_id = row_or_event_id.tenant_id if hasattr(row_or_event_id, "tenant_id") else uuid4()
    return dispatch_outbox_event(str(event_id), str(tenant_id))


def _run_notification_stage(notification_stage, job):
    return notification_stage({"job_id": str(job.id)}, str(job.tenant_id))


# =============================================================================
# EventOutbox model
# =============================================================================


class TestEventOutboxModel:
    """EventOutbox field defaults and enum values."""

    def test_column_default_status_is_pending(self):
        """The Column default for status is OutboxStatus.PENDING."""
        from sqlalchemy import inspect as sa_inspect
        col = EventOutbox.__table__.c["status"]
        assert col.default.arg == OutboxStatus.PENDING.value

    def test_column_default_attempts_is_zero(self):
        """The Column default for attempts is 0."""
        from sqlalchemy import inspect as sa_inspect
        col = EventOutbox.__table__.c["attempts"]
        assert col.default.arg == 0

    def test_outbox_status_enum_values(self):
        assert OutboxStatus.PENDING.value == "pending"
        assert OutboxStatus.DISPATCHED.value == "dispatched"
        assert OutboxStatus.FAILED.value == "failed"
        assert OutboxStatus.DEAD_LETTER.value == "dead_letter"

    def test_dispatched_at_and_dead_lettered_at_nullable(self):
        row = _make_outbox_row()
        assert row.dispatched_at is None
        assert row.dead_lettered_at is None

    def test_last_error_nullable(self):
        row = _make_outbox_row()
        assert row.last_error is None

    def test_payload_contains_required_fields(self):
        tenant_id = uuid4()
        job_id = uuid4()
        output_id = uuid4()
        payload = {
            "event_type": "layer1.source_corpus.ready",
            "tenant_id": str(tenant_id),
            "job_id": str(job_id),
            "output_contract": "SourceCorpus",
            "output_id": str(output_id),
            "skill_name": "licensing_company_intake",
            "aggregate_type": "SourceCorpus",
            "aggregate_id": str(output_id),
            "emitted_at": datetime.now(UTC).isoformat(),
        }
        row = EventOutbox(
            tenant_id=tenant_id,
            event_type="layer1.source_corpus.ready",
            aggregate_type="SourceCorpus",
            aggregate_id=str(output_id),
            payload=payload,
        )
        assert row.payload["tenant_id"] == str(tenant_id)
        assert row.payload["job_id"] == str(job_id)
        assert row.payload["output_id"] == str(output_id)
        assert row.payload["output_contract"] == "SourceCorpus"


# =============================================================================
# dispatch_outbox_event — success path
# =============================================================================


class TestDispatchOutboxEventSuccess:
    """dispatch_outbox_event marks event as dispatched on success."""

    def test_dispatches_pending_event(self):
        from layer1_ingestion.shared.tasks import dispatch_outbox_event

        event_id = uuid4()
        row = _make_outbox_row(status=OutboxStatus.PENDING.value)
        row.id = event_id

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = row

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            _dispatch_event(dispatch_outbox_event, row)

        assert row.status == OutboxStatus.DISPATCHED.value
        assert row.dispatched_at is not None
        mock_session.commit.assert_called()

    def test_skips_already_dispatched_event(self):
        from layer1_ingestion.shared.tasks import dispatch_outbox_event

        event_id = uuid4()
        row = _make_outbox_row(status=OutboxStatus.DISPATCHED.value)
        row.id = event_id

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = row

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            _dispatch_event(dispatch_outbox_event, row)

        # Status must not change
        assert row.status == OutboxStatus.DISPATCHED.value
        mock_session.commit.assert_not_called()

    def test_skips_dead_lettered_event(self):
        from layer1_ingestion.shared.tasks import dispatch_outbox_event

        event_id = uuid4()
        row = _make_outbox_row(status=OutboxStatus.DEAD_LETTER.value)
        row.id = event_id

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = row

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            _dispatch_event(dispatch_outbox_event, row)

        assert row.status == OutboxStatus.DEAD_LETTER.value
        mock_session.commit.assert_not_called()

    def test_handles_missing_event_gracefully(self):
        from layer1_ingestion.shared.tasks import dispatch_outbox_event

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            # Should not raise
            dispatch_outbox_event(str(uuid4()), str(uuid4()))


# =============================================================================
# dispatch_outbox_event — failure and retry path
# =============================================================================


class TestDispatchOutboxEventFailure:
    """dispatch_outbox_event increments attempts and records last_error on failure."""

    def test_increments_attempts_on_failure(self):
        import layer1_ingestion.shared.tasks as tasks_module

        event_id = uuid4()
        row = _make_outbox_row(status=OutboxStatus.PENDING.value, attempts=0)
        row.id = event_id

        call_count = 0

        def session_factory(*args, **kwargs):
            nonlocal call_count
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            if call_count == 0:
                # First call: raise during delivery
                mock_session.query.return_value.filter.return_value.first.side_effect = RuntimeError("delivery failed")
            else:
                # Second call: return row for error recording
                mock_session.query.return_value.filter.return_value.first.return_value = row
            call_count += 1
            return mock_session

        with patch("layer1_ingestion.shared.tasks.get_db_session", side_effect=session_factory):
            with patch.object(
                tasks_module.dispatch_outbox_event,
                "retry",
                side_effect=Exception("retry"),
            ):
                with pytest.raises(Exception):
                    _dispatch_event(tasks_module.dispatch_outbox_event, row)

        assert row.attempts == 1
        assert row.last_error is not None

    def test_dead_letters_after_max_attempts(self):
        import layer1_ingestion.shared.tasks as tasks_module
        from layer1_ingestion.shared.tasks import MAX_DISPATCH_ATTEMPTS

        event_id = uuid4()
        row = _make_outbox_row(
            status=OutboxStatus.FAILED.value,
            attempts=MAX_DISPATCH_ATTEMPTS - 1,
        )
        row.id = event_id

        call_count = 0

        def session_factory(*args, **kwargs):
            nonlocal call_count
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            if call_count == 0:
                mock_session.query.return_value.filter.return_value.first.side_effect = RuntimeError("delivery failed")
            else:
                mock_session.query.return_value.filter.return_value.first.return_value = row
            call_count += 1
            return mock_session

        with patch("layer1_ingestion.shared.tasks.get_db_session", side_effect=session_factory):
            with patch.object(
                tasks_module.dispatch_outbox_event,
                "retry",
                side_effect=Exception("retry"),
            ):
                # Should not raise after dead-lettering (returns early)
                try:
                    _dispatch_event(tasks_module.dispatch_outbox_event, row)
                except Exception:
                    pass

        assert row.status == OutboxStatus.DEAD_LETTER.value
        assert row.dead_lettered_at is not None

    def test_records_last_error_message(self):
        import layer1_ingestion.shared.tasks as tasks_module

        event_id = uuid4()
        row = _make_outbox_row(status=OutboxStatus.PENDING.value, attempts=0)
        row.id = event_id

        call_count = 0

        def session_factory(*args, **kwargs):
            nonlocal call_count
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            if call_count == 0:
                mock_session.query.return_value.filter.return_value.first.side_effect = RuntimeError("connection refused")
            else:
                mock_session.query.return_value.filter.return_value.first.return_value = row
            call_count += 1
            return mock_session

        with patch("layer1_ingestion.shared.tasks.get_db_session", side_effect=session_factory):
            with patch.object(
                tasks_module.dispatch_outbox_event,
                "retry",
                side_effect=Exception("retry"),
            ):
                with pytest.raises(Exception):
                    _dispatch_event(tasks_module.dispatch_outbox_event, row)

        assert "connection refused" in (row.last_error or "")


# =============================================================================
# notification_stage outbox creation
# =============================================================================


class TestNotificationStageOutbox:
    """notification_stage creates EventOutbox rows after successful storage."""

    def _make_job(
        self,
        *,
        tenant_id: UUID | None = None,
        skill_name: str = "licensing_company_intake",
        output_contract: str = "SourceCorpus",
        downstream_events: list[str] | None = None,
    ) -> MagicMock:
        job = MagicMock()
        job.id = uuid4()
        job.tenant_id = tenant_id or uuid4()
        job.target_id = uuid4()
        job.skill_name = skill_name
        job.output_contract = output_contract
        job.downstream_events = downstream_events or [
            "layer1.source_corpus.ready",
            "layer2.ontology_extraction.requested",
        ]
        job.started_at = datetime.now(UTC)
        job.completed_at = None
        job.status = "QUEUED"
        job.progress_stage = None
        job.progress_percent_complete = 0
        return job

    def test_creates_outbox_rows_for_each_downstream_event(self):
        """One EventOutbox row per downstream_event entry."""
        import layer1_ingestion.shared.tasks as tasks_module

        job = self._make_job()
        corpus_id = uuid4()
        corpus = MagicMock(spec=SourceCorpus)
        corpus.id = corpus_id

        added_rows: list[EventOutbox] = []

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        def query_side_effect(model):
            q = MagicMock()
            if model is tasks_module.ScrapingJob:
                q.get.return_value = job
            elif model is tasks_module.ScrapingTarget:
                q.get.return_value = None
            elif model is SourceCorpus:
                q.filter.return_value.first.return_value = corpus
            elif model is AccountIntelligencePacket:
                q.filter.return_value.first.return_value = None
            elif model is tasks_module.JobStageDetail:
                q.filter.return_value.first.return_value = None
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_session.query.side_effect = query_side_effect

        def add_side_effect(obj):
            if isinstance(obj, EventOutbox):
                added_rows.append(obj)

        mock_session.add.side_effect = add_side_effect

        with patch("layer1_ingestion.shared.tasks.notification.get_db_session", return_value=mock_session):
            with patch.object(tasks_module.dispatch_outbox_event, "apply_async"):
                _run_notification_stage(tasks_module.notification_stage, job)

        assert len(added_rows) == 2
        event_types = {r.event_type for r in added_rows}
        assert "layer1.source_corpus.ready" in event_types
        assert "layer2.ontology_extraction.requested" in event_types

    def test_outbox_payload_contains_required_fields(self):
        """Each outbox row payload includes tenant_id, job_id, output_id, output_contract."""
        import layer1_ingestion.shared.tasks as tasks_module

        tenant_id = uuid4()
        job = self._make_job(tenant_id=tenant_id, downstream_events=["layer1.source_corpus.ready"])
        corpus_id = uuid4()
        corpus = MagicMock(spec=SourceCorpus)
        corpus.id = corpus_id

        added_rows: list[EventOutbox] = []

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        def query_side_effect(model):
            q = MagicMock()
            if model is tasks_module.ScrapingJob:
                q.get.return_value = job
            elif model is tasks_module.ScrapingTarget:
                q.get.return_value = None
            elif model is SourceCorpus:
                q.filter.return_value.first.return_value = corpus
            elif model is tasks_module.JobStageDetail:
                q.filter.return_value.first.return_value = None
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_session.query.side_effect = query_side_effect
        mock_session.add.side_effect = lambda obj: added_rows.append(obj) if isinstance(obj, EventOutbox) else None

        with patch("layer1_ingestion.shared.tasks.notification.get_db_session", return_value=mock_session):
            with patch.object(tasks_module.dispatch_outbox_event, "apply_async"):
                _run_notification_stage(tasks_module.notification_stage, job)

        assert len(added_rows) == 1
        payload = added_rows[0].payload
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["job_id"] == str(job.id)
        assert payload["output_id"] == str(corpus_id)
        assert payload["output_contract"] == "SourceCorpus"

    def test_no_outbox_rows_when_no_skill(self):
        """Jobs without a skill_name do not create outbox rows."""
        import layer1_ingestion.shared.tasks as tasks_module

        job = self._make_job(skill_name=None, downstream_events=[])
        job.skill_name = None
        job.downstream_events = []

        added_rows: list[EventOutbox] = []

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        def query_side_effect(model):
            q = MagicMock()
            if model is tasks_module.ScrapingJob:
                q.get.return_value = job
            elif model is tasks_module.ScrapingTarget:
                q.get.return_value = None
            elif model is tasks_module.JobStageDetail:
                q.filter.return_value.first.return_value = None
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_session.query.side_effect = query_side_effect
        mock_session.add.side_effect = lambda obj: added_rows.append(obj) if isinstance(obj, EventOutbox) else None

        with patch("layer1_ingestion.shared.tasks.notification.get_db_session", return_value=mock_session):
            _run_notification_stage(tasks_module.notification_stage, job)

        outbox_rows = [r for r in added_rows if isinstance(r, EventOutbox)]
        assert len(outbox_rows) == 0

    def test_dispatch_apply_async_called_per_outbox_row(self):
        """dispatch_outbox_event.apply_async is called once per outbox row."""
        import layer1_ingestion.shared.tasks as tasks_module

        job = self._make_job(downstream_events=["layer1.source_corpus.ready", "layer2.ontology_extraction.requested"])
        corpus = MagicMock(spec=SourceCorpus)
        corpus.id = uuid4()

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        def query_side_effect(model):
            q = MagicMock()
            if model is tasks_module.ScrapingJob:
                q.get.return_value = job
            elif model is tasks_module.ScrapingTarget:
                q.get.return_value = None
            elif model is SourceCorpus:
                q.filter.return_value.first.return_value = corpus
            elif model is tasks_module.JobStageDetail:
                q.filter.return_value.first.return_value = None
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_session.query.side_effect = query_side_effect

        with patch("layer1_ingestion.shared.tasks.notification.get_db_session", return_value=mock_session):
            with patch.object(tasks_module.dispatch_outbox_event, "apply_async") as mock_apply:
                _run_notification_stage(tasks_module.notification_stage, job)

        assert mock_apply.call_count == 2

    def test_account_intelligence_packet_outbox(self):
        """Prospect research jobs create outbox rows with AccountIntelligencePacket output_id."""
        import layer1_ingestion.shared.tasks as tasks_module

        job = self._make_job(
            skill_name="prospect_research",
            output_contract="AccountIntelligencePacket",
            downstream_events=["layer1.account_intelligence.ready", "layer2.signal_extraction.requested"],
        )
        packet_id = uuid4()
        packet = MagicMock(spec=AccountIntelligencePacket)
        packet.id = packet_id

        added_rows: list[EventOutbox] = []

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        def query_side_effect(model):
            q = MagicMock()
            if model is tasks_module.ScrapingJob:
                q.get.return_value = job
            elif model is tasks_module.ScrapingTarget:
                q.get.return_value = None
            elif model is AccountIntelligencePacket:
                q.filter.return_value.first.return_value = packet
            elif model is tasks_module.JobStageDetail:
                q.filter.return_value.first.return_value = None
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_session.query.side_effect = query_side_effect
        mock_session.add.side_effect = lambda obj: added_rows.append(obj) if isinstance(obj, EventOutbox) else None

        with patch("layer1_ingestion.shared.tasks.notification.get_db_session", return_value=mock_session):
            with patch.object(tasks_module.dispatch_outbox_event, "apply_async"):
                _run_notification_stage(tasks_module.notification_stage, job)

        assert len(added_rows) == 2
        for row in added_rows:
            assert row.payload["output_id"] == str(packet_id)
            assert row.payload["output_contract"] == "AccountIntelligencePacket"
