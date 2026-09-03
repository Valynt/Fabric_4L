"""Storage stage task.

Submodule of ``layer1_ingestion.shared.tasks`` (split from the former megafile).
"""

from datetime import UTC, datetime
from uuid import UUID

from value_fabric.shared.error_handling import sanitize_log_error

from ...metrics.prometheus_metrics import get_metrics
from ...shared.otel_celery import start_celery_span
from ..database import get_db_session
from ..models import (
    AccountIntelligencePacket,
    ExtractedData,
    JobStatus,
    PipelineStage,
    RawContent,
    ScrapingJob,
    SourceCorpus,
)
from ..task_contracts import storage_stageResult
from ..tasks import (
    _update_stage,
)
from .tasks_bootstrap import celery_app, logger


@celery_app.task(name="layer1_ingestion.shared.tasks.storage_stage", bind=True, max_retries=3)
def storage_stage(self, prev_result: dict, tenant_id: str):
    """Stage 8: Storage (save to database, update references).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting storage stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.storage",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _update_stage(session, job_id, PipelineStage.STORAGE, "RUNNING")
                job.status = JobStatus.STORING.value
                job.progress_stage = PipelineStage.STORAGE.value
                session.commit()

                config = job.configuration
                raw_content_id = config.get("raw_content_id")

                if raw_content_id:
                    raw_content = session.query(RawContent).get(UUID(raw_content_id))
                    if raw_content:
                        extraction_started_at = datetime.now(UTC)
                        # Create ExtractedData record
                        extracted = ExtractedData(
                            job_id=job_id,
                            tenant_id=job.tenant_id,
                            target_id=job.target_id,
                            raw_content_id=raw_content.id,
                            extraction_method=config.get("extraction_config", {}).get(
                                "method", "DETERMINISTIC"
                            ),
                            extraction_time_ms=None,
                            data={
                                "title": raw_content.meta_title,
                                "description": raw_content.meta_description,
                                "url": raw_content.source_url,
                            },
                            provenance_source_url=raw_content.source_url,
                            storage_path=raw_content.storage_html_path,
                            format="JSON",
                        )
                        extracted.extraction_time_ms = int(
                            (datetime.now(UTC) - extraction_started_at).total_seconds() * 1000
                        )
                        session.add(extracted)
                        session.flush()

                        # Update references
                        raw_content.extracted_data_id = extracted.id
                        raw_content.processing_status = "EXTRACTED"

                        job.results_extracted_record_count += 1
                        job.results_storage_bytes_used += raw_content.source_content_length or 0

                # Skill-aware storage: persist structured intelligence output
                skill_output = config.get("skill_output")
                output_contract = config.get("output_contract")
                if skill_output and output_contract:
                    if output_contract == "SourceCorpus":
                        # Idempotent: skip if a SourceCorpus already exists for this job
                        existing_corpus = (
                            session.query(SourceCorpus)
                            .filter(
                                SourceCorpus.job_id == job_id,
                                SourceCorpus.tenant_id == job.tenant_id,
                            )
                            .first()
                        )
                        if existing_corpus:
                            logger.info(
                                "SourceCorpus already exists (idempotent retry)",
                                job_id=str(job_id),
                                corpus_id=str(existing_corpus.id),
                            )
                        else:
                            corpus = SourceCorpus(
                                tenant_id=job.tenant_id,
                                company_id=skill_output.get("company_id"),
                                company_name=skill_output.get("company_name", "Unknown"),
                                corpus_type=skill_output.get(
                                    "corpus_type", "licensing_company_ontology_seed"
                                ),
                                source_groups=skill_output.get("source_groups", []),
                                candidate_concepts=skill_output.get("candidate_concepts", []),
                                provenance=skill_output.get("provenance", []),
                                extraction_status=skill_output.get(
                                    "extraction_status", "ready_for_extraction"
                                ),
                                job_id=job_id,
                            )
                            session.add(corpus)
                            session.flush()
                            logger.info(
                                "SourceCorpus stored",
                                job_id=str(job_id),
                                corpus_id=str(corpus.id),
                                company_name=corpus.company_name,
                            )
                    elif output_contract == "AccountIntelligencePacket":
                        # Idempotent: skip if a packet already exists for this job
                        existing_packet = (
                            session.query(AccountIntelligencePacket)
                            .filter(
                                AccountIntelligencePacket.job_id == job_id,
                                AccountIntelligencePacket.tenant_id == job.tenant_id,
                            )
                            .first()
                        )
                        if existing_packet:
                            logger.info(
                                "AccountIntelligencePacket already exists (idempotent retry)",
                                job_id=str(job_id),
                                packet_id=str(existing_packet.id),
                            )
                        else:
                            packet = AccountIntelligencePacket(
                                tenant_id=job.tenant_id,
                                account_id=skill_output.get("account_id"),
                                account_name=skill_output.get("account_name", "Unknown"),
                                packet_type=skill_output.get("packet_type", "prospect_research"),
                                company_profile=skill_output.get("company_profile", {}),
                                observed_signals=skill_output.get("observed_signals", []),
                                likely_pain_areas=skill_output.get("likely_pain_areas", []),
                                likely_stakeholders=skill_output.get("likely_stakeholders", []),
                                source_references=skill_output.get("source_references", []),
                                confidence_summary=skill_output.get("confidence_summary", {}),
                                next_recommended_events=skill_output.get(
                                    "next_recommended_events", []
                                ),
                                job_id=job_id,
                            )
                            session.add(packet)
                            session.flush()
                            logger.info(
                                "AccountIntelligencePacket stored",
                                job_id=str(job_id),
                                packet_id=str(packet.id),
                                account_name=packet.account_name,
                            )

                _update_stage(session, job_id, PipelineStage.STORAGE, "COMPLETED")
                session.commit()

                logger.info("Storage completed", job_id=str(job_id))
                return storage_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            logger.error(
                "Storage failed",
                job_id=str(job_id),
                error_code="STORAGE_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session, job_id, PipelineStage.STORAGE, "FAILED", sanitize_log_error(exc)[:200]
                )
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="storage", reason="stage_failure")
            raise self.retry(exc=exc, countdown=10)
