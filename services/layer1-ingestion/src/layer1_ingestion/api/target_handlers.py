"""Scraping target route handlers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy.exc
import structlog
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from value_fabric.shared.error_handling.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

from ..compliance.url_safety import URLSafetyError, validate_url_safety
from ..crawler.decision_store import CrawlDecisionRepository
from ..shared.database import get_db_from_context_sync
from ..shared.models import (
    ExtractionMethod,
    JobStageDetail,
    JobStatus,
    PipelineStage,
    ScrapingJob,
    ScrapingTarget,
    TargetStatus,
    TriggeredBy,
    create_scraping_job,
    create_scraping_target,
)
from .dependencies import get_current_user_id, get_current_user_roles, get_tenant_id
from .schemas.content_schemas import CrawlDecisionSummary
from .schemas.target_schemas import (
    CreateTargetRequest,
    ExecuteTargetRequest,
    ExecuteTargetResponse,
    ScrapingTargetDetail,
    ScrapingTargetSummary,
    TargetListResponse,
    UpdateTargetRequest,
    ValidateTargetRequest,
    ValidateTargetResponse,
    ValidationWarning,
)
from .target_config import apply_target_config_updates, build_create_target_configs

logger = structlog.get_logger()


# Roles that may bypass per-user ownership checks within a tenant.
_ADMIN_ROLES = frozenset({"admin", "tenant_admin", "super_admin"})


def _require_target_ownership(
    target: ScrapingTarget,
    user_id: UUID,
    roles: list[str],
) -> None:
    """Verify the requesting user owns the target or is a tenant admin.

    Raises NotFoundError (not Forbidden) to avoid leaking target existence.
    """
    if any(role in _ADMIN_ROLES for role in roles):
        return
    if str(target.created_by) == str(user_id):
        return
    raise NotFoundError(message="Target not found")


def _build_task_unavailable_detail() -> dict[str, str]:
    return {
        "code": "SERVICE_UNAVAILABLE",
        "message": (
            "Background processing is temporarily unavailable. "
            "Please retry shortly or contact support if the issue persists."
        ),
    }


class _UnavailableTask:
    """Fail closed when task infrastructure is unavailable."""

    def __init__(self, task_name: str, import_error: ImportError) -> None:
        self.task_name = task_name
        self.import_error = import_error

    def apply_async(self, *args: Any, **kwargs: Any) -> None:
        logger.error(
            "background_task_unavailable",
            task_name=self.task_name,
            error_type=type(self.import_error).__name__,
            error=str(self.import_error),
            exc_info=self.import_error,
        )
        raise HTTPException(status_code=503, detail=_build_task_unavailable_detail())


try:
    from ..shared.otel_celery import build_celery_options
    from ..shared.tasks import process_scraping_job
except ImportError as exc:
    build_celery_options = None  # type: ignore[assignment]
    process_scraping_job = _UnavailableTask("process_scraping_job", exc)


def _url_safety_error_payload(reason_code: str) -> dict[str, str]:
    return {
        "error": "url_validation_failed",
        "reason_code": reason_code,
        "message": "URL blocked by compliance policy",
    }


async def list_targets(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: TargetStatus | None = Query(None),
    search: str | None = Query(None, description="Search in name, description, url"),
    tags: list[str] | None = Query(None),
    sort_by: str = Query(
        default="created_at", regex="^(created_at|updated_at|last_success_at|name)$"
    ),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """List all scraping targets for the organization."""
    query = db.query(ScrapingTarget).filter(ScrapingTarget.tenant_id == org_id)

    if status:
        query = query.filter(ScrapingTarget.status == status.value)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (ScrapingTarget.name.ilike(search_filter))
            | (ScrapingTarget.description.ilike(search_filter))
            | (ScrapingTarget.url.ilike(search_filter))
        )

    if tags:
        for tag in tags:
            query = query.filter(ScrapingTarget.tags.contains([tag]))

    total = query.count()
    total_pages = (total + limit - 1) // limit

    sort_column = getattr(ScrapingTarget, sort_by)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    offset = (page - 1) * limit
    targets = query.offset(offset).limit(limit).all()

    return TargetListResponse(
        data=[
            ScrapingTargetSummary(
                id=t.id,  # type: ignore[arg-type]
                name=t.name,  # type: ignore[arg-type]
                url=t.url,  # type: ignore[arg-type]
                target_type=t.target_type,  # type: ignore[arg-type]
                source_category=t.source_category,  # type: ignore[arg-type]
                status=t.status,  # type: ignore[arg-type]
                created_at=t.created_at,  # type: ignore[arg-type]
                updated_at=t.updated_at,  # type: ignore[arg-type]
                last_success_at=t.last_success_at,  # type: ignore[arg-type]
                success_count=t.success_count,  # type: ignore[arg-type]
                error_count=t.error_count,  # type: ignore[arg-type]
                average_execution_time_ms=t.average_execution_time_ms,  # type: ignore[arg-type]
                tags=t.tags or [],
            )
            for t in targets
        ],
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
        },
    )


async def create_target(
    request: CreateTargetRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Create a new scraping target."""
    try:
        validated = validate_url_safety(
            request.url, allowlist_domains=request.compliance.domain_allowlist
        )
    except URLSafetyError as exc:
        raise ValidationError(
            message=str(_url_safety_error_payload(exc.reason_code))
        ) from exc

    if (
        request.extraction_config.method == ExtractionMethod.AI_LLM
        and not request.extraction_config.llm_provider
    ):
        raise ValidationError(message="llm_provider is required when method is AI_LLM")

    target_configs = build_create_target_configs(request)

    target = create_scraping_target(
        tenant_id=org_id,
        name=request.name,
        url=validated.normalized_url,
        target_type=request.target_type,
        created_by=user_id,
        description=request.description,
        extraction_config=target_configs["extraction_config"],
        browser_config=target_configs["browser_config"],
        schedule=target_configs["schedule"],
        rate_limit=target_configs["rate_limit"],
        compliance=target_configs["compliance"],
        proxy_config=target_configs["proxy_config"],
        tags=request.tags,
    )

    if target_configs["authentication"]:
        target.authentication = target_configs["authentication"]

    db.add(target)
    db.commit()
    db.refresh(target)

    logger.info("Created scraping target", target_id=str(target.id), name=target.name)

    return _target_to_detail(target)


