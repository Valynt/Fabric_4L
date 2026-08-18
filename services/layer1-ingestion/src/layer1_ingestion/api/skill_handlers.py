"""Skill-specific ingestion route handlers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from value_fabric.shared.error_handling.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

from ..shared.database import get_db_from_context_sync
from ..shared.models import (
    AccountIntelligencePacket,
    JobStageDetail,
    JobStatus,
    PipelineStage,
    ScrapingJob,
    ScrapingJobType,
    ScrapingTarget,
    SourceCorpus,
    TargetStatus,
    TriggeredBy,
    create_scraping_job,
)
from ..skills import get_skill
from ._task_fallback import UnavailableTask, _build_task_unavailable_detail
from .dependencies import get_current_user_id, get_tenant_id
from .schemas.content_schemas import (
    AccountIntelligencePacketListResponse,
    AccountIntelligencePacketResponse,
    AccountIntelligencePacketSummary,
    SourceCorpusListResponse,
    SourceCorpusResponse,
    SourceCorpusSummary,
)
from .schemas.job_schemas import (
    CreateLicensingCompanyIntakeRequest,
    CreateProspectResearchRequest,
    SkillJobResponse,
)
from .target_handlers import _calculate_queue_position

logger = structlog.get_logger()

_MAX_LIST_LIMIT = 100
_DEFAULT_LIST_LIMIT = 20


try:
    from ..shared.otel_celery import build_celery_options
    from ..shared.tasks import process_scraping_job
except ImportError as exc:
    build_celery_options = None  # type: ignore[assignment]
    process_scraping_job = UnavailableTask("process_scraping_job", exc)


def _source_corpus_to_response(corpus: SourceCorpus) -> SourceCorpusResponse:
    """Convert a SourceCorpus DB model to its API response."""
    return SourceCorpusResponse(
        id=corpus.id,
        tenant_id=corpus.tenant_id,
        company_id=corpus.company_id,
        company_name=corpus.company_name,
        corpus_type=corpus.corpus_type,
        source_groups=corpus.source_groups or [],
        candidate_concepts=corpus.candidate_concepts or [],
        provenance=corpus.provenance or [],
        extraction_status=corpus.extraction_status,
        created_at=corpus.created_at,
        updated_at=corpus.updated_at,
    )


def _account_packet_to_response(
    packet: AccountIntelligencePacket,
) -> AccountIntelligencePacketResponse:
    """Convert an AccountIntelligencePacket DB model to its API response."""
    return AccountIntelligencePacketResponse(
        id=packet.id,
        tenant_id=packet.tenant_id,
        account_id=packet.account_id,
        account_name=packet.account_name,
        packet_type=packet.packet_type,
        company_profile=packet.company_profile or {},
        observed_signals=packet.observed_signals or [],
        likely_pain_areas=packet.likely_pain_areas or [],
        likely_stakeholders=packet.likely_stakeholders or [],
        source_references=packet.source_references or [],
        confidence_summary=packet.confidence_summary or {},
        next_recommended_events=packet.next_recommended_events or [],
        created_at=packet.created_at,
        updated_at=packet.updated_at,
    )


def _create_skill_job(
    db: Session,
    org_id: UUID,
    user_id: UUID,
    target_id: UUID,
    job_type: ScrapingJobType,
    entity_name: str,
    entity_id: str | None,
    priority: int,
    override_config: dict[str, Any] | None,
) -> ScrapingJob:
    """Create and queue a skill-aware scraping job."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )
    if not target:
        raise NotFoundError(message="Target not found")

    if target.status != TargetStatus.ACTIVE.value:
        raise ConflictError(message=f"Target is not active (status: {target.status})")

    skill = get_skill(job_type.value)
    if not skill:
        raise ValidationError(message=str(f"Unknown job_type: {job_type.value}"))

    configuration = {
        "target_id": str(target.id),
        "target_name": target.name,
        "url": target.url,
        "target_type": target.target_type,
        "job_type": job_type.value,
        (
            "company_name"
            if job_type == ScrapingJobType.LICENSING_COMPANY_INTAKE
            else "account_name"
        ): entity_name,
        (
            "company_id"
            if job_type == ScrapingJobType.LICENSING_COMPANY_INTAKE
            else "account_id"
        ): entity_id,
        "extraction_config": target.extraction_config,
        "browser_config": target.browser_config,
        "rate_limit": target.rate_limit,
        "compliance": target.compliance,
        "proxy_config": target.proxy_config,
        "authentication": target.authentication,
        "override_config": override_config,
    }

    job = create_scraping_job(
        tenant_id=org_id,
        target_id=target_id,
        created_by=user_id,
        configuration=configuration,
        priority=priority,
        triggered_by=TriggeredBy.API,
        correlation_id=str(uuid4()),
    )
    job.job_type = job_type.value
    job.skill_name = skill.skill_name
    job.target_entity_id = entity_id
    job.target_entity_type = skill.config.target_entity_type
    job.output_contract = skill.output_contract
    job.downstream_events = skill.downstream_events

    db.add(job)
    db.commit()
    db.refresh(job)

    for stage in PipelineStage:
        stage_detail = JobStageDetail(
            job_id=job.id, tenant_id=org_id, stage=stage.value, status="PENDING"
        )
        db.add(stage_detail)

    job.status = JobStatus.QUEUED.value
    db.commit()
    process_scraping_job.apply_async(
        args=[str(job.id), str(job.tenant_id)],
        **(build_celery_options() or {}),
    )

    logger.info(
        "Queued skill-aware job",
        job_id=str(job.id),
        job_type=job_type.value,
        skill_name=skill.skill_name,
    )
    return job


