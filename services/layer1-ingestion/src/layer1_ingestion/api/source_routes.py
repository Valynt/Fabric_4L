"""Canonical source ingestion routes for Layer 1.

Implements the unified source intake boundary for Notes, Web/Search, Audio,
CRM, PDF, and Meeting source types. All sources converge on a single contract:
accept the raw artifact, store it immutably, produce a normalized document, and
emit a transactional outbox event for downstream extraction.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypeVar, cast

T = TypeVar("T", bound="BaseModel")


def _orm_to_response(model_class: type[T], instance: Any) -> T:
    """Build a Pydantic response model from a SQLAlchemy ORM instance.

    Handles UUID -> str and enum -> value coercion while keeping mypy happy
    because all values are passed as ``Any`` through ``**kwargs``.
    """
    kwargs: dict[str, Any] = {}
    for field_name in model_class.model_fields:
        value = getattr(instance, field_name, None)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, Enum) and not isinstance(value, str):
            value = value.value
        kwargs[field_name] = value
    return model_class(**kwargs)

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..orchestrator import PipelineCoordinator
from ..shared.consent_service import ConsentService
from ..shared.custody_policy import CustodyPolicyService
from ..shared.database import get_db_from_context_sync
from ..shared.models import (
    EventOutbox,
    IngestedSource,
    IngestionRunStatus,
    NormalizedDocument,
    OutboxStatus,
    SourceIngestionRun,
    SourceType,
    SourceVersion,
)

try:
    from value_fabric.shared.error_handling.exceptions import ConflictError, ValidationError
    from value_fabric.shared.llm_safety import InjectionSeverity, PromptGuard
    from value_fabric.shared.observability.logging import get_logger
except ImportError as e:
    raise ImportError(
        f"Failed to import from value_fabric.shared. Ensure packages/shared is in PYTHONPATH. Error: {e}"
    ) from e


logger = get_logger(__name__)
router = APIRouter()


# Lazy dependency imports to avoid circular imports with the main router module.
def _get_tenant_id(request: Request) -> uuid.UUID:
    from .main import get_tenant_id
    return get_tenant_id(request)


def _get_current_user_id(request: Request) -> uuid.UUID:
    from .main import get_current_user_id
    return get_current_user_id(request)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================


class SourceIntakeRequest(BaseModel):
    """Unified command for ingesting a source artifact.

    tenant_id, user_id, and authorization scopes come from the authenticated
    principal via governance middleware; they are never editable request fields.
    """

    account_id: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    external_reference: str | None = Field(None, max_length=500)
    idempotency_key: str | None = Field(None, max_length=255)
    consent_id: str | None = Field(None, description="Explicit consent record id (v3.0). Optional during migration.")
    requested_outputs: list[str] = Field(default_factory=lambda: ["fabric_found_summary"])
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_type", mode="before")
    @classmethod
    def _normalize_source_type(cls, v: str | SourceType) -> SourceType:
        if isinstance(v, SourceType):
            return v
        try:
            return SourceType(v.lower())
        except ValueError as exc:
            raise ValueError(
                f"Unsupported source_type '{v}'. Allowed: {', '.join(t.value for t in SourceType)}"
            ) from exc


class AcceptedSourceResponse(BaseModel):
    """Synchronous confirmation that the source was accepted."""

    source_id: str
    source_version_id: str
    ingestion_run_id: str
    status: str
    revision: int


class SourceVersionResponse(BaseModel):
    """Source version detail response."""

    id: str
    source_id: str
    version_number: int
    content_hash: str
    media_type: str
    status: str
    created_at: datetime


class SourceDetailResponse(BaseModel):
    """Source detail response."""

    id: str
    tenant_id: str
    account_id: str
    source_type: str
    title: str
    external_reference: str | None
    latest_version_id: str | None
    latest_version_number: int
    status: str
    created_at: datetime
    updated_at: datetime


class IngestionRunResponse(BaseModel):
    """Ingestion run status response."""

    id: str
    source_id: str
    source_version_id: str
    status: str
    requested_outputs: list[str]
    stage_metadata: dict[str, Any]
    error_code: str | None
    error_detail_safe: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    @classmethod
    def from_run(cls, run: SourceIngestionRun) -> IngestionRunResponse:
        """Build a response from a SQLAlchemy SourceIngestionRun instance.

        Explicit casts keep mypy happy while SQLAlchemy runtime attributes are
        the actual Python values.
        """
        from typing import cast

        return cls(
            id=str(run.id),
            source_id=str(run.source_id),
            source_version_id=str(run.source_version_id),
            status=cast(str, run.status),
            requested_outputs=cast(list[str], run.requested_outputs or []),
            stage_metadata=cast(dict[str, Any], run.stage_metadata or {}),
            error_code=cast(str | None, run.error_code),
            error_detail_safe=cast(str | None, run.error_detail_safe),
            started_at=cast(datetime | None, run.started_at),
            completed_at=cast(datetime | None, run.completed_at),
            created_at=cast(datetime, run.created_at),
        )


# =============================================================================
# NORMALIZERS
# =============================================================================


MEDIA_TYPES: dict[SourceType, str] = {
    SourceType.NOTES: "text/markdown",
    SourceType.URL: "text/markdown",
    SourceType.AUDIO: "text/plain",
    SourceType.CRM: "application/json",
    SourceType.PDF: "text/markdown",
    SourceType.MEETING: "text/plain",
}


def _is_production_env() -> bool:
    """True only for the exact production environment (fail-closed doctrine)."""
    import os

    return os.getenv("ENVIRONMENT", os.getenv("ENV", os.getenv("APP_ENV", ""))).strip().lower() == "production"


def _normalize_source(
    source_type: SourceType,
    content: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Produce a deterministic NormalizedDocument from raw source content.

    This is a minimal first-pass normalizer. Per-source-type connectors (audio
    transcription, CRM field mapping, PDF layout reconstruction) will replace
    the simple branches over time.
    """
    media_type = MEDIA_TYPES.get(source_type, "text/plain")

    # Indirect prompt-injection screening (V1-AI-001): every ingested document
    # is scanned at the intake boundary. The detection is recorded on the
    # immutable normalized document so downstream layers (L2 extraction, L4
    # prompts) can see it; in production-like environments definite or strong
    # injections are rejected at intake instead of entering the pipeline.
    injection_result = PromptGuard().check(
        content,
        context={
            "tenant_id": metadata.get("tenant_id"),
            "external_reference": metadata.get("external_reference"),
        },
    )
    if injection_result.is_injection and _is_production_env():
        raise ValidationError(
            message=(
                f"Source content rejected: prompt injection detected "
                f"({injection_result.severity.value}: {', '.join(injection_result.matched_patterns)})"
            )
        )

    normalized: dict[str, Any] = {
        "media_type": media_type,
        "language": "en",
        "content": content,
        "sections": [],
        "participants": metadata.get("participants", []),
        "source_metadata": {
            "source_type": source_type.value,
            "external_reference": metadata.get("external_reference"),
            "title": metadata.get("title"),
            "prompt_injection": {
                "is_injection": injection_result.is_injection,
                "severity": injection_result.severity.value,
                "matched_patterns": injection_result.matched_patterns,
                "confidence": injection_result.confidence,
            },
        },
        "normalizer_version": "1.0.0",
        "chunks": [],
    }

    if source_type in (SourceType.NOTES, SourceType.URL, SourceType.PDF):
        # Simple markdown section extraction from headings.
        lines = content.splitlines()
        current_section: dict[str, Any] | None = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                if current_section:
                    normalized["sections"].append(current_section)
                level = len(stripped) - len(stripped.lstrip("#"))
                current_section = {
                    "level": level,
                    "title": stripped.lstrip("#").strip(),
                    "content": [],
                }
            elif current_section is not None:
                current_section["content"].append(stripped)
        if current_section:
            normalized["sections"].append(current_section)

    elif source_type in (SourceType.AUDIO, SourceType.MEETING):
        # Placeholder for transcript segmentation with timecodes.
        normalized["sections"] = [
            {
                "level": 1,
                "title": "Transcript",
                "content": content.splitlines(),
            }
        ]

    elif source_type == SourceType.CRM:
        # Placeholder: CRM connector would map fields into structured narrative.
        normalized["sections"] = [
            {
                "level": 1,
                "title": "CRM Records",
                "content": [content],
            }
        ]

    return normalized