async def get_target(
    target_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    roles: list[str] = Depends(get_current_user_roles),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get detailed information about a specific target."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message="Target not found")

    _require_target_ownership(target, user_id, roles)

    return _target_to_detail(target)


async def update_target(
    target_id: UUID,
    request: UpdateTargetRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    roles: list[str] = Depends(get_current_user_roles),
    db: Session = Depends(get_db_from_context_sync),
):
    """Update a scraping target."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message="Target not found")

    _require_target_ownership(target, user_id, roles)

    active_jobs = (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.target_id == target_id,
            ScrapingJob.status.in_(
                [
                    JobStatus.PENDING.value,
                    JobStatus.QUEUED.value,
                    JobStatus.VALIDATING.value,
                    JobStatus.BROWSER_ACQUIRING.value,
                    JobStatus.NAVIGATING.value,
                    JobStatus.EXTRACTING.value,
                    JobStatus.TRANSFORMING.value,
                    JobStatus.STORING.value,
                ]
            ),
        )
        .count()
    )

    if active_jobs > 0:
        raise ConflictError(
            message=f"Cannot modify target with {active_jobs} active jobs"
        )

    if request.name is not None:
        target.name = request.name
    if request.description is not None:
        target.description = request.description
    if request.target_type is not None:
        target.target_type = request.target_type.value
    if request.status is not None:
        target.status = request.status.value
    if request.tags is not None:
        target.tags = request.tags
    apply_target_config_updates(target, request)

    target.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(target)

    logger.info("Updated scraping target", target_id=str(target.id))

    return _target_to_detail(target)


async def delete_target(
    target_id: UUID,
    force: bool = Query(default=False, description="Hard delete if no jobs exist"),
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    roles: list[str] = Depends(get_current_user_roles),
    db: Session = Depends(get_db_from_context_sync),
):
    """Archive a scraping target (soft delete)."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message="Target not found")

    _require_target_ownership(target, user_id, roles)

    job_count = db.query(ScrapingJob).filter(ScrapingJob.target_id == target_id).count()

    if job_count > 0:
        target.status = TargetStatus.ARCHIVED.value
        logger.info("Archived scraping target", target_id=str(target_id))
    elif force:
        db.delete(target)
        logger.info("Hard deleted scraping target", target_id=str(target_id))
    else:
        # Soft-delete is default when no jobs exist and force is not set
        target.status = TargetStatus.ARCHIVED.value
        logger.info("Archived scraping target", target_id=str(target_id))

    return None


async def validate_target(
    target_id: UUID,
    request: ValidateTargetRequest,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Validate target configuration without executing."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message="Target not found")

    errors = []
    warnings = []
    robots_check = None

    test_url = request.test_url or target.url
    try:
        validate_url_safety(
            test_url,
            allowlist_domains=(target.compliance or {}).get("domain_allowlist"),
        )
    except URLSafetyError as exc:
        errors.append(
            ValidationError(
                field="url",
                message=f"URL blocked by compliance policy ({exc.reason_code})",
            )
        )

    if request.validate_schema and target.extraction_config.get("extraction_schema"):
        schema = target.extraction_config.get("extraction_schema")
        if not isinstance(schema, dict):
            errors.append(
                ValidationError(
                    field="extraction_schema",
                    message="Extraction schema must be a valid JSON object",
                )
            )

    if request.validate_robots_txt:
        from urllib.parse import urlparse

        from ..compliance.robots_checker import RobotsChecker

        parsed = urlparse(test_url)
        checker = RobotsChecker(tenant_id=str(org_id))
        domain = parsed.netloc
        allowed, reason, rules = await checker.check_url(domain, test_url)
        robots_check = {
            "allowed": allowed,
            "crawl_delay": rules.get("crawl_delay") if rules else None,
        }
        if not allowed:
            warnings.append(
                ValidationWarning(
                    field="robots_txt",
                    message=reason or "URL is disallowed by robots.txt",
                )
            )

    valid = len(errors) == 0

    return ValidateTargetResponse(
        valid=valid, errors=errors, warnings=warnings, robots_txt_check=robots_check
    )


async def execute_target(
    target_id: UUID,
    request: ExecuteTargetRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Trigger immediate execution of a target with idempotency support."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message="Target not found")

    if target.status != TargetStatus.ACTIVE.value:
        raise ConflictError(message=f"Target is not active (status: {target.status})")

    idempotency_key = request.idempotency_key or None
    existing_response, placeholder = await _check_idempotency_key(
        idempotency_key, org_id, target_id, db
    )
    if existing_response:
        return existing_response

    configuration = _build_job_configuration(target, request.override_config)

    correlation_id = str(uuid4())
    job = create_scraping_job(
        tenant_id=org_id,
        target_id=target_id,
        created_by=user_id,
        configuration=configuration,
        priority=request.priority,
        triggered_by=TriggeredBy.API,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
    )

    db.add(job)
    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        # Durable dedup backstop: idx_scraping_jobs_tenant_idempotency
        # (tenant_id, idempotency_key) fired — a concurrent request created the
        # job first. Redis-only dedup can lose entries on a flush; the database
        # is the authoritative idempotency boundary (V1-TENANCY-010 / S-2).
        existing_job = None
        if idempotency_key:
            existing_job = (
                db.query(ScrapingJob)
                .filter(
                    ScrapingJob.tenant_id == org_id,
                    ScrapingJob.idempotency_key == idempotency_key,
                )
                .first()
            )
        if existing_job is not None:
            if existing_job.target_id != target_id:
                if placeholder:
                    _delete_idempotency_key(org_id, target_id, idempotency_key)
                raise ConflictError(
                    message="Idempotency key is already in use for another target"
                )
            logger.info(
                "Idempotency key hit at database boundary, returning existing job",
                idempotency_key=idempotency_key,
                job_id=str(existing_job.id),
            )
            return ExecuteTargetResponse(
                job_id=existing_job.id,
                status=existing_job.status,
                estimated_start_time=existing_job.started_at,
                queue_position=None,
                queue_position_metadata=None,
            )
        raise
    db.refresh(job)

    if idempotency_key:
        _update_idempotency_key(org_id, target_id, idempotency_key, job.id)

    try:
        _initialize_pipeline_stages(job.id, org_id, db)
        job.status = JobStatus.QUEUED.value
        db.commit()
    except sqlalchemy.exc.SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "failed_to_persist_queued_job",
            job_id=str(job.id),
            tenant_id=str(org_id),
            error=str(exc),
        )
        # The job row was already committed before stage initialization; mark it
        # failed so it is not left in an ambiguous default status.
        job.status = JobStatus.FAILED.value
        db.commit()
        # Remove the placeholder so the caller can retry; if we leave it, the
        # short TTL will still expire within 60 seconds, but explicit cleanup
        # gives a faster recovery path.
        if idempotency_key and placeholder:
            _delete_idempotency_key(org_id, target_id, idempotency_key)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Failed to queue scraping job",
            },
        ) from exc

    process_scraping_job.apply_async(
        args=[str(job.id), str(job.tenant_id)],
        **(build_celery_options() or {}),
    )

    logger.info("Queued scraping job", job_id=str(job.id), target_id=str(target_id))

    return ExecuteTargetResponse(
        job_id=job.id,
        status=JobStatus.QUEUED.value,
        queue_position=_calculate_queue_position(db, org_id, job.created_at),
        queue_position_metadata={
            "calculation": "count_queued_jobs_created_before_or_at_current_job",
            "scope": "organization",
        },
        estimated_start_time=None,
    )


