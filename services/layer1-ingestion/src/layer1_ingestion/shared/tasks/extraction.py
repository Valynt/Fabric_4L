"""AI/LLM extraction stage task.

Submodule of ``layer1_ingestion.shared.tasks`` (split from the former megafile).
"""

import os
from uuid import UUID

import httpx
from value_fabric.shared.error_handling import sanitize_log_error

from ...metrics.prometheus_metrics import get_metrics
from ...skills import get_extraction_schema
from ..config import settings
from ..database import get_db_session
from ..models import (
    ExtractionMethod,
    PipelineStage,
    RawContent,
    ScrapingJob,
)
from ..otel_celery import start_celery_span
from ..task_contracts import ai_extraction_stageResult
from ..tasks import (
    _update_stage,
    _verify_l3_graph_population,
)
from .tasks_bootstrap import celery_app, logger
from ..tasks_helpers import (
    _run_async,
)

try:
    from value_fabric.shared.identity.jwt import encode_service_jwt
except ImportError:
    encode_service_jwt = None  # type: ignore

@celery_app.task(name="layer1_ingestion.shared.tasks.ai_extraction_stage", bind=True, max_retries=5)
def ai_extraction_stage(self, prev_result: dict, tenant_id: str):
    return _run_async(_ai_extraction_stage_async(self, prev_result, tenant_id))


