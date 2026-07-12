"""RESOLVING_CONNECTOR stage handler for source ingress."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from layer1_ingestion.domain.stages import IngestionStage
from layer1_ingestion.orchestrator.connector_resolution import (
    ConnectorResolution,
    ConnectorResolutionError,
    resolve_connector_for_source,
)
from layer1_ingestion.orchestrator.coordinator import PipelineCoordinator
from layer1_ingestion.orchestrator.stage_handlers.base import StageHandler
from layer1_ingestion.orchestrator.stage_handlers.context import StageContext, _flatten_artifact_ids
from layer1_ingestion.shared.models import IngestionRunStep, SourceIngestionRun


def _snapshot_hash(source: Any, source_version: Any, resolution: ConnectorResolution) -> str:
    """Build a deterministic hash for the connector/source snapshot used by this run."""
    payload = {
        "source": {
            "id": getattr(source, "id", None),
            "source_type": getattr(source, "source_type", None),
            "custody_mode": getattr(source, "custody_mode", None),
            "external_reference": getattr(source, "external_reference", None),
            "field_scope_id": getattr(source, "field_scope_id", None),
            "snapshot_hash": getattr(source, "snapshot_hash", None),
        },
        "source_version": {
            "id": getattr(source_version, "id", None),
            "content_hash": getattr(source_version, "content_hash", None),
            "raw_storage_uri": getattr(source_version, "raw_storage_uri", None),
            "source_uri": getattr(source_version, "source_uri", None),
            "meta": getattr(source_version, "meta", {}),
        },
        "resolution": resolution.to_artifact(),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ResolvingConnectorHandler(StageHandler):
    """Build a connector plan artifact from source and version metadata."""

    stage = IngestionStage.RESOLVING_CONNECTOR

    def handle(self, ctx: StageContext) -> str:
        source = ctx.source
        source_version = ctx.source_version
        if source is None:
            return ctx.fail_permanent(
                error_code="MISSING_SOURCE",
                error_detail_safe="Connector resolution requires a source record.",
            )
        if source_version is None:
            return ctx.fail_permanent(
                error_code="MISSING_SOURCE_VERSION",
                error_detail_safe="Connector resolution requires a source version record.",
            )

        try:
            resolution = resolve_connector_for_source(source, source_version)
        except ConnectorResolutionError as exc:
            return ctx.fail_permanent(
                error_code=exc.code,
                error_detail_safe=f"Unable to resolve connector: {exc.message}",
            )

        ctx.run.connector_name = resolution.connector_name
        ctx.run.connector_config_hash = resolution.config_hash()
        ctx.run.policy_version = resolution.policy_version
        ctx.run.source_snapshot_hash = _snapshot_hash(source, source_version, resolution)
        ctx.persist_step_artifact("connector_resolution", resolution.to_artifact())
        return ctx.advance(IngestionStage.FETCHING_SOURCE)

    def execute(
        self,
        db: Session,
        coordinator: PipelineCoordinator,
        run: SourceIngestionRun,
        step: IngestionRunStep,
    ) -> None:
        """Pipeline entry point: execute in a stage context."""
        coordinator.mark_step_running(step)
        ctx = StageContext(
            tenant_id=run.tenant_id,
            account_id=getattr(run.source, "account_id", None),
            source=run.source,
            source_version=run.version,
            step=step,
            run=run,
            coordinator=coordinator,
            db=db,
            artifacts=_flatten_artifact_ids(step.input_artifact_ids or {}),
        )
        self.handle(ctx)