async def _check_idempotency_key(
    idempotency_key: str | None,
    org_id: UUID,
    target_id: UUID,
    db: Session,
) -> tuple[ExecuteTargetResponse | None, str | None]:
    """Check idempotency key and return existing job response if found.

    Returns a tuple of (response, placeholder). If placeholder is not None,
    the caller owns it and must either replace it with a real job_id via
    _update_idempotency_key or delete it via _delete_idempotency_key on failure.
    """
    if not idempotency_key:
        return None, None

    idempotency_key_str = f"idempotency:{org_id}:{target_id}:{idempotency_key}"
    from ..shared.database import redis_client

    if not redis_client:
        return None, None

    try:
        job_id_placeholder = f"placeholder:{uuid4()}"
        # Use a short TTL for the placeholder so an orphaned placeholder (e.g.
        # request crash before the real job_id is written) expires quickly.
        set_result = redis_client.set(
            idempotency_key_str, job_id_placeholder, nx=True, ex=60
        )
    except Exception as exc:
        logger.warning(
            "idempotency_redis_set_failed",
            idempotency_key=idempotency_key,
            error=str(exc),
        )
        return None, None

    if set_result is not None:
        from ..metrics.prometheus_metrics import get_metrics

        metrics = get_metrics()
        if metrics and metrics.config.enabled:
            metrics.increment_idempotency_key_miss()
        return None, job_id_placeholder

    for attempt in range(5):
        try:
            existing_job_id = _decode_redis_value(
                redis_client.get(idempotency_key_str)
            )
        except Exception as exc:
            logger.warning(
                "idempotency_redis_get_failed",
                idempotency_key=idempotency_key,
                error=str(exc),
            )
            break
        if not existing_job_id or not existing_job_id.startswith("placeholder:"):
            break
        await asyncio.sleep(0.05 * (2**attempt))

    try:
        existing_job_id = _decode_redis_value(redis_client.get(idempotency_key_str))
    except Exception as exc:
        logger.warning(
            "idempotency_redis_get_failed",
            idempotency_key=idempotency_key,
            error=str(exc),
        )
        existing_job_id = None

    if existing_job_id and not existing_job_id.startswith("placeholder:"):
        logger.info(
            "Idempotency key hit, returning existing job",
            idempotency_key=idempotency_key,
            job_id=existing_job_id,
        )
        existing_job = db.query(ScrapingJob).get(UUID(existing_job_id))
        if existing_job and existing_job.tenant_id == org_id:
            from ..metrics.prometheus_metrics import get_metrics

            metrics = get_metrics()
            if metrics and metrics.config.enabled:
                metrics.increment_idempotency_key_hit()
            return ExecuteTargetResponse(
                job_id=UUID(existing_job_id),
                status=existing_job.status,
                estimated_start_time=existing_job.started_at,
                queue_position=None,
                queue_position_metadata=None,
            ), None
        try:
            redis_client.delete(idempotency_key_str)
        except Exception as exc:
            logger.warning(
                "idempotency_redis_delete_failed",
                idempotency_key=idempotency_key,
                error=str(exc),
            )

    if existing_job_id and existing_job_id.startswith("placeholder:"):
        raise ConflictError(
            message="A request with this idempotency key is already in progress"
        )

    return None, None


