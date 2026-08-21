"""Pure, stateless helper functions for the Celery task module.

These helpers were extracted from ``layer1_ingestion.shared.tasks`` to keep that
module focused on Celery task registration and orchestration. Each helper here is
pure or depends only on the database session models, has no dependency on Celery
or the task module globals, and is re-exported by ``tasks`` so that both bare-name
callers and ``from layer1_ingestion.shared.tasks import ...`` consumers keep working
unchanged.
"""

import asyncio
from urllib.parse import urlparse

from jsonschema import Draft7Validator

from .models import JobStageDetail, ScrapingTarget


def _domain_class(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if not host:
        return "unknown"
    if host.endswith(".gov") or host.endswith(".edu"):
        return "regulated"
    if host.endswith(".internal") or host.endswith(".local"):
        return "internal"
    return "public"


def _run_async(coro):
    # In a Celery worker there is no running event loop, so run the coroutine
    # to completion. When called from an async test context (e.g. pytest-asyncio)
    # with a running loop, return the coroutine so the caller can await it.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return coro


def _is_stage_already_completed(session, job_id, stage):
    """Check if stage is already completed (idempotency)."""
    existing_stage = (
        session.query(JobStageDetail)
        .filter(
            JobStageDetail.job_id == job_id,
            JobStageDetail.stage == stage.value,
        )
        .first()
    )
    return existing_stage and existing_stage.status == "COMPLETED"


def _get_target_config(session, job) -> dict:
    """Get target configuration from job."""
    target_config = {}
    if job.target_id:
        target = session.query(ScrapingTarget).get(job.target_id)
        if target:
            target_config = target.extraction_config or {}
    return target_config


def _extract_unified_crawl_result(fast_result, crawl_result, final_path):
    """Extract unified crawl result from fast or browser path."""
    if fast_result and final_path in ("fast",):
        return (
            fast_result.url,
            fast_result.status_code,
            fast_result.headers,
            fast_result.html or "",
            fast_result.title,
            fast_result.fetch_time_ms,
        )
    elif crawl_result:
        return (
            crawl_result.final_url,
            crawl_result.status_code,
            crawl_result.headers,
            crawl_result.html_content or "",
            crawl_result.title or "",
            crawl_result.duration_ms,
        )
    return "", None, {}, "", "", 0


def _validate_payload_against_schema(
    data: dict,
    schema: dict,
) -> tuple[bool, list[dict], list[str], list[str]]:
    """Validate *data* against a JSON Schema *schema*.

    Returns:
        (schema_valid, errors, required_present, required_missing)

    *errors* is a list of dicts with keys ``path``, ``message``, ``validator``
    so callers can persist them directly into ``ExtractedData.validation_errors``.
    """
    validator = Draft7Validator(schema)
    raw_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))

    errors = [
        {
            "path": ".".join(str(p) for p in err.absolute_path) or "$",
            "message": err.message,
            "validator": err.validator,
        }
        for err in raw_errors
    ]

    # Determine which required fields are present / missing
    required_fields: list[str] = schema.get("required", [])
    required_present = [f for f in required_fields if f in data]
    required_missing = [f for f in required_fields if f not in data]

    return len(errors) == 0, errors, required_present, required_missing