def _chunk_content(content: str, max_chars: int = 800, overlap: int = 80) -> list[dict[str, Any]]:
    """Produce semantic-ish chunks with character-range anchors."""
    chunks: list[dict[str, Any]] = []
    start = 0
    ordinal = 0
    while start < len(content):
        end = min(start + max_chars, len(content))
        # Extend to word boundary.
        if end < len(content):
            while end > start and content[end] not in (" ", "\n"):
                end -= 1
        ordinal += 1
        chunks.append(
            {
                "chunk_id": f"chk_{ordinal:04d}",
                "ordinal": ordinal,
                "text": content[start:end].strip(),
                "token_count": len(content[start:end].split()),
                "anchor": {"type": "character_range", "start": start, "end": end},
            }
        )
        start = max(end - overlap, start + 1)
    return chunks


# =============================================================================
# FINGERPRINT
# =============================================================================


def _compute_fingerprint(
    tenant_id: str,
    account_id: str,
    source_type: str,
    external_reference: str | None,
    content_hash: str,
    external_identity: dict[str, Any] | None = None,
) -> str:
    """Deterministic fingerprint for deduplication.

    Exact repeat of tenant + account + source type + external reference +
    content hash + external identity (v3.0) returns the existing logical
    source. Custody mode, connector name, and runtime are intentionally
    excluded from the fingerprint.
    """
    identity = external_identity or {}
    key = "|".join(
        [
            str(tenant_id),
            account_id,
            source_type,
            external_reference or "",
            identity.get("external_system", ""),
            identity.get("external_object_type", ""),
            identity.get("external_object_id", ""),
            identity.get("external_version", ""),
            identity.get("snapshot_hash", ""),
            content_hash,
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# =============================================================================
# STORAGE
# =============================================================================


def _raw_storage_uri(tenant_id: str, account_id: str, source_id: str, version_id: str) -> str:
    """Tenant-scoped object storage key for the immutable raw artifact."""
    # Preserve the contract path even if S3 is not configured yet; local runs
    # can store alongside metadata in Postgres until object storage is wired.
    return f"s3://layer1-raw-html/{tenant_id}/{account_id}/{source_id}/{version_id}/raw"


# =============================================================================
# API ENDPOINTS
# =============================================================================


async def create_source(
    intake: SourceIntakeRequest,
    http_request: Request,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Accept a source artifact and begin the durable ingestion pipeline.

    Synchronous response returns identifiers only. The frontend must subscribe
    to the run via GET /api/v1/ingestion-runs/{run_id} or the SSE stream.
    """
    ctx = getattr(http_request, "state", None)
    if ctx is not None:
        ctx = getattr(ctx, "governance_context", None)

    content_bytes = intake.content.encode("utf-8")
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    external_identity = {
        k: v
        for k, v in intake.metadata.get("external_identity", {}).items()
        if k in {"external_system", "external_object_type", "external_object_id", "external_version", "snapshot_hash"}
    }
    fingerprint = _compute_fingerprint(
        str(org_id),
        intake.account_id,
        intake.source_type.value,
        intake.external_reference,
        content_hash,
        external_identity=external_identity,
    )

    # Idempotency: exact fingerprint returns existing logical source and a new
    # run tied to the existing latest version.
    existing = (
        db.query(IngestedSource)
        .filter(
            IngestedSource.tenant_id == org_id,
            IngestedSource.account_id == intake.account_id,
            IngestedSource.fingerprint == fingerprint,
        )
        .first()
    )

    # Resolve explicit consent if provided (v3.0). During migration consent is
    # optional; if omitted the source/run is created without consent binding.
    consent_id: uuid.UUID | None = None
    if intake.consent_id:
        consent_service = ConsentService(db)
        consent = consent_service.require_active_consent(
            tenant_id=org_id,
            account_id=intake.account_id,
            source_type=intake.source_type.value,
            scope={"title": intake.title, "external_reference": intake.external_reference},
        )
        consent_id = cast(uuid.UUID | None, consent.id)

    # Resolve custody policy (v3.0). Defaults are source-type driven.
    custody_service = CustodyPolicyService()
    custody = custody_service.decide(
        intake.source_type,
        connector_name=intake.metadata.get("connector_name"),
        customer_hosted=intake.metadata.get("customer_hosted", False),
    )

    if existing:
        latest_version = (
            db.query(SourceVersion)
            .filter(SourceVersion.id == existing.latest_version_id)
            .first()
        )
        if latest_version and latest_version.content_hash == content_hash:
            # Exact duplicate: return existing source/version but start a new run.
            run = SourceIngestionRun(
                tenant_id=org_id,
                source_id=existing.id,
                source_version_id=latest_version.id,
                consent_id=consent_id,
                status=IngestionRunStatus.ACCEPTED,
                requested_outputs=intake.requested_outputs,
                idempotency_key=intake.idempotency_key,
                correlation_id=str(uuid.uuid4()),
                created_by=user_id,
            )
            db.add(run)
            coordinator = PipelineCoordinator(db)
            coordinator.start_run(run)
            db.commit()
            db.refresh(run)
            db.refresh(existing)
            return AcceptedSourceResponse(
                source_id=str(existing.id),
                source_version_id=str(latest_version.id),
                ingestion_run_id=str(run.id),
                status="accepted",
                revision=cast(int, existing.latest_version_number),
            )

    # Create new logical source.
    source = IngestedSource(
        tenant_id=org_id,
        account_id=intake.account_id,
        source_type=intake.source_type.value,
        title=intake.title,
        external_reference=intake.external_reference,
        fingerprint=fingerprint,
        custody_mode=custody.mode.value,
        consent_id=consent_id,
        external_system=external_identity.get("external_system"),
        external_object_type=external_identity.get("external_object_type"),
        external_object_id=external_identity.get("external_object_id"),
        external_version=external_identity.get("external_version"),
        snapshot_hash=external_identity.get("snapshot_hash"),
        created_by=user_id,
    )
    db.add(source)
    db.flush()

    version_number = 1
    if existing:
        version_number = cast(int, existing.latest_version_number) + 1
        source = existing
        if consent_id:
            source.consent_id = consent_id  # type: ignore[assignment]

    version_id = uuid.uuid4()
    storage_uri = _raw_storage_uri(str(org_id), intake.account_id, str(source.id), str(version_id))

    version = SourceVersion(
        id=version_id,
        source_id=source.id,
        version_number=version_number,
        content_hash=content_hash,
        raw_storage_uri=storage_uri,
        raw_bytes_size=len(content_bytes),
        media_type=MEDIA_TYPES.get(intake.source_type, "text/plain"),
        language="en",
        status="stored",
        storage_backend=custody.allowed_backends[0] if custody.allowed_backends else None,
        meta={
            "custody_mode": custody.mode.value,
            "retention_class": custody.retention_class,
            "store_raw": custody.store_raw,
            "store_extracted": custody.store_extracted,
            "store_reference_only": custody.store_reference_only,
            "policy_version": custody.policy_version,
            "idempotency_key": intake.idempotency_key,
            "external_reference": intake.external_reference,
            "requested_outputs": intake.requested_outputs,
            **intake.metadata,
        },
        created_by=user_id,
    )
    db.add(version)
    db.flush()

    source.latest_version_id = version.id
    source.latest_version_number = cast(Any, version_number)

    normalized_data = _normalize_source(
        intake.source_type,
        intake.content,
        {
            "external_reference": intake.external_reference,
            "title": intake.title,
            "participants": intake.metadata.get("participants", []),
        },
    )
    normalized_data["chunks"] = _chunk_content(normalized_data["content"])

    normalized = NormalizedDocument(
        tenant_id=org_id,
        source_version_id=version.id,
        document_id=f"doc_{version.id.hex[:12]}",
        media_type=normalized_data["media_type"],
        language=normalized_data["language"],
        content=normalized_data["content"],
        sections=normalized_data["sections"],
        participants=normalized_data["participants"],
        source_metadata=normalized_data["source_metadata"],
        normalizer_version=normalized_data["normalizer_version"],
        chunks=normalized_data["chunks"],
    )
    db.add(normalized)

    run = SourceIngestionRun(
        tenant_id=org_id,
        source_id=source.id,
        source_version_id=version.id,
        consent_id=consent_id,
        status=IngestionRunStatus.ACCEPTED,
        requested_outputs=intake.requested_outputs,
        idempotency_key=intake.idempotency_key,
        correlation_id=str(uuid.uuid4()),
        stage_metadata={
            "current_stage": IngestionRunStatus.ACCEPTED.value,
            "started_at": datetime.now(UTC).isoformat(),
        },
        created_by=user_id,
    )
    db.add(run)

    # Transactional outbox event for downstream handoff.
    outbox = EventOutbox(
        tenant_id=org_id,
        event_type="fabric.source.normalized.v1",
        aggregate_type="source_version",
        aggregate_id=str(version.id),
        payload={
            "tenant_id": str(org_id),
            "account_id": intake.account_id,
            "source_id": str(source.id),
            "source_version_id": str(version.id),
            "ingestion_run_id": str(run.id),
            "source_type": intake.source_type.value,
            "document_id": normalized.document_id,
            "media_type": normalized.media_type,
            "storage_uri": storage_uri,
            "content_hash": content_hash,
            "requested_outputs": intake.requested_outputs,
            "emitted_at": datetime.now(UTC).isoformat(),
        },
        status=OutboxStatus.PENDING,
    )
    db.add(outbox)

    coordinator = PipelineCoordinator(db)
    coordinator.start_run(run)

    db.commit()
    db.refresh(source)
    db.refresh(version)
    db.refresh(run)

    logger.info(
        "source_accepted",
        tenant_id=str(org_id),
        account_id=intake.account_id,
        source_id=str(source.id),
        source_version_id=str(version.id),
        run_id=str(run.id),
        source_type=intake.source_type.value,
    )

    return AcceptedSourceResponse(
        source_id=str(source.id),
        source_version_id=str(version.id),
        ingestion_run_id=str(run.id),
        status="accepted",
        revision=version_number,
    )


async def get_source(
    source_id: uuid.UUID,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve a source and its latest version metadata."""
    source = (
        db.query(IngestedSource)
        .filter(IngestedSource.id == source_id, IngestedSource.tenant_id == org_id)
        .first()
    )
    if not source:
        raise ValidationError(message="Source not found")
    return _orm_to_response(SourceDetailResponse, source)


async def get_source_version(
    source_id: uuid.UUID,
    version_id: uuid.UUID,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve a specific source version."""
    version = (
        db.query(SourceVersion)
        .join(IngestedSource)
        .filter(
            SourceVersion.id == version_id,
            SourceVersion.source_id == source_id,
            IngestedSource.tenant_id == org_id,
        )
        .first()
    )
    if not version:
        raise ValidationError(message="Source version not found")
    return _orm_to_response(SourceVersionResponse, version)


async def get_ingestion_run(
    run_id: uuid.UUID,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve the status of an ingestion run."""
    run = (
        db.query(SourceIngestionRun)
        .filter(SourceIngestionRun.id == run_id, SourceIngestionRun.tenant_id == org_id)
        .first()
    )
    if not run:
        raise ValidationError(message="Ingestion run not found")
    return _orm_to_response(IngestionRunResponse, run)


async def retry_ingestion_run(
    run_id: uuid.UUID,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retry a failed ingestion run by creating a new run for the same version."""
    run = (
        db.query(SourceIngestionRun)
        .filter(SourceIngestionRun.id == run_id, SourceIngestionRun.tenant_id == org_id)
        .first()
    )
    if not run:
        raise ValidationError(message="Ingestion run not found")
    if run.status not in {IngestionRunStatus.FAILED_RETRYABLE.value, IngestionRunStatus.FAILED_PERMANENT.value}:
        raise ConflictError(message="Run is not in a retryable state")

    new_run = SourceIngestionRun(
        tenant_id=org_id,
        source_id=run.source_id,
        source_version_id=run.source_version_id,
        status=IngestionRunStatus.ACCEPTED,
        requested_outputs=run.requested_outputs,
        idempotency_key=run.idempotency_key,
        correlation_id=str(uuid.uuid4()),
        created_by=user_id,
    )
    db.add(new_run)
    coordinator = PipelineCoordinator(db)
    coordinator.start_run(new_run)
    db.commit()
    db.refresh(new_run)
    return IngestionRunResponse.from_run(new_run)


async def cancel_ingestion_run(
    run_id: uuid.UUID,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Cancel a running ingestion run while preserving prior artifacts."""
    run = (
        db.query(SourceIngestionRun)
        .filter(SourceIngestionRun.id == run_id, SourceIngestionRun.tenant_id == org_id)
        .first()
    )
    if not run:
        raise ValidationError(message="Ingestion run not found")
    if run.status in {IngestionRunStatus.READY.value, IngestionRunStatus.CANCELLED.value, IngestionRunStatus.FAILED_PERMANENT.value}:
        raise ConflictError(message="Run is already in a terminal state")

    run.status = IngestionRunStatus.CANCELLED.value  # type: ignore[assignment]
    run.completed_at = datetime.now(UTC)  # type: ignore[assignment]
    db.commit()
    db.refresh(run)
    return IngestionRunResponse.from_run(run)


# =============================================================================
# ROUTE REGISTRATION
# =============================================================================


def register_routes(parent_router: APIRouter) -> None:
    """Register canonical source routes under the parent /api/v1/ingestion router."""
    parent_router.add_api_route(
        "/sources",
        create_source,
        methods=["POST"],
        response_model=AcceptedSourceResponse,
        status_code=202,
        tags=["Source Ingestion"],
        summary="Ingest a source artifact",
        description="Unified source intake for notes, web, audio, CRM, PDF, and meeting sources.",
    )
    parent_router.add_api_route(
        "/sources/{source_id}",
        get_source,
        methods=["GET"],
        response_model=SourceDetailResponse,
        tags=["Source Ingestion"],
        summary="Get source metadata",
    )
    parent_router.add_api_route(
        "/sources/{source_id}/versions/{version_id}",
        get_source_version,
        methods=["GET"],
        response_model=SourceVersionResponse,
        tags=["Source Ingestion"],
        summary="Get source version metadata",
    )
    parent_router.add_api_route(
        "/runs/{run_id}",
        get_ingestion_run,
        methods=["GET"],
        response_model=IngestionRunResponse,
        tags=["Source Ingestion"],
        summary="Get ingestion run status",
    )
    parent_router.add_api_route(
        "/runs/{run_id}/retry",
        retry_ingestion_run,
        methods=["POST"],
        response_model=IngestionRunResponse,
        tags=["Source Ingestion"],
        summary="Retry a failed ingestion run",
    )
    parent_router.add_api_route(
        "/runs/{run_id}/cancel",
        cancel_ingestion_run,
        methods=["POST"],
        response_model=IngestionRunResponse,
        tags=["Source Ingestion"],
        summary="Cancel an ingestion run",
    )
