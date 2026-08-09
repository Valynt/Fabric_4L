"""Unit tests for the durable pipeline orchestrator.

Covers:
- PipelineStateMachine transitions and happy-path advancement
- PipelineCoordinator: start_run, advance, mark_step_completed, _emit_event
- Outbox relay: dispatch_pending_pipeline_events emits Celery task calls
- NoopStageHandler: walks the happy path without external work
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from layer1_ingestion.orchestrator import PipelineCoordinator, PipelineStateMachine, TransitionError
from layer1_ingestion.orchestrator.connector_resolution import (
    ConnectorKind,
    ConnectorResolution,
    CustodyMode,
    FetchStrategy,
)
from layer1_ingestion.orchestrator.outbox_relay import dispatch_pending_pipeline_events
from layer1_ingestion.orchestrator.stage_handlers import get_stage_handler
from layer1_ingestion.orchestrator.stage_handlers.applying_policy import ApplyingPolicyHandler
from layer1_ingestion.orchestrator.stage_handlers.fetching_source import (
    FetchingSourceHandler,
    ObjectStorageClient,
)
from layer1_ingestion.orchestrator.stage_handlers.validating_access import ValidatingAccessHandler
from layer1_ingestion.shared.models import (
    EventOutbox,
    IngestedSource,
    IngestionRunStatus,
    IngestionRunStep,
    IngestionRunStepStatus,
    SourceConsent,
    SourceConsentStatus,
    SourceIngestionRun,
    SourceType,
    SourceVersion,
)


@pytest.fixture()
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture()
def ingestion_run(db: Session, tenant_id: UUID) -> SourceIngestionRun:
    """Create a source, version, and a fresh ACCEPTED ingestion run."""
    source = IngestedSource(
        tenant_id=tenant_id,
        account_id="acc_test_123",
        source_type=SourceType.NOTES,
        title="Test Source",
        fingerprint="deadbeef123",
        created_by=uuid4(),
    )
    db.add(source)
    db.flush()

    version = SourceVersion(
        source_id=source.id,
        version_number=1,
        content_hash="deadbeef",
        raw_storage_uri="raw://test",
        raw_bytes_size=0,
        media_type="text/plain",
        created_by=uuid4(),
    )
    db.add(version)
    db.flush()

    run = SourceIngestionRun(
        tenant_id=tenant_id,
        source_id=source.id,
        source_version_id=version.id,
        status=IngestionRunStatus.ACCEPTED,
        requested_outputs=["fabric_found_summary"],
        created_by=uuid4(),
    )
    db.add(run)
    db.flush()
    db.refresh(run)
    return run


class TestPipelineStateMachine:
    def test_happy_path_sequence(self):
        states = PipelineStateMachine._HAPPY_PATH
        assert states[0] == IngestionRunStatus.ACCEPTED.value
        assert states[1] == IngestionRunStatus.VALIDATING_ACCESS.value
        assert states[2] == IngestionRunStatus.RESOLVING_CONNECTOR.value
        assert states[-1] == IngestionRunStatus.READY.value

    def test_next_happy_state(self):
        assert (
            PipelineStateMachine.next_happy_state(IngestionRunStatus.ACCEPTED.value)
            == IngestionRunStatus.VALIDATING_ACCESS.value
        )
        assert (
            PipelineStateMachine.next_happy_state(IngestionRunStatus.VALIDATING_ACCESS.value)
            == IngestionRunStatus.RESOLVING_CONNECTOR.value
        )
        assert PipelineStateMachine.next_happy_state(IngestionRunStatus.READY.value) is None

    def test_invalid_transition_raises(self):
        with pytest.raises(TransitionError):
            PipelineStateMachine().transition(
                IngestionRunStatus.ACCEPTED.value,
                IngestionRunStatus.READY.value,
            )

    def test_terminal_state_cannot_transition(self):
        with pytest.raises(TransitionError):
            PipelineStateMachine().transition(
                IngestionRunStatus.READY.value,
                IngestionRunStatus.VALIDATING_ACCESS.value,
            )


class TestPipelineCoordinator:
    def test_start_run_advances_to_validating_access(self, db: Session, ingestion_run: SourceIngestionRun):
        coordinator = PipelineCoordinator(db)
        coordinator.start_run(ingestion_run)
        db.flush()

        assert ingestion_run.status == IngestionRunStatus.VALIDATING_ACCESS.value
        assert ingestion_run.current_step_id is not None
        assert ingestion_run.started_at is not None

        step = db.query(IngestionRunStep).filter(
            IngestionRunStep.id == ingestion_run.current_step_id
        ).first()
        assert step is not None
        assert step.stage_name == IngestionRunStatus.VALIDATING_ACCESS.value
        assert step.status == IngestionRunStepStatus.PENDING.value

    def test_start_run_emits_outbox_event(self, db: Session, ingestion_run: SourceIngestionRun):
        coordinator = PipelineCoordinator(db)
        coordinator.start_run(ingestion_run)
        db.flush()

        events = (
            db.query(EventOutbox)
            .filter(
                EventOutbox.aggregate_id == str(ingestion_run.id),
                EventOutbox.stage_name == IngestionRunStatus.VALIDATING_ACCESS.value,
            )
            .all()
        )
        assert len(events) == 1
        assert events[0].event_type == "fabric.run.stage_requested.v1"
        assert events[0].status == "pending"

    def test_advance_creates_next_step(self, db: Session, ingestion_run: SourceIngestionRun):
        coordinator = PipelineCoordinator(db)
        coordinator.start_run(ingestion_run)
        db.flush()

        step = db.query(IngestionRunStep).filter(
            IngestionRunStep.id == ingestion_run.current_step_id
        ).first()
        coordinator.mark_step_running(step)
        coordinator.mark_step_completed(step, {"checksum": "abc"})
        next_state = IngestionRunStatus.RESOLVING_CONNECTOR.value
        next_step = coordinator.advance(ingestion_run, next_state)
        db.flush()

        assert ingestion_run.status == next_state
        assert ingestion_run.current_step_id == next_step.id
        assert next_step.stage_name == next_state

    def test_advance_from_non_accepted_requires_running_step(
        self, db: Session, ingestion_run: SourceIngestionRun
    ):
        coordinator = PipelineCoordinator(db)
        coordinator.start_run(ingestion_run)
        db.flush()
        first_step = db.query(IngestionRunStep).filter(
            IngestionRunStep.id == ingestion_run.current_step_id
        ).first()
        # Move directly without marking the step running/completed
        next_step = coordinator.advance(ingestion_run, IngestionRunStatus.RESOLVING_CONNECTOR.value)
        db.flush()

        # The old step is not completed because it was never running
        db.refresh(first_step)
        assert first_step.status == IngestionRunStepStatus.PENDING.value
        assert next_step.stage_name == IngestionRunStatus.RESOLVING_CONNECTOR.value


class TestOutboxRelay:
    def test_dispatch_pending_events_calls_dispatcher(self, db: Session, ingestion_run: SourceIngestionRun):
        coordinator = PipelineCoordinator(db)
        coordinator.start_run(ingestion_run)
        db.flush()

        dispatched: list[tuple[str, dict]] = []

        def dispatcher(stage_name: str, payload: dict) -> None:
            dispatched.append((stage_name, payload))

        count = dispatch_pending_pipeline_events(db, dispatcher=dispatcher)
        db.flush()

        assert count == 1
        assert dispatched[0][0] == IngestionRunStatus.VALIDATING_ACCESS.value
        assert dispatched[0][1]["stage_name"] == IngestionRunStatus.VALIDATING_ACCESS.value
        assert "run_id" in dispatched[0][1]

        event = db.query(EventOutbox).filter(
            EventOutbox.aggregate_id == str(ingestion_run.id)
        ).first()
        assert event.status == "dispatched"
        assert event.dispatched_at is not None


class _InMemoryStorageClient(ObjectStorageClient):
    """Fake object storage client that serves the fixed fixture URI."""

    async def download_bytes(self, storage_uri: str) -> bytes:
        if storage_uri == "raw://test":
            return b"happy path content"
        raise FileNotFoundError(storage_uri)


class _TestFetchingSourceHandler(FetchingSourceHandler):
    """Test-only handler wired to an in-memory storage client."""

    def __init__(self) -> None:
        super().__init__(storage_client=_InMemoryStorageClient())


class TestNoopStageHandler:
    def test_handler_walks_happy_path(self, db: Session, ingestion_run: SourceIngestionRun):
        from layer1_ingestion.orchestrator.stage_handlers import register_stage_handler
        from layer1_ingestion.orchestrator.stage_handlers.noop import NoopStageHandler

        register_stage_handler(IngestionRunStatus.VALIDATING_ACCESS.value, NoopStageHandler)
        coordinator = PipelineCoordinator(db)
        handler = get_stage_handler(IngestionRunStatus.VALIDATING_ACCESS.value)

        coordinator.start_run(ingestion_run)
        db.flush()
        step = db.query(IngestionRunStep).filter(
            IngestionRunStep.id == ingestion_run.current_step_id
        ).first()

        handler.run(
            db,
            coordinator,
            ingestion_run.id,
            ingestion_run.tenant_id,
            IngestionRunStatus.VALIDATING_ACCESS.value,
        )
        db.flush()

        db.refresh(ingestion_run)
        db.refresh(step)
        assert step.status == IngestionRunStepStatus.COMPLETED.value
        assert ingestion_run.status == IngestionRunStatus.RESOLVING_CONNECTOR.value
        assert ingestion_run.current_step_id != step.id

    def test_handler_reaches_ready(self, db: Session, ingestion_run: SourceIngestionRun):
        from layer1_ingestion.orchestrator.stage_handlers import (
            _STAGE_HANDLER_REGISTRY,
            register_stage_handler,
        )
        from layer1_ingestion.orchestrator.stage_handlers.noop import NoopStageHandler

        # Snapshot the registry so we can restore it after the test.
        original_registry = dict(_STAGE_HANDLER_REGISTRY)
        register_stage_handler(IngestionRunStatus.VALIDATING_ACCESS.value, NoopStageHandler)
        register_stage_handler(IngestionRunStatus.FETCHING_SOURCE.value, _TestFetchingSourceHandler)
        register_stage_handler(IngestionRunStatus.APPLYING_POLICY.value, ApplyingPolicyHandler)

        coordinator = PipelineCoordinator(db)
        coordinator.start_run(ingestion_run)
        db.flush()

        resolution = ConnectorResolution(
            connector_kind=ConnectorKind.LOCAL,
            connector_name="local",
            custody_mode=CustodyMode.REFERENCE_EXTRACT,
            fetch_strategy=FetchStrategy.LOCAL_PAYLOAD,
            requires_fetch=False,
        )

        try:
            # Walk the full happy path
            while not PipelineStateMachine.is_terminal(ingestion_run.status):
                step = db.query(IngestionRunStep).filter(
                    IngestionRunStep.id == ingestion_run.current_step_id
                ).first()
                if step.stage_name == IngestionRunStatus.FETCHING_SOURCE.value:
                    step.input_artifact_ids = {
                        IngestionRunStatus.RESOLVING_CONNECTOR.value: {
                            "connector_resolution": resolution.to_artifact()
                        }
                    }
                    db.flush()
                handler = get_stage_handler(step.stage_name)
                handler.run(
                    db,
                    coordinator,
                    ingestion_run.id,
                    ingestion_run.tenant_id,
                    step.stage_name,
                )
                db.flush()
                db.refresh(ingestion_run)

            failed_step = (
                db.query(IngestionRunStep)
                .filter(
                    IngestionRunStep.run_id == ingestion_run.id,
                    IngestionRunStep.status == IngestionRunStepStatus.FAILED.value,
                )
                .order_by(IngestionRunStep.created_at.desc())
                .first()
            )
            fail_msg = f"Run ended in {ingestion_run.status}"
            if failed_step:
                fail_msg += (
                    f" at {failed_step.stage_name}: "
                    f"{failed_step.error_code} - {failed_step.error_detail_safe}"
                )
            assert ingestion_run.status == IngestionRunStatus.READY.value, fail_msg
            assert ingestion_run.completed_at is not None
            steps = db.query(IngestionRunStep).filter(
                IngestionRunStep.run_id == ingestion_run.id
            ).all()
            # ACCEPTED is the starting state and does not get its own step.
            assert len(steps) == len(PipelineStateMachine._HAPPY_PATH) - 1
        finally:
            _STAGE_HANDLER_REGISTRY.clear()
            _STAGE_HANDLER_REGISTRY.update(original_registry)


class TestValidatingAccessHandler:
    def test_valid_source_advances_to_resolving_connector(
        self, db: Session, ingestion_run: SourceIngestionRun
    ):
        coordinator = PipelineCoordinator(db)
        coordinator.start_run(ingestion_run)
        db.flush()

        handler = ValidatingAccessHandler()
        handler.run(
            db,
            coordinator,
            ingestion_run.id,
            ingestion_run.tenant_id,
            IngestionRunStatus.VALIDATING_ACCESS.value,
        )
        db.flush()
        db.refresh(ingestion_run)

        assert ingestion_run.status == IngestionRunStatus.RESOLVING_CONNECTOR.value
        step = db.query(IngestionRunStep).filter(
            IngestionRunStep.id == ingestion_run.current_step_id
        ).first()
        assert step is not None
        assert step.stage_name == IngestionRunStatus.RESOLVING_CONNECTOR.value

    def test_inactive_source_fails_permanently(
        self, db: Session, ingestion_run: SourceIngestionRun
    ):
        ingestion_run.source.status = "archived"
        db.flush()
        coordinator = PipelineCoordinator(db)
        coordinator.start_run(ingestion_run)
        db.flush()

        handler = ValidatingAccessHandler()
        handler.run(
            db,
            coordinator,
            ingestion_run.id,
            ingestion_run.tenant_id,
            IngestionRunStatus.VALIDATING_ACCESS.value,
        )
        db.flush()
        db.refresh(ingestion_run)

        assert ingestion_run.status == IngestionRunStatus.FAILED_PERMANENT.value
        assert ingestion_run.completed_at is not None

    def test_missing_version_fails_permanently(
        self, db: Session, tenant_id: UUID
    ):
        source = IngestedSource(
            tenant_id=tenant_id,
            account_id="acc_test_123",
            source_type=SourceType.NOTES,
            title="Test Source",
            fingerprint="deadbeef123",
            created_by=uuid4(),
        )
        db.add(source)
        db.flush()

        run = SourceIngestionRun(
            tenant_id=tenant_id,
            source_id=source.id,
            source_version_id=uuid4(),
            status=IngestionRunStatus.ACCEPTED,
            created_by=uuid4(),
        )
        db.add(run)
        db.flush()

        coordinator = PipelineCoordinator(db)
        coordinator.start_run(run)
        db.flush()

        handler = ValidatingAccessHandler()
        handler.run(
            db,
            coordinator,
            run.id,
            run.tenant_id,
            IngestionRunStatus.VALIDATING_ACCESS.value,
        )
        db.flush()
        db.refresh(run)

        assert run.status == IngestionRunStatus.FAILED_PERMANENT.value

    def test_revoked_consent_fails_permanently(
        self, db: Session, ingestion_run: SourceIngestionRun
    ):
        consent = SourceConsent(
            tenant_id=ingestion_run.tenant_id,
            account_id=ingestion_run.source.account_id,
            source_type=ingestion_run.source.source_type,
            status=SourceConsentStatus.REVOKED,
            consent_hash="revoked-hash",
            scope={},
            granted_by=uuid4(),
        )
        db.add(consent)
        db.flush()
        ingestion_run.consent_id = consent.id
        ingestion_run.source.consent_id = consent.id
        db.flush()

        coordinator = PipelineCoordinator(db)
        coordinator.start_run(ingestion_run)
        db.flush()

        handler = ValidatingAccessHandler()
        handler.run(
            db,
            coordinator,
            ingestion_run.id,
            ingestion_run.tenant_id,
            IngestionRunStatus.VALIDATING_ACCESS.value,
        )
        db.flush()
        db.refresh(ingestion_run)

        assert ingestion_run.status == IngestionRunStatus.FAILED_PERMANENT.value
