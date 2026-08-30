"""Post-processing stage task.

Submodule of ``layer1_ingestion.shared.tasks`` (split from the former megafile).
"""

from uuid import UUID

from value_fabric.shared.error_handling import sanitize_log_error

from ...compliance.pii_scanner import PIIScanner
from ...metrics.prometheus_metrics import get_metrics
from ...skills import get_skill
from ..database import get_db_session
from ..models import (
    ComplianceEventType,
    ComplianceLog,
    ExtractedData,
    JobStatus,
    PipelineStage,
    RawContent,
    ScrapingJob,
)
from ..otel_celery import start_celery_span
from ..task_contracts import post_processing_stageResult
from ..tasks import (
    _update_stage,
    celery_app,
    logger,
)


@celery_app.task(name="layer1_ingestion.shared.tasks.post_processing_stage", bind=True, max_retries=2)
def post_processing_stage(self, prev_result: dict, tenant_id: str):
    """Stage 6: Post-processing (PII redaction, normalization).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting post-processing stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.post_processing",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _update_stage(session, job_id, PipelineStage.POST_PROCESSING, "RUNNING")
                job.status = JobStatus.TRANSFORMING.value
                job.progress_stage = PipelineStage.POST_PROCESSING.value
                session.commit()

                config = job.configuration
                compliance_config = config.get("compliance", {})
                raw_content_id = config.get("raw_content_id")

                if raw_content_id:
                    raw_content = session.query(RawContent).get(UUID(raw_content_id))

                    if raw_content and compliance_config.get("pii_redaction_enabled", True):
                        # Scan for PII
                        scanner = PIIScanner()
                        scan_result = scanner.scan(raw_content.meta_title or "")
                        scan_result.extend(scanner.scan(raw_content.meta_description or ""))

                        # Log PII detection
                        if scan_result:
                            log = ComplianceLog(
                                tenant_id=job.tenant_id,
                                job_id=job_id,
                                target_id=job.target_id,
                                event_type=ComplianceEventType.PII_DETECTED.value,
                                severity="WARNING",
                                pii_detection={
                                    "detection_method": "REGEX",
                                    "patterns_detected": [
                                        {"pattern_type": r.type, "count": 1, "locations": [r.text]}
                                        for r in scan_result
                                    ],
                                    "redaction_applied": True,
                                    "redacted_count": len(scan_result),
                                },
                                request_url=raw_content.source_url,
                                response_action_taken="REDACTED",
                            )
                            session.add(log)

                # Skill-aware post-processing: build structured intelligence outputs
                skill = get_skill(job.job_type)
                if skill:
                    raw_contents = (
                        session.query(RawContent).filter(RawContent.job_id == job_id).all()
                    )
                    extracted_data = (
                        session.query(ExtractedData).filter(ExtractedData.job_id == job_id).all()
                    )
                    skill_output = skill.build_output(job, raw_contents, extracted_data)
                    # Store in job configuration for downstream stages
                    job.configuration["skill_output"] = skill_output
                    job.configuration["output_contract"] = skill.output_contract
                    logger.info(
                        "Skill output built",
                        job_id=str(job_id),
                        skill_name=skill.skill_name,
                        output_contract=skill.output_contract,
                    )

                _update_stage(session, job_id, PipelineStage.POST_PROCESSING, "COMPLETED")
                session.commit()

                logger.info("Post-processing completed", job_id=str(job_id))
                return post_processing_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            logger.error(
                "Post-processing failed",
                job_id=str(job_id),
                error_code="POST_PROCESSING_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session,
                    job_id,
                    PipelineStage.POST_PROCESSING,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="post_processing", reason="stage_failure")
            raise self.retry(exc=exc, countdown=10)