async def _ai_extraction_stage_async(self, prev_result: dict, tenant_id: str):
    """Stage 5: AI/LLM Extraction (conditional based on config).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting AI extraction stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.ai_extraction",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                config = job.configuration
                extraction_config = config.get("extraction_config", {})
                method = extraction_config.get("method", "DETERMINISTIC")

                # Skill-aware extraction: override schema if a skill is configured
                skill_schema = get_extraction_schema(job.job_type)
                if skill_schema:
                    extraction_config = {**extraction_config, "extraction_schema": skill_schema}
                    job.configuration["extraction_config"] = extraction_config
                    logger.info(
                        "Using skill-specific extraction schema",
                        job_id=str(job_id),
                        skill_name=job.skill_name,
                    )

                if method == ExtractionMethod.DETERMINISTIC.value:
                    logger.info("Skipping AI extraction (deterministic mode)", job_id=str(job_id))
                    return ai_extraction_stageResult.model_validate(
                        {"success": True, "job_id": str(job_id), "skipped": True}
                    ).model_dump()

                _update_stage(session, job_id, PipelineStage.AI_EXTRACTION, "RUNNING")
                job.progress_stage = PipelineStage.AI_EXTRACTION.value
                session.commit()

                raw_content_id = config.get("raw_content_id")
                raw_content = (
                    session.query(RawContent).get(UUID(raw_content_id)) if raw_content_id else None
                )

                if not raw_content:
                    raise ValueError("Raw content not found for AI extraction")

                l2_url = settings.layer2_api_url
                extraction_model = extraction_config.get(
                    "model", os.getenv("EXTRACTION_MODEL", settings.openai_model)
                )
                extraction_payload = {
                    "content": raw_content.meta_title or "",
                    "content_type": "text",
                    "extraction_method": method.lower(),
                    "source_id": str(raw_content_id),
                    "source_version_id": str(raw_content_id),  # For L3 graph population tracking
                    "job_id": str(job_id),
                    "tenant_id": str(job.tenant_id),
                    "model_version": extraction_config.get("model_version", extraction_model),
                    "schema_version": extraction_config.get("schema_version", "1.0"),
                    "prompt_version": extraction_config.get(
                        "prompt_version", "entity_extraction_v1"
                    ),
                    "options": {
                        "model": extraction_model,
                        "temperature": extraction_config.get("temperature", 0.0),
                        "max_tokens": extraction_config.get("max_tokens", 4000),
                    },
                }
                # Pass skill-specific schema downstream if configured
                schema = extraction_config.get("extraction_schema")
                if schema:
                    extraction_payload["extraction_schema"] = schema

                # OPTIMIZATION: Use Celery for L2 dispatch when enabled (async queue-based processing)
                # Falls back to HTTP if Celery disabled or unavailable
                use_celery_dispatch = (
                    settings.use_celery_for_l2
                )  # Local flag to avoid race condition
                if use_celery_dispatch:
                    try:
                        # Import Celery for cross-service dispatch
                        from celery import Celery

                        # Create a Celery client pointing to L2's broker
                        l2_celery = Celery(
                            "layer2_extraction",
                            broker=settings.layer2_celery_broker_url,
                            backend=settings.layer2_celery_broker_url,
                        )

                        # Dispatch task to L2 Celery worker with extract-and-ingest
                        logger.info(
                            "Dispatching extract-and-ingest task to L2 Celery", job_id=str(job_id)
                        )
                        result = l2_celery.send_task(
                            "layer2_extraction.shared.tasks.run_extraction_task",
                            args=[
                                str(job_id),
                                job.source_url or "",
                                raw_content.meta_title or "",
                                extraction_payload,
                            ],
                            kwargs={
                                "mark_pipeline_complete": False,
                                "use_extract_and_ingest": True,
                            },
                        )

                        # Wait for result with timeout
                        extraction_result = result.get(timeout=300)
                        tokens_consumed = extraction_result.get("tokens_consumed", 0)
                        logger.info(
                            "L2 Celery extract-and-ingest completed",
                            job_id=str(job_id),
                            task_id=result.id,
                        )

                    except Exception as e:
                        logger.warning(
                            "L2 Celery dispatch failed, falling back to HTTP",
                            job_id=str(job_id),
                            error=repr(e),
                        )
                        # Fall through to HTTP fallback
                        use_celery_dispatch = False  # Disable for this run
                else:
                    logger.info("Using HTTP fallback for L2 extract-and-ingest", job_id=str(job_id))

                # HTTP fallback (extract-and-ingest endpoint for graph population)
                if not use_celery_dispatch:
                    # P1-001: Sign S2S JWT for L2 authentication
                    s2s_token = None
                    if encode_service_jwt is not None:
                        s2s_token = encode_service_jwt(
                            tenant_id=job.tenant_id,
                            sub="layer1-ingestion",
                            aud="layer2-extraction",
                        )

                    async def _call_l2():
                        request_headers = {
                            "Content-Type": "application/json",
                            "X-Tenant-ID": str(job.tenant_id),
                        }
                        if s2s_token:
                            request_headers["Authorization"] = f"Bearer {s2s_token}"
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            response = await client.post(
                                f"{l2_url}/v1/extract-and-ingest",
                                json=extraction_payload,
                                headers=request_headers,
                            )
                            response.raise_for_status()
                            return response.json()

                    try:
                        extraction_result = await _call_l2()
                        tokens_consumed = extraction_result.get("tokens_consumed", 0)
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code in (429, 503, 504):
                            logger.warning(
                                "L2 transient error, returning to queue via Celery retry",
                                job_id=str(job_id),
                                status=e.response.status_code,
                            )
                            raise self.retry(exc=e, countdown=15)
                        raise ValueError(
                            f"L2 extract-and-ingest failed: HTTP {e.response.status_code}: {e.response.text}"
                        )
                    except Exception as e:
                        logger.warning(
                            "L2 extract-and-ingest failed, retrying via Celery",
                            job_id=str(job_id),
                            error_code="L2_EXTRACTION_ERROR",
                        )
                        raise self.retry(exc=e, countdown=30)

                job.configuration["extraction_result"] = extraction_result

                # Verify L3 graph population from this source version
                l3_entity_count = await _verify_l3_graph_population(
                    tenant_id=str(job.tenant_id),
                    source_version_id=str(raw_content_id),
                )
                logger.info(
                    "L3 graph population verified",
                    job_id=str(job_id),
                    source_version_id=str(raw_content_id),
                    entities_in_graph=l3_entity_count,
                )

                _update_stage(session, job_id, PipelineStage.AI_EXTRACTION, "COMPLETED")
                job.resources_llm_tokens_consumed += tokens_consumed
                session.commit()

                logger.info(
                    "AI extraction completed",
                    job_id=str(job_id),
                    tokens_consumed=tokens_consumed,
                    entities_extracted=len(extraction_result.get("entities", [])),
                )
                return ai_extraction_stageResult.model_validate(
                    {
                        "success": True,
                        "job_id": str(job_id),
                        "tokens_consumed": tokens_consumed,
                        "entities_extracted": len(extraction_result.get("entities", [])),
                    }
                ).model_dump()

        except Exception as exc:
            if "Retry" in type(exc).__name__:
                raise
            logger.error(
                "AI extraction failed",
                job_id=str(job_id),
                error_code="AI_EXTRACTION_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session,
                    job_id,
                    PipelineStage.AI_EXTRACTION,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="ai_extraction", reason="stage_failure")
            raise self.retry(exc=exc, countdown=30)
