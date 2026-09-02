"""Validation stage task.

Submodule of ``layer1_ingestion.shared.tasks`` (split from the former megafile).
"""

from uuid import UUID

from value_fabric.shared.error_handling import sanitize_log_error

from ...metrics.prometheus_metrics import get_metrics
from ..database import get_db_session
from ..models import (
    ExtractedData,
    PipelineStage,
    ScrapingJob,
)
from ..otel_celery import start_celery_span
from ..task_contracts import validation_stageResult
from ..tasks import (
    _update_stage,
)
from ..tasks_helpers import _validate_payload_against_schema
from .tasks_bootstrap import celery_app, logger


@celery_app.task(name="layer1_ingestion.shared.tasks.validation_stage", bind=True, max_retries=2)
def validation_stage(self, prev_result: dict, tenant_id: str):
    """Stage 7: Validation (schema, data quality).

    Validates the job's ExtractedData payload against the extraction_schema
    stored in the job configuration.  Results are written back to the
    ExtractedData record so downstream stages and the API can surface them.

    If no extraction_schema is configured the stage completes successfully
    without modifying the ExtractedData record (schema validation is opt-in).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting validation stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.validation",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _update_stage(session, job_id, PipelineStage.VALIDATION, "RUNNING")
                job.progress_stage = PipelineStage.VALIDATION.value
                session.commit()

                config = job.configuration
                extraction_config = config.get("extraction_config", {})
                schema = extraction_config.get("extraction_schema")

                if schema and isinstance(schema, dict):
                    # Locate the ExtractedData record produced by ai_extraction_stage
                    extracted = (
                        session.query(ExtractedData)
                        .filter(
                            ExtractedData.job_id == job_id,
                            ExtractedData.tenant_id == job.tenant_id,
                        )
                        .order_by(ExtractedData.provenance_extracted_at.desc())
                        .first()
                    )

                    if extracted is not None:
                        payload = extracted.data or {}
                        schema_valid, errors, required_present, required_missing = (
                            _validate_payload_against_schema(payload, schema)
                        )

                        extracted.validation_schema_valid = schema_valid
                        extracted.validation_errors = errors
                        extracted.validation_required_fields_present = required_present
                        extracted.validation_required_fields_missing = required_missing

                        if not schema_valid:
                            logger.warning(
                                "Extracted data failed schema validation",
                                job_id=str(job_id),
                                tenant_id=str(job.tenant_id),
                                error_count=len(errors),
                                required_missing=required_missing,
                            )
                        else:
                            logger.info(
                                "Extracted data passed schema validation",
                                job_id=str(job_id),
                                tenant_id=str(job.tenant_id),
                            )
                    else:
                        logger.info(
                            "No ExtractedData record found; skipping schema validation",
                            job_id=str(job_id),
                        )
                else:
                    logger.info(
                        "No extraction_schema configured; skipping schema validation",
                        job_id=str(job_id),
                    )

                _update_stage(session, job_id, PipelineStage.VALIDATION, "COMPLETED")
                session.commit()

                logger.info("Validation completed", job_id=str(job_id))
                return validation_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            logger.error(
                "Validation failed",
                job_id=str(job_id),
                error_code="VALIDATION_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session,
                    job_id,
                    PipelineStage.VALIDATION,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="validation", reason="stage_failure")
            raise self.retry(exc=exc, countdown=10)