async def create_licensing_company_intake_job(
    request: CreateLicensingCompanyIntakeRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Create a skill-aware job for licensing company ontology intake."""
    job = _create_skill_job(
        db=db,
        org_id=org_id,
        user_id=user_id,
        target_id=request.target_id,
        job_type=ScrapingJobType.LICENSING_COMPANY_INTAKE,
        entity_name=request.company_name,
        entity_id=request.company_id,
        priority=request.priority,
        override_config=request.override_config,
    )

    queue_position = _calculate_queue_position(db, org_id, job.created_at)

    return SkillJobResponse(
        job_id=job.id,
        status=JobStatus.QUEUED.value,
        job_type=job.job_type,
        skill_name=job.skill_name or "",
        queue_position=queue_position,
        queue_position_metadata={
            "calculation": "count_queued_jobs_created_before_or_at_current_job",
            "scope": "organization",
        },
    )


async def create_prospect_research_job(
    request: CreateProspectResearchRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Create a skill-aware job for prospect research."""
    job = _create_skill_job(
        db=db,
        org_id=org_id,
        user_id=user_id,
        target_id=request.target_id,
        job_type=ScrapingJobType.PROSPECT_RESEARCH,
        entity_name=request.account_name,
        entity_id=request.account_id,
        priority=request.priority,
        override_config=request.override_config,
    )

    queue_position = _calculate_queue_position(db, org_id, job.created_at)

    return SkillJobResponse(
        job_id=job.id,
        status=JobStatus.QUEUED.value,
        job_type=job.job_type,
        skill_name=job.skill_name or "",
        queue_position=queue_position,
        queue_position_metadata={
            "calculation": "count_queued_jobs_created_before_or_at_current_job",
            "scope": "organization",
        },
    )


async def get_source_corpus(
    corpus_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve a SourceCorpus by ID."""
    corpus = (
        db.query(SourceCorpus)
        .filter(SourceCorpus.id == corpus_id, SourceCorpus.tenant_id == org_id)
        .first()
    )
    if not corpus:
        raise NotFoundError(message="Corpus not found")
    return _source_corpus_to_response(corpus)


async def get_account_intelligence_packet(
    packet_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve an AccountIntelligencePacket by ID."""
    packet = (
        db.query(AccountIntelligencePacket)
        .filter(
            AccountIntelligencePacket.id == packet_id,
            AccountIntelligencePacket.tenant_id == org_id,
        )
        .first()
    )
    if not packet:
        raise NotFoundError(message="Intelligence packet not found")
    return _account_packet_to_response(packet)


async def get_job_skill_output(
    job_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve the skill-specific output for a completed job."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )
    if not job:
        raise NotFoundError(message="Job not found")

    if not job.skill_name:
        raise NotFoundError(message="Job has no skill output")

    if job.output_contract == "SourceCorpus":
        corpus = (
            db.query(SourceCorpus)
            .filter(SourceCorpus.job_id == job_id, SourceCorpus.tenant_id == org_id)
            .first()
        )
        if not corpus:
            raise NotFoundError(message="SourceCorpus not yet available")
        return {
            "output_contract": "SourceCorpus",
            "data": _source_corpus_to_response(corpus).model_dump(),
        }

    if job.output_contract == "AccountIntelligencePacket":
        packet = (
            db.query(AccountIntelligencePacket)
            .filter(
                AccountIntelligencePacket.job_id == job_id,
                AccountIntelligencePacket.tenant_id == org_id,
            )
            .first()
        )
        if not packet:
            raise NotFoundError(message="AccountIntelligencePacket not yet available")
        return {
            "output_contract": "AccountIntelligencePacket",
            "data": _account_packet_to_response(packet).model_dump(),
        }

    raise ValidationError(
        message=str(f"Unknown output_contract: {job.output_contract}")
    )


def _corpus_to_summary(corpus: SourceCorpus) -> SourceCorpusSummary:
    source_count = sum(g.get("count", 0) for g in (corpus.source_groups or []))
    return SourceCorpusSummary(
        id=corpus.id,
        company_name=corpus.company_name,
        company_id=corpus.company_id,
        corpus_type=corpus.corpus_type,
        source_count=source_count,
        extraction_status=corpus.extraction_status,
        created_at=corpus.created_at,
    )


def _packet_to_summary(
    packet: AccountIntelligencePacket,
) -> AccountIntelligencePacketSummary:
    signals = packet.observed_signals or []
    high_conf = sum(1 for s in signals if s.get("confidence") == "high")
    return AccountIntelligencePacketSummary(
        id=packet.id,
        account_name=packet.account_name,
        account_id=packet.account_id,
        packet_type=packet.packet_type,
        observed_signal_count=len(signals),
        high_confidence_signal_count=high_conf,
        created_at=packet.created_at,
    )


async def list_source_corpora(
    company_id: str | None = Query(default=None),
    job_id: UUID | None = Query(default=None),
    extraction_status: str | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIST_LIMIT, ge=1, le=_MAX_LIST_LIMIT),
    cursor: str | None = Query(
        default=None,
        description="ISO-8601 created_at of last seen item for cursor pagination",
    ),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """List SourceCorpus records for the authenticated tenant."""
    q = db.query(SourceCorpus).filter(SourceCorpus.tenant_id == org_id)

    if company_id:
        q = q.filter(SourceCorpus.company_id == company_id)
    if job_id:
        q = q.filter(SourceCorpus.job_id == job_id)
    if extraction_status:
        q = q.filter(SourceCorpus.extraction_status == extraction_status)
    if created_after:
        q = q.filter(SourceCorpus.created_at >= created_after)
    if created_before:
        q = q.filter(SourceCorpus.created_at <= created_before)
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            q = q.filter(SourceCorpus.created_at < cursor_dt)
        except ValueError:
            raise BadRequestError(
                message="Invalid cursor format; expected ISO-8601 datetime"
            )

    total = q.count()
    items = q.order_by(SourceCorpus.created_at.desc()).limit(limit).all()

    next_cursor = None
    if len(items) == limit and items:
        next_cursor = items[-1].created_at.isoformat()

    return SourceCorpusListResponse(
        items=[_corpus_to_summary(c) for c in items],
        total=total,
        limit=limit,
        next_cursor=next_cursor,
    )


async def get_source_corpus_detail(
    corpus_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve a SourceCorpus by ID including full provenance."""
    corpus = (
        db.query(SourceCorpus)
        .filter(SourceCorpus.id == corpus_id, SourceCorpus.tenant_id == org_id)
        .first()
    )
    if not corpus:
        raise NotFoundError(message="SourceCorpus not found")
    return _source_corpus_to_response(corpus)


async def list_account_intelligence_packets(
    account_id: str | None = Query(default=None),
    job_id: UUID | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIST_LIMIT, ge=1, le=_MAX_LIST_LIMIT),
    cursor: str | None = Query(
        default=None,
        description="ISO-8601 created_at of last seen item for cursor pagination",
    ),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """List AccountIntelligencePacket records for the authenticated tenant."""
    q = db.query(AccountIntelligencePacket).filter(
        AccountIntelligencePacket.tenant_id == org_id
    )

    if account_id:
        q = q.filter(AccountIntelligencePacket.account_id == account_id)
    if job_id:
        q = q.filter(AccountIntelligencePacket.job_id == job_id)
    if created_after:
        q = q.filter(AccountIntelligencePacket.created_at >= created_after)
    if created_before:
        q = q.filter(AccountIntelligencePacket.created_at <= created_before)
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            q = q.filter(AccountIntelligencePacket.created_at < cursor_dt)
        except ValueError:
            raise BadRequestError(
                message="Invalid cursor format; expected ISO-8601 datetime"
            )

    total = q.count()
    items = q.order_by(AccountIntelligencePacket.created_at.desc()).limit(limit).all()

    next_cursor = None
    if len(items) == limit and items:
        next_cursor = items[-1].created_at.isoformat()

    return AccountIntelligencePacketListResponse(
        items=[_packet_to_summary(p) for p in items],
        total=total,
        limit=limit,
        next_cursor=next_cursor,
    )


async def get_account_intelligence_packet_detail(
    packet_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve an AccountIntelligencePacket by ID including full source references."""
    packet = (
        db.query(AccountIntelligencePacket)
        .filter(
            AccountIntelligencePacket.id == packet_id,
            AccountIntelligencePacket.tenant_id == org_id,
        )
        .first()
    )
    if not packet:
        raise NotFoundError(message="AccountIntelligencePacket not found")
    return _account_packet_to_response(packet)