def _delete_idempotency_key(
    org_id: UUID, target_id: UUID, idempotency_key: str
) -> None:
    """Delete an idempotency key (used on failure before a real job_id exists)."""
    idempotency_key_str = f"idempotency:{org_id}:{target_id}:{idempotency_key}"
    from ..shared.database import redis_client

    if not redis_client:
        return

    try:
        redis_client.delete(idempotency_key_str)
    except Exception as exc:
        logger.warning(
            "idempotency_redis_delete_failed",
            idempotency_key=idempotency_key,
            error=str(exc),
        )


def _decode_redis_value(value: Any) -> str | None:
    """Normalize Redis client return values for idempotency comparisons."""
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _build_job_configuration(
    target: ScrapingTarget, override_config: dict[str, Any] | None
) -> dict[str, Any]:
    """Build configuration snapshot for job execution."""
    return {
        "target_id": str(target.id),
        "target_name": target.name,
        "url": target.url,
        "target_type": target.target_type,
        "extraction_config": target.extraction_config,
        "browser_config": target.browser_config,
        "rate_limit": target.rate_limit,
        "compliance": target.compliance,
        "proxy_config": target.proxy_config,
        "authentication": target.authentication,
        "override_config": override_config,
    }


def _update_idempotency_key(
    org_id: UUID, target_id: UUID, idempotency_key: str, job_id: UUID
) -> None:
    """Update idempotency key with actual job ID (TTL 24h)."""
    idempotency_key_str = f"idempotency:{org_id}:{target_id}:{idempotency_key}"
    from ..shared.database import redis_client

    if not redis_client:
        return

    try:
        redis_client.setex(idempotency_key_str, 86400, str(job_id))
    except Exception as exc:
        logger.warning(
            "idempotency_redis_update_failed",
            idempotency_key=idempotency_key,
            job_id=str(job_id),
            error=str(exc),
        )


