from __future__ import annotations

"""Business cases sub-router for Layer 4 analysis API.

Handles case listing, creation, lifecycle management, document generation,
regeneration with lineage diffs, and evidence-governed export.
"""

import asyncio
import json
import logging
import sys
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
    ValueFabricException,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.policy_registry import authorize_action

from ...config.settings import get_settings
from ...engine.executor import WorkflowExecutor
from ...models.agent_state import (
    BusinessCaseInputData,
)
from ...models.business_case_record import BusinessCaseRecord
from ...services.account_service import AccountService
from ...services.business_case_service import BusinessCaseService
from ...services.export_provenance import build_export_provenance_manifest
from ...services.export_storage import generate_download_url, upload_bytes
from ..common.audit import emit_and_persist_audit
from ..common.db import get_route_db
from ..common.errors import normalize_exception
from .analysis_schemas import (
    BusinessCaseRequest,
    BusinessCaseResponse,
    CaseListItem,
    CaseListResponse,
    CreateCaseRequest,
    CreateCaseResponse,
    RegenerateBusinessCaseRequest,
    export_business_caseResult,
)

logger = logging.getLogger(__name__)


def compute_case_diff(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    prev_total = float(previous.get("total_estimated_value", 0.0) or 0.0)
    curr_total = float(current.get("total_estimated_value", 0.0) or 0.0)
    prev_narrative = str(previous.get("executive_summary", "") or "")
    curr_narrative = str(current.get("executive_summary", "") or "")
    return {
        "totals": {
            "previous_total_value": prev_total,
            "current_total_value": curr_total,
            "delta": curr_total - prev_total,
        },
        "narrative_sections_changed": {
            "executive_summary": prev_narrative != curr_narrative,
        },
    }


def _resolve_account_service() -> type[AccountService]:
    mod = _get_analysis_module()
    return getattr(mod, "AccountService", AccountService)


def _resolve_business_case_service() -> type[BusinessCaseService]:
    mod = _get_analysis_module()
    return getattr(mod, "BusinessCaseService", BusinessCaseService)


def _resolve_emit_and_persist_audit() -> _EmitAuditCallable:
    mod = _get_analysis_module()
    return cast(
        _EmitAuditCallable,
        getattr(mod, "emit_and_persist_audit", emit_and_persist_audit),
    )


def _resolve_require_approved_case() -> _RequireApprovedCaseCallable:
    mod = _get_analysis_module()
    return cast(
        _RequireApprovedCaseCallable,
        getattr(mod, "_require_approved_case", require_approved_case),
    )


def _resolve_get_settings() -> Callable[[], object]:
    mod = _get_analysis_module()
    return cast(Callable[[], object], getattr(mod, "get_settings", get_settings))


def _resolve_upload_bytes() -> _UploadBytesCallable:
    mod = _get_analysis_module()
    return cast(_UploadBytesCallable, getattr(mod, "upload_bytes", upload_bytes))


def _resolve_generate_download_url() -> _GenerateDownloadUrlCallable:
    mod = _get_analysis_module()
    return cast(
        _GenerateDownloadUrlCallable,
        getattr(mod, "generate_download_url", generate_download_url),
    )


def _get_analysis_module() -> object:
    return sys.modules.get("layer4_agents.api.routes.analysis")


def parse_case_account_uuid(account_id: str) -> UUID:
    """Parse account identifiers used by case workspace routes."""
    try:
        return UUID(account_id)
    except ValueError as exc:
        raise ValidationError(message="account_id must be a UUID") from exc


def isoformat_or_none(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def is_workspace_case_create_body(body: object) -> bool:
    """Disambiguate the legacy workspace create payload from business-case generation."""
    if not isinstance(body, dict):
        return False
    generation_keys = {"sections", "output_format", "custom_inputs", "opportunity_id"}
    return "account_id" in body and "title" in body and not generation_keys.intersection(body)


async def create_workspace_case_record(
    request: CreateCaseRequest,
    db: AsyncSession,
    context: RequestContext,
) -> CreateCaseResponse:
    account_uuid = parse_case_account_uuid(request.account_id)
    tenant_id = str(context.tenant_id)
    account_service_cls = _resolve_account_service()
    account = await account_service_cls(db).get_account(account_uuid, tenant_id=tenant_id)
    if account is None:
        raise NotFoundError(message=f"Account not found: {request.account_id}")

    case_id = request.case_id or str(uuid4())
    now = datetime.now(UTC).isoformat()
    record = BusinessCaseRecord(
        case_id=case_id,
        account_id=account_uuid,
        workflow_id=case_id,
        status="created",
        tenant_id=tenant_id,
    )
    db.add(record)

    return CreateCaseResponse(
        case_id=case_id,
        account_id=request.account_id,
        title=request.title,
        status="created",
        created_at=now,
    )


async def require_approved_case(
    record: BusinessCaseRecord,
    context: RequestContext,
    account: _TenantAccount,
    format: str = "pdf",
) -> None:
    """Raise if the business case is not in an export-allowed status."""
    if str(record.status).lower() not in {"approved", "exported", "delivered"}:
        emit_audit = _resolve_emit_and_persist_audit()
        await emit_audit(
            action=AuditAction.EXPORT_REQUESTED,
            context=context,
            resource_type="BusinessCaseExport",
            resource_id=str(record.case_id),
            details={
                "case_id": str(record.case_id),
                "format": format,
                "outcome": "denied",
                "denied_reason": "approval_required",
                "tenant_id": str(context.tenant_id),
                "account_id": str(account.id),
                "case_status": str(record.status),
            },
        )
        raise ConflictError(message="Business case must be approved before export")


def build_cases_router(
    *,
    get_executor: Callable[[], WorkflowExecutor],
    require_tenant_account_fn: Callable[
        [AsyncSession, UUID, RequestContext], Awaitable[_TenantAccount]
    ],
    is_smoke_mode_fn: _SmokeModeCallable,
    smoke_business_case_response_fn: _SmokeBusinessCaseCallable,
) -> APIRouter:
    router = APIRouter()

    @router.post("/cases", response_model=BusinessCaseResponse)
    async def generate_business_case(
        request: BusinessCaseRequest,
        background_tasks: BackgroundTasks,
        http_request: Request,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> BusinessCaseResponse:
        """Generate a business case document."""
        authorize_action("layer4.analysis.generate_case", context)
        try:
            try:
                raw_body = await http_request.json()
            except asyncio.CancelledError:
                raise
            except Exception:
                raw_body = {}
            if is_workspace_case_create_body(raw_body):
                workspace_case = await create_workspace_case_record(
                    CreateCaseRequest.model_validate(raw_body),
                    db,
                    context,
                )
                return BusinessCaseResponse(
                    case_id=workspace_case.case_id,
                    title=workspace_case.title or "Case Workspace",
                    status=workspace_case.status,
                    created_at=workspace_case.created_at,
                    case_metadata={
                        "account_id": workspace_case.account_id,
                        "workspace_case": True,
                    },
                )

            account_service_cls = _resolve_account_service()
            account = await account_service_cls(db).get_account(
                request.account_id, tenant_id=str(context.tenant_id)
            )
            if not account:
                raise NotFoundError(message=f"Account not found: {request.account_id}")

            custom_inputs = dict(request.custom_inputs)
            custom_inputs["provider_record_id"] = account.provider_record_id

            if is_smoke_mode_fn(http_request, body_mode=str(custom_inputs.get("mode", ""))):
                return cast(
                    BusinessCaseResponse,
                    await smoke_business_case_response_fn(
                        http_request, request, account, db, context
                    ),
                )

            executor = get_executor()

            input_data = BusinessCaseInputData(
                account_id=request.account_id,
                opportunity_id=request.opportunity_id,
                sections_requested=request.sections,
                output_format=request.output_format,
                custom_inputs=custom_inputs,
            )

            result = await executor.run(
                workflow_type="business_case",
                input_data=input_data.model_dump(),
                tenant_id=str(context.tenant_id),
                user_id=context.user_id,
            )

            output_data = result.output_data or {}
            assemble_data = output_data.get("assemble", {})
            truth_gate = output_data.get("verify_truth_requirements", {})
            sdes_bundle = output_data.get("generate_sdes", {})

            case_metadata = dict(assemble_data.get("case_metadata", {}))
            case_metadata["account_id"] = str(request.account_id)

            business_case_service_cls = _resolve_business_case_service()
            business_case_service = business_case_service_cls(db)
            await business_case_service.upsert_case_record(
                case_id=result.workflow_id,
                workflow_id=result.workflow_id,
                account_id=request.account_id,
                opportunity_id=request.opportunity_id,
                status=result.status.value,
                document_url=assemble_data.get("document_url"),
                tenant_id=str(context.tenant_id),
            )

            return BusinessCaseResponse(
                case_id=result.workflow_id,
                status=result.status.value,
                title=assemble_data.get("title", "Business Case"),
                summary=assemble_data.get("summary", ""),
                total_value=assemble_data.get("total_value", 0.0),
                implementation_cost=assemble_data.get("implementation_cost", 0.0),
                roi_ratio=assemble_data.get("roi_ratio", 0.0),
                payback_months=assemble_data.get("payback_months", 0),
                confidence_score=assemble_data.get("confidence_score", 0.0),
                recommendations=assemble_data.get("recommendations", []),
                created_at=assemble_data.get("created_at"),
                document_url=assemble_data.get("document_url"),
                page_count=assemble_data.get("page_count", 0),
                file_size_bytes=assemble_data.get("file_size_bytes", 0),
                truth_references=assemble_data.get(
                    "truth_references", truth_gate.get("truth_references", [])
                ),
                remediation_items=assemble_data.get(
                    "remediation_items", truth_gate.get("remediation_items", [])
                ),
                sdes=sdes_bundle,
                case_metadata=case_metadata,
            )

        except asyncio.CancelledError:
            raise
        except (ValueFabricException, HTTPException):
            raise
        except Exception as e:
            logger.exception("Business case generation failed: %s", e)
            raise normalize_exception(
                e,
                status_code=500,
                message="Business case generation failed",
                error_code="L4_BUSINESS_CASE_GENERATION_FAILED",
                request_id=getattr(http_request.state, "request_id", None),
            )

    @router.post("/cases", response_model=CreateCaseResponse)
    async def create_case(
        request: CreateCaseRequest,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> CreateCaseResponse:
        """Create a new case for an account.

        Creates a case workspace for the specified account.
        """
        authorize_action("layer4.analysis.write_case", context)
        return await create_workspace_case_record(request, db, context)

    @router.post("/cases/{case_id}/regenerate", response_model=BusinessCaseResponse)
    async def regenerate_business_case(
        case_id: str,
        request: RegenerateBusinessCaseRequest,
        background_tasks: BackgroundTasks,
        http_request: Request,
        executor: WorkflowExecutor = Depends(get_executor),
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> BusinessCaseResponse:
        """Regenerate a business case with latest inputs and preserve revision lineage."""
        authorize_action("layer4.analysis.regenerate_case", context)
        if request.previous_case_id != case_id:
            raise ValidationError(message="previous_case_id must match route case_id")
        previous_result = await executor.get_result(case_id)
        previous_assemble = (previous_result or {}).get("output", {}).get("assemble_document", {})
        response = await generate_business_case(
            request, background_tasks, http_request, db, context
        )
        current_result = await executor.get_result(response.case_id)
        current_assemble = (current_result or {}).get("output", {}).get("assemble_document", {})
        diff_summary = compute_case_diff(previous_assemble, current_assemble)
        source_version = str(request.custom_inputs.get("value_case_version", "latest"))
        source_hash = str(request.custom_inputs.get("value_case_hash", "unknown"))
        response.case_metadata.update(
            {
                "source_value_case_version": source_version,
                "source_value_case_hash": source_hash,
                "regenerated_from_case_id": case_id,
            }
        )
        response.revision_history = [
            {
                "case_id": case_id,
                "created_at": (previous_result or {}).get("created_at"),
            },
            {
                "case_id": response.case_id,
                "created_at": (current_result.get("created_at") if current_result else None),
            },
        ]
        response.diff_summary = diff_summary
        return response

    @router.get("/cases/{case_id}", response_model=BusinessCaseResponse)
    async def get_business_case(
        case_id: str,
        executor: WorkflowExecutor = Depends(get_executor),
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> BusinessCaseResponse:
        """Get a generated business case by ID."""
        authorize_action("layer4.analysis.read_case", context)
        result = await executor.get_result(case_id)

        if not result:
            raise NotFoundError(message=f"Business case {case_id} not found")

        record = await db.get(BusinessCaseRecord, case_id)
        if record and record.account_id:
            await require_tenant_account_fn(db, record.account_id, context)
        else:
            result_tenant = result.get("metadata", {}).get("tenant_id")
            if result_tenant and str(result_tenant) != str(context.tenant_id):
                raise AuthorizationError(
                    message=f"Business case {case_id} does not belong to the current tenant"
                )

        output = result.get("output", {})
        assemble_data = output.get("assemble_document", {})
        truth_gate = output.get("verify_truth_requirements", {})
        sdes_bundle = output.get("generate_sdes", {})
        narrative_data = output.get("synthesize_narrative", {})
        case_metadata = dict(assemble_data.get("case_metadata", {}))
        if record and record.account_id:
            case_metadata["account_id"] = str(record.account_id)

        return BusinessCaseResponse(
            case_id=case_id,
            title=assemble_data.get("title", "Business Case"),
            summary=assemble_data.get("executive_summary", narrative_data.get("narrative", "")),
            total_value=assemble_data.get("total_estimated_value", 0.0),
            implementation_cost=assemble_data.get("implementation_cost_estimate", 0.0),
            roi_ratio=assemble_data.get("roi_ratio", 0.0),
            payback_months=assemble_data.get("payback_months", 0),
            confidence_score=assemble_data.get("confidence_score", 0.0),
            recommendations=assemble_data.get("recommendations", []),
            created_at=result.get("created_at"),
            status=assemble_data.get(
                "status", record.status if record else result.get("status", "unknown")
            ),
            document_url=assemble_data.get("document_url", record.document_url if record else None),
            page_count=assemble_data.get("page_count", 0),
            file_size_bytes=assemble_data.get("file_size_bytes", 0),
            truth_references=assemble_data.get(
                "truth_references", truth_gate.get("truth_references", [])
            ),
            remediation_items=assemble_data.get(
                "remediation_items", truth_gate.get("remediation_items", [])
            ),
            sdes=sdes_bundle,
            case_metadata=case_metadata,
        )

    @router.get("/cases/{case_id}/export", response_model=dict[str, object])
    async def export_business_case(
        case_id: str,
        format: str = "pdf",
        executor: WorkflowExecutor = Depends(get_executor),
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> dict[str, object]:
        """Export a generated business case."""
        authorize_action("layer4.analysis.export_case", context)
        record = await db.get(BusinessCaseRecord, case_id)
        if not record or str(getattr(record, "tenant_id", None)) != str(context.tenant_id):
            raise NotFoundError(message=f"Business case {case_id} not found")

        try:
            account = await require_tenant_account_fn(db, record.account_id, context)
        except ValueFabricException as exc:
            emit_audit = _resolve_emit_and_persist_audit()
            await emit_audit(
                action=AuditAction.EXPORT_REQUESTED,
                context=context,
                resource_type="BusinessCaseExport",
                resource_id=case_id,
                details={
                    "case_id": case_id,
                    "format": format,
                    "outcome": "denied",
                    "denied_reason": "tenant_access_denied",
                    "tenant_id": str(context.tenant_id),
                    "record_account_id": str(record.account_id),
                },
            )
            raise exc

        require_approved = _resolve_require_approved_case()
        await require_approved(record, context, account, format)

        result = await executor.get_result(case_id)
        if not result:
            raise ConflictError(
                message="Business case draft is not approved or document bytes unavailable"
            )

        output = result.get("output", {})
        assemble_data = output.get("assemble_document", {})
        truth_gate = output.get("verify_truth_requirements", {})

        blocked = bool(assemble_data.get("blocked")) or not truth_gate.get("passed", True)
        truth_references = assemble_data.get(
            "truth_references", truth_gate.get("truth_references", [])
        )
        remediation_items = assemble_data.get(
            "remediation_items", truth_gate.get("remediation_items", [])
        )

        document_bytes = assemble_data.get("document_bytes")
        export_id = str(uuid4())

        if blocked:
            emit_audit = _resolve_emit_and_persist_audit()
            await emit_audit(
                action=AuditAction.EXPORT_REQUESTED,
                context=context,
                resource_type="BusinessCaseExport",
                resource_id=case_id,
                details={
                    "case_id": case_id,
                    "format": format,
                    "outcome": "denied",
                    "denied_reason": "truth_gate_blocked",
                    "tenant_id": str(context.tenant_id),
                    "account_id": str(account.id),
                    "blocked": True,
                    "truth_gate_passed": truth_gate.get("passed", False),
                },
            )
            return cast(
                dict[str, object],
                export_business_caseResult(
                    case_id=case_id,
                    export_id=export_id,
                    format=format,
                    document_url=assemble_data.get("document_url"),
                    download_ready=False,
                    blocked=True,
                    remediation_items=remediation_items,
                    truth_references=truth_references,
                    manifest={
                        "case_id": case_id,
                        "format": format,
                        "blocked": True,
                        "truth_references": truth_references,
                        "remediation_items": remediation_items,
                        "truth_gate": {
                            "passed": truth_gate.get("passed", False),
                            "requirements": truth_gate.get("requirements", []),
                        },
                    },
                ).model_dump(),
            )

        if not document_bytes:
            raise ConflictError(message="Business case document bytes unavailable")

        if not isinstance(document_bytes, bytes):
            document_bytes = bytes(document_bytes)

        get_settings_fn = _resolve_get_settings()
        effective_settings = get_settings_fn()
        if not getattr(effective_settings, "export_storage_endpoint", None):
            raise ServiceUnavailableError(message="Export storage endpoint is not configured")

        workflow_id = (
            result.get("workflow_id") or result.get("metadata", {}).get("workflow_id") or case_id
        )
        filename = f"business_case_{case_id}.{format}"
        manifest_filename = f"business_case_{case_id}.provenance.json"

        manifest = build_export_provenance_manifest(
            case_id=case_id,
            workflow_result=result,
            actor_context=context,
            export_id=export_id,
        )
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")

        base_prefix = f"{case_id}/{export_id}"
        object_key = f"{base_prefix}/{filename}"
        manifest_key = f"{base_prefix}/{manifest_filename}"
        metadata = {
            "case-id": case_id,
            "workflow-id": workflow_id,
            "export-id": export_id,
            "tenant-id": str(context.tenant_id),
            "tenant_id": str(context.tenant_id),
            "actor-user-id": str(context.user_id or ""),
            "actor-subject": str(getattr(context, "subject", "") or ""),
            "account-id": str(account.id),
        }

        content_type = "application/pdf" if format == "pdf" else "application/octet-stream"

        upload_bytes_fn = _resolve_upload_bytes()
        await upload_bytes_fn(
            tenant_id=str(context.tenant_id),
            object_key=object_key,
            content=document_bytes,
            content_type=content_type,
            metadata=metadata,
        )
        await upload_bytes_fn(
            tenant_id=str(context.tenant_id),
            object_key=manifest_key,
            content=manifest_bytes,
            content_type="application/json",
            metadata=metadata,
        )

        generate_url_fn = _resolve_generate_download_url()
        document_url = await generate_url_fn(
            tenant_id=str(context.tenant_id), object_key=object_key
        )
        manifest_url = await generate_url_fn(
            tenant_id=str(context.tenant_id), object_key=manifest_key
        )
        expires_at = datetime.fromtimestamp(
            datetime.now(UTC).timestamp()
            + getattr(effective_settings, "export_signed_url_ttl_seconds", 900),
            tz=UTC,
        ).isoformat()

        emit_audit = _resolve_emit_and_persist_audit()
        await emit_audit(
            action=AuditAction.EXPORT_REQUESTED,
            context=context,
            resource_type="BusinessCaseExport",
            resource_id=case_id,
            details={
                "case_id": case_id,
                "workflow_id": workflow_id,
                "export_id": export_id,
                "format": format,
                "account_id": str(account.id),
            },
        )

        await emit_audit(
            action=AuditAction.EXPORT_PACKAGE_GENERATED,
            context=context,
            resource_type="BusinessCaseExport",
            resource_id=case_id,
            details={
                "case_id": case_id,
                "workflow_id": workflow_id,
                "export_id": export_id,
                "pdf_object_key": object_key,
                "manifest_object_key": manifest_key,
                "account_id": str(account.id),
                "truth_object_ids": manifest.get("truth_object_ids", []),
                "source_references": manifest.get("source_references", []),
            },
        )

        await emit_audit(
            action=AuditAction.EXPORT_DOWNLOAD_ACCESSED,
            context=context,
            resource_type="BusinessCaseExport",
            resource_id=case_id,
            details={
                "case_id": case_id,
                "workflow_id": workflow_id,
                "export_id": export_id,
                "pdf_object_key": object_key,
                "account_id": str(account.id),
            },
        )

        return cast(
            dict[str, object],
            export_business_caseResult(
                case_id=case_id,
                export_id=export_id,
                format=format,
                document_url=document_url,
                manifest_url=manifest_url,
                download_ready=True,
                blocked=False,
                manifest=manifest,
                remediation_items=remediation_items,
                truth_references=truth_references,
                url_expires_at=expires_at,
            ).model_dump(),
        )

    @router.get("/cases", response_model=CaseListResponse)
    async def list_cases(
        account_id: str,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> CaseListResponse:
        """List cases for an account."""
        authorize_action("layer4.analysis.list_cases", context)
        account_uuid = parse_case_account_uuid(account_id)
        tenant_id = str(context.tenant_id)

        account = await AccountService(db).get_account(account_uuid, tenant_id=tenant_id)
        if account is None:
            return CaseListResponse(items=[], total=0)

        result = await db.execute(
            select(BusinessCaseRecord).where(
                BusinessCaseRecord.account_id == account_uuid,
                BusinessCaseRecord.tenant_id == tenant_id,
            )
        )
        records = result.scalars().all()

        items = [
            CaseListItem(
                case_id=str(r.case_id),
                account_id=str(r.account_id) if r.account_id else None,
                title=getattr(r, "title", None),
                status=r.status,
                created_at=isoformat_or_none(getattr(r, "created_at", None)),
                updated_at=isoformat_or_none(getattr(r, "updated_at", None)),
            )
            for r in records
        ]

        return CaseListResponse(items=items, total=len(items))

    return router


class _EmitAuditCallable(Protocol):
    async def __call__(
        self,
        *,
        action: AuditAction,
        context: RequestContext,
        resource_type: str,
        resource_id: str,
        details: Mapping[str, object] | None = None,
    ) -> None: ...


class _TenantAccount(Protocol):
    id: UUID


class _RequireApprovedCaseCallable(Protocol):
    async def __call__(
        self,
        record: BusinessCaseRecord,
        context: RequestContext,
        account: _TenantAccount,
        format: str = "pdf",
    ) -> None: ...


class _UploadBytesCallable(Protocol):
    def __call__(
        self,
        *,
        tenant_id: str,
        object_key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> Awaitable[object]: ...


class _GenerateDownloadUrlCallable(Protocol):
    def __call__(
        self,
        *,
        tenant_id: str,
        object_key: str,
        expires_in_seconds: int | None = None,
    ) -> Awaitable[str]: ...


class _SmokeModeCallable(Protocol):
    def __call__(
        self,
        http_request: Request,
        *,
        body_mode: str | None = None,
    ) -> bool: ...


class _SmokeBusinessCaseCallable(Protocol):
    def __call__(
        self,
        http_request: Request,
        request: BusinessCaseRequest,
        account: _TenantAccount,
        db: AsyncSession,
        context: RequestContext,
    ) -> Awaitable[BusinessCaseResponse]: ...
