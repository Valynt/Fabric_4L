"""Access validation stage for the canonical source ingestion pipeline.

Verifies the source exists, the tenant has access, and any required consent is
active before allowing the run to proceed to connector resolution.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from layer1_ingestion.shared.models import (
    IngestionRunStatus,
    IngestionRunStep,
    SourceConsentStatus,
    SourceIngestionRun,
    SourceVersion,
)

from ..coordinator import PipelineCoordinator
from ..state_machine import PipelineStateMachine
from .base import StageHandler


class ValidatingAccessHandler(StageHandler):
    """Validate tenant access and consent for a source ingestion run."""

    def execute(
        self,
        db: Session,
        coordinator: PipelineCoordinator,
        run: SourceIngestionRun,
        step: IngestionRunStep,
    ) -> None:
        coordinator.mark_step_running(step)

        source = run.source
        if source is None or source.status != "active":
            self._fail(
                coordinator,
                run,
                step,
                "SOURCE_NOT_ACTIVE",
                "Source is missing or not in active status.",
            )
            return

        version = (
            db.query(SourceVersion)
            .filter(
                SourceVersion.id == run.source_version_id,
                SourceVersion.source_id == run.source_id,
            )
            .first()
        )
        if version is None:
            self._fail(
                coordinator,
                run,
                step,
                "SOURCE_VERSION_NOT_FOUND",
                "Source version not found.",
            )
            return

        consent = run.consent
        if consent is not None and consent.status != SourceConsentStatus.GRANTED.value:
            self._fail(
                coordinator,
                run,
                step,
                "CONSENT_NOT_GRANTED",
                f"Consent is {consent.status}, expected granted.",
            )
            return

        if consent is not None and consent.expires_at is not None:
            if consent.expires_at < datetime.now(UTC):
                self._fail(
                    coordinator,
                    run,
                    step,
                    "CONSENT_EXPIRED",
                    "Consent has expired.",
                )
                return

        output_artifacts = {
            "source_id": str(source.id),
            "source_version_id": str(version.id),
            "custody_mode": source.custody_mode,
            "consent_status": consent.status if consent else None,
            "validated_at": datetime.now(UTC).isoformat(),
        }
        coordinator.mark_step_completed(step, output_artifacts)

        next_state = PipelineStateMachine.next_happy_state(step.stage_name)
        if next_state is not None:
            coordinator.advance(
                run,
                next_state,
                output_artifact_ids={step.stage_name: output_artifacts},
            )

    def _fail(
        self,
        coordinator: PipelineCoordinator,
        run: SourceIngestionRun,
        step: IngestionRunStep,
        error_code: str,
        error_detail: str,
    ) -> None:
        coordinator.mark_step_failed(step, error_code, error_detail)
        coordinator.advance(
            run,
            IngestionRunStatus.FAILED_PERMANENT.value,
            error_code=error_code,
            error_detail_safe=error_detail,
        )