def _initialize_pipeline_stages(job_id: UUID, org_id: UUID, db: Session) -> None:
    """Initialize pipeline stages for a job."""
    for stage in PipelineStage:
        stage_detail = JobStageDetail(
            job_id=job_id, tenant_id=org_id, stage=stage.value, status="PENDING"
        )
        db.add(stage_detail)


def _calculate_queue_position(db: Session, org_id: UUID, created_at: datetime) -> int:
    """Calculate queue position for a job."""
    return (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.tenant_id == org_id,
            ScrapingJob.status == JobStatus.QUEUED.value,
            ScrapingJob.created_at <= created_at,
        )
        .count()
    )


async def get_target_decisions(
    target_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get recent crawl decisions for a target's jobs."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message="Target not found")

    jobs = db.query(ScrapingJob).filter(ScrapingJob.target_id == target_id).all()
    job_ids = [str(j.id) for j in jobs]

    repo = CrawlDecisionRepository(db)
    all_decisions = []

    for job_id in job_ids[:5]:
        decisions = await repo.get_by_job(job_id, tenant_id=str(org_id), limit=20)
        all_decisions.extend(decisions)

    all_decisions.sort(key=lambda d: d.created_at, reverse=True)
    all_decisions = all_decisions[:limit]

    return [
        CrawlDecisionSummary(
            decision_id=UUID(d.decision_id),
            url=d.url,
            router_decision=d.router_decision,
            router_rule=d.router_rule,
            final_path=d.final_path,
            fallback_reason=d.fallback_reason,
            fetch_time_ms=d.fetch_time_ms,
            created_at=d.created_at,
        )
        for d in all_decisions
    ]


def _target_to_detail(target: ScrapingTarget) -> ScrapingTargetDetail:
    """Convert ScrapingTarget to ScrapingTargetDetail response."""
    return ScrapingTargetDetail(
        id=target.id,  # type: ignore[arg-type]
        tenant_id=target.tenant_id,  # type: ignore[arg-type]
        name=target.name,  # type: ignore[arg-type]
        description=target.description,  # type: ignore[arg-type]
        url=target.url,  # type: ignore[arg-type]
        url_pattern=target.url_pattern,  # type: ignore[arg-type]
        target_type=target.target_type,  # type: ignore[arg-type]
        source_category=target.source_category,  # type: ignore[arg-type]
        crawl_path=(target.extraction_config or {}).get("crawl_path", "browser"),
        status=target.status,  # type: ignore[arg-type]
        extraction_config=target.extraction_config or {},
        browser_config=target.browser_config or {},
        schedule=target.schedule,
        rate_limit=target.rate_limit or {},
        compliance=target.compliance or {},
        proxy_config=target.proxy_config or {},
        authentication=target.authentication,
        tags=target.tags or [],
        created_at=target.created_at,  # type: ignore[arg-type]
        updated_at=target.updated_at,  # type: ignore[arg-type]
        created_by=target.created_by,  # type: ignore[arg-type]
        last_success_at=target.last_success_at,  # type: ignore[arg-type]
        last_error_at=target.last_error_at,  # type: ignore[arg-type]
        success_count=target.success_count,  # type: ignore[arg-type]
        error_count=target.error_count,  # type: ignore[arg-type]
        average_execution_time_ms=target.average_execution_time_ms,  # type: ignore[arg-type]
    )
