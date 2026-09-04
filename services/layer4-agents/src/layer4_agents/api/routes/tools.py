from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
    ValueFabricException,
)

"""Tools API routes."""


import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from value_fabric.shared.audit import AuditAction, AuditEmitter, AuditOutcome, emit_audit_event
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated, require_tenant_context
from value_fabric.shared.identity.policy_registry import authorize_action

from ...config.settings import get_settings
from ...contracts.tool_dto import ToolCategoriesResponse, ToolSchemaResponse
from ...database import get_db_from_context
from ...engine.executor import WorkflowExecutor
from ...services.export_provenance import build_export_provenance_manifest
from ...services.export_storage import generate_download_url, upload_bytes
from ...tools import create_default_registry
from ...tools.registry import ToolCategory, ToolRegistry


class _ToolGatewayUnavailable(RuntimeError):
    """Raised when governance tool-gateway dependencies are unavailable."""


try:
    # Compatibility import path required by the release gate:
    # from value_fabric.shared.governance.tool_gateway import ToolGateway
    from value_fabric.shared.governance.abom import AgentBillOfMaterials
    from value_fabric.shared.governance.tool_gateway import (
        InvariantViolation,
        ToolGateway,
        ToolGatewayDenied,
    )

    _GATE_AVAILABLE = True
    _GATE_IMPORT_ERROR: ImportError | None = None
except ImportError as exc:
    AgentBillOfMaterials = None  # type: ignore[assignment]
    ToolGateway = None  # type: ignore[assignment]
    InvariantViolation = _ToolGatewayUnavailable  # type: ignore[assignment]
    ToolGatewayDenied = _ToolGatewayUnavailable  # type: ignore[assignment]
    _GATE_AVAILABLE = False
    _GATE_IMPORT_ERROR = exc

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class ToolListResponse(BaseModel):
    """Tool list response."""

    name: str
    category: str
    description: str
    timeout_seconds: int
    requires_auth: bool


class ToolInvokeRequest(BaseModel):
    """Tool invocation request."""

    tool_name: str = Field(..., description="Name of tool to invoke")
    input_data: dict[str, Any] = Field(default_factory=dict, description="Tool input parameters")


class ToolInvokeResponse(BaseModel):
    """Tool invocation response."""

    tool_name: str
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None


def get_tool_registry() -> ToolRegistry:
    """Get tool registry instance."""
    return create_default_registry()


def get_executor() -> WorkflowExecutor:
    """Get workflow executor instance used by export endpoints."""
    from .main import workflow_executor

    if workflow_executor is None:
        raise ServiceUnavailableError(message = "Workflow executor not initialized")
    return workflow_executor


async def _require_export_tenant_context(
    context: RequestContext = Depends(require_authenticated),
) -> RequestContext:
    """Require validated tenant context without changing the endpoint body shape."""
    return await require_tenant_context(context)


def require_tool_gateway_available() -> None:
    """Fail closed when mandatory tool-governance dependencies are unavailable."""
    if not _GATE_AVAILABLE:
        logger.error(
            "Tool governance gateway unavailable; refusing ungoverned tool execution",
            exc_info=_GATE_IMPORT_ERROR,
        )
        raise ServiceUnavailableError(message = "Tool governance gateway unavailable; refusing ungoverned tool execution.")


@router.get("/tools", response_model=list[ToolListResponse])
async def list_tools(
    category: str | None = None,
    search: str | None = None,
    registry: ToolRegistry = Depends(get_tool_registry),
    ctx: RequestContext = Depends(require_authenticated),
) -> list[ToolListResponse]:
    """List available tools with optional filtering.

    Query Parameters:
        category: Filter by category (knowledge, calculation, crm, generation, integration, utility)
        search: Search in tool name/description
    """
    authorize_action("layer4.tools.list", ctx)
    cat = None
    if category:
        try:
            cat = ToolCategory(category.lower())
        except ValueError:
            raise ValidationError(message = str(f"Invalid category: {category}"))

    tools = registry.list_tools(category=cat, search=search)

    return [
        ToolListResponse(
            name=t.name,
            category=t.category.value,
            description=t.description,
            timeout_seconds=t.timeout_seconds,
            requires_auth=t.requires_auth,
        )
        for t in tools
    ]


@router.get("/tools/{tool_name}", response_model=ToolSchemaResponse)
async def get_tool_schema(
    tool_name: str,
    registry: ToolRegistry = Depends(get_tool_registry),
    ctx: RequestContext = Depends(require_authenticated),
) -> ToolSchemaResponse:
    """Get detailed schema for a specific tool."""
    authorize_action("layer4.tools.read_schema", ctx)
    if not registry.has_tool(tool_name):
        raise NotFoundError(message = str(f"Tool '{tool_name}' not found"))

    tool = registry.get(tool_name)
    schema = tool.get_schema()

    return ToolSchemaResponse.model_validate({
        "name": schema.name,
        "category": schema.category.value,
        "description": schema.description,
        "input_schema": schema.input_schema,
        "output_schema": schema.output_schema,
        "timeout_seconds": schema.timeout_seconds,
        "requires_auth": schema.requires_auth,
        "examples": schema.examples,
    })


@router.post("/tools/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(
    request: ToolInvokeRequest,
    registry: ToolRegistry = Depends(get_tool_registry),
    ctx: RequestContext = Depends(require_authenticated),
) -> ToolInvokeResponse:
    """Invoke a tool directly.

    Example:
        POST /v1/tools/invoke
        {
            "tool_name": "calculate_roi",
            "input_data": {
                "investment": 250000,
                "returns": [400000, 450000, 500000]
            }
        }
    """
    authorize_action("layer4.tools.invoke", ctx)
    if not registry.has_tool(request.tool_name):
        raise NotFoundError(message = str(f"Tool '{request.tool_name}' not found"))

    try:
        # ── GATE enforcement: route through ToolGateway; never fall back to ungoverned execution ──
        require_tool_gateway_available()
        assert AgentBillOfMaterials is not None
        assert ToolGateway is not None
        abom = AgentBillOfMaterials.from_manifest_dir(
            manifest_dir="services/layer4-agents/manifests",
            agent_type="ConversationAgent",  # API routes act on behalf of ValuePilot
        )
        gateway = ToolGateway(
            registry=registry,
            abom=abom,
            tenant_id=str(ctx.tenant_id) if ctx else None,
        )
        result = await gateway.execute(request.tool_name, request.input_data)

        return ToolInvokeResponse(
            tool_name=request.tool_name, success=True, result=result, error=None
        )

    except (ToolGatewayDenied, InvariantViolation) as e:
        logger.warning(
            "GATE denied tool invocation: %s — %s",
            request.tool_name, repr(e),  # ban-str-e-allow: structured-log
        )
        return ToolInvokeResponse(
            tool_name=request.tool_name, success=False, result=None,
            error=f"Policy denied: {e}",
        )

    except ValueFabricException:
        raise

    except asyncio.CancelledError:
        raise
    except Exception:
        # Log full exception server-side for debugging
        logger.exception(
            f"Tool execution failed: {request.tool_name}",
            extra={"tool_name": request.tool_name, "input_data": request.input_data}
        )
        # Return generic error to client - don't leak internal details
        return ToolInvokeResponse(
            tool_name=request.tool_name, success=False, result=None, error="Tool execution failed"
        )


# Document Export Models
class DocumentExportRequest(BaseModel):
    """Request for document export via DocumentExportTool."""

    document_type: str = Field("business_case", description="Type of document to export")
    business_case_id: str = Field(..., description="Business case ID to export")
    format: str = Field("pdf", description="Export format: pdf, html")
    include_provenance: bool = Field(True, description="Include provenance information")


class DocumentExportResponse(BaseModel):
    """Response from document export."""

    success: bool
    export_id: str | None = None
    download_url: str | None = None
    manifest_url: str | None = None
    filename: str | None = None
    manifest_filename: str | None = None
    file_size_bytes: int | None = None
    url_expires_at: str | None = None
    format: str = "pdf"
    error: str | None = None


class ExportAuditRecord(BaseModel):
    """Audit record for export governance endpoints."""

    event_id: str
    action: str
    case_id: str | None = None
    workflow_id: str | None = None
    export_id: str | None = None
    actor_id: str | None = None
    tenant_id: str | None = None
    timestamp: str
    outcome: str
    details: dict[str, Any]


@router.post(
    "/tools/export-document",
    response_model=DocumentExportResponse,
    responses={
        400: {
            "description": "Tenant context is missing or invalid",
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}
            },
        },
        404: {
            "description": "Business case not found",
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}
            },
        },
        503: {
            "description": "Export service unavailable",
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}
            },
        },
    },
)
async def export_document_tool(
    request: DocumentExportRequest,
    registry: ToolRegistry = Depends(get_tool_registry),
    workflow_executor: WorkflowExecutor = Depends(get_executor),
    context: RequestContext = Depends(_require_export_tenant_context),
) -> DocumentExportResponse:
    """Export a business case to PDF using DocumentExportTool.

    This endpoint triggers PDF generation from business case data.
    Returns the generated PDF for download.

    Example:
        POST /v1/tools/export-document
        {
            "document_type": "business_case",
            "business_case_id": "bc-123",
            "format": "pdf",
            "include_provenance": true
        }
    """
    authorize_action("layer4.tools.export_document", context)
    try:
        if not get_settings().export_storage_endpoint:
            raise ServiceUnavailableError(message = "Export storage endpoint is not configured")

        result = await workflow_executor.get_result_for_tenant(
            request.business_case_id,
            str(context.tenant_id),
        )

        if not result:
            raise NotFoundError(message = str(f"Business case {request.business_case_id} not found"))

        # Extract business case data
        output = result.get("output", {})
        assemble_data = output.get("assemble_document", {})
        narrative_data = output.get("synthesize_narrative", {})

        business_case_data = {
            "title": assemble_data.get("title", "Business Case"),
            "organization": assemble_data.get("organization", "Acme Corp"),
            "use_cases": assemble_data.get("use_cases", []),
            "executive_summary": assemble_data.get(
                "executive_summary", narrative_data.get("narrative", "")
            ),
            "methodology": assemble_data.get(
                "methodology",
                "Value estimation based on industry benchmarks and organizational data.",
            ),
        }

        # Prepare tool input
        tool_input = {
            "document_type": request.document_type,
            "business_case_data": business_case_data,
            "format": request.format,
            "include_provenance": request.include_provenance,
        }

        # Execute DocumentExportTool via GATE; never fall back to ungoverned execution.
        require_tool_gateway_available()
        assert AgentBillOfMaterials is not None
        assert ToolGateway is not None
        abom = AgentBillOfMaterials.from_manifest_dir(
            manifest_dir="services/layer4-agents/manifests",
            agent_type="NarrativeAgent",  # Export is owned by NarrativeAgent
        )
        gateway = ToolGateway(
            registry=registry,
            abom=abom,
            tenant_id=str(context.tenant_id) if context else None,
        )
        tool_result = await gateway.execute("export_document", tool_input)
        export_id = str(uuid4())
        workflow_id = (
            result.get("workflow_id")
            or result.get("metadata", {}).get("workflow_id")
            or request.business_case_id
        )

        event = emit_audit_event(
            AuditAction.EXPORT_REQUESTED,
            tenant_id=context.tenant_id if context else None,
            user_id=context.user_id if context else None,
            api_key_id=context.api_key_id if context else None,
            resource_type="BusinessCaseExport",
            resource_id=request.business_case_id,
            outcome=AuditOutcome.SUCCESS,
            details={
                "export_id": export_id,
                "case_id": request.business_case_id,
                "workflow_id": workflow_id,
                "format": request.format,
                "document_type": request.document_type,
            },
        )
        await AuditEmitter.write_to_db(event, get_db_from_context)

        if not tool_result.get("success"):
            return DocumentExportResponse(
                success=False,
                export_id=export_id,
                error=tool_result.get("error", "PDF generation failed"),
            )

        pdf_bytes = tool_result.get("pdf_bytes", b"")
        filename = tool_result.get("filename", f"business_case_{request.business_case_id}.pdf")
        if not isinstance(pdf_bytes, bytes):
            pdf_bytes = bytes(pdf_bytes)

        manifest = build_export_provenance_manifest(
            case_id=request.business_case_id,
            workflow_result=result,
            actor_context=context,
            export_id=export_id,
        )
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        manifest_filename = f"{filename.rsplit('.', 1)[0]}.provenance.json"

        base_prefix = f"{request.business_case_id}/{export_id}"
        pdf_key = f"{base_prefix}/{filename}"
        manifest_key = f"{base_prefix}/{manifest_filename}"
        object_metadata = {
            "case-id": request.business_case_id,
            "workflow-id": workflow_id,
            "export-id": export_id,
            "tenant-id": str(context.tenant_id) if context else "unknown",
        }

        await upload_bytes(
            tenant_id=str(context.tenant_id) if context else "unknown",
            object_key=pdf_key,
            content=pdf_bytes,
            content_type="application/pdf",
            metadata=object_metadata,
        )
        await upload_bytes(
            tenant_id=str(context.tenant_id) if context else "unknown",
            object_key=manifest_key,
            content=manifest_bytes,
            content_type="application/json",
            metadata=object_metadata,
        )

        download_url = await generate_download_url(tenant_id=str(context.tenant_id) if context else "unknown", object_key=pdf_key)
        manifest_url = await generate_download_url(tenant_id=str(context.tenant_id) if context else "unknown", object_key=manifest_key)
        expires_at = datetime.now(UTC).timestamp() + get_settings().export_signed_url_ttl_seconds
        expires_at_iso = datetime.fromtimestamp(expires_at, tz=UTC).isoformat()

        package_event = emit_audit_event(
            AuditAction.EXPORT_PACKAGE_GENERATED,
            tenant_id=context.tenant_id if context else None,
            user_id=context.user_id if context else None,
            api_key_id=context.api_key_id if context else None,
            resource_type="BusinessCaseExport",
            resource_id=request.business_case_id,
            details={
                "export_id": export_id,
                "case_id": request.business_case_id,
                "workflow_id": workflow_id,
                "pdf_object_key": pdf_key,
                "manifest_object_key": manifest_key,
                "manifest_filename": manifest_filename,
                "truth_object_ids": manifest.get("truth_object_ids", []),
                "source_references": manifest.get("source_references", []),
            },
        )
        await AuditEmitter.write_to_db(package_event, get_db_from_context)

        access_event = emit_audit_event(
            AuditAction.EXPORT_DOWNLOAD_ACCESSED,
            tenant_id=context.tenant_id if context else None,
            user_id=context.user_id if context else None,
            api_key_id=context.api_key_id if context else None,
            resource_type="BusinessCaseExport",
            resource_id=request.business_case_id,
            details={
                "export_id": export_id,
                "case_id": request.business_case_id,
                "workflow_id": workflow_id,
                "pdf_object_key": pdf_key,
                "manifest_object_key": manifest_key,
                "reason": "initial_signed_url_issued",
            },
        )
        await AuditEmitter.write_to_db(access_event, get_db_from_context)

        return DocumentExportResponse(
            success=True,
            export_id=export_id,
            download_url=download_url,
            manifest_url=manifest_url,
            filename=filename,
            manifest_filename=manifest_filename,
            file_size_bytes=tool_result.get("file_size_bytes"),
            url_expires_at=expires_at_iso,
            format=request.format,
        )

    except ValueFabricException:
        raise
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Document export failed")
        return DocumentExportResponse(success=False, error="Document export failed")


@router.get("/tools/governance/audit/exports", response_model=list[ExportAuditRecord])
async def list_export_audit_events(
    case_id: str | None = None,
    workflow_id: str | None = None,
    limit: int = 100,
    db=Depends(get_db_from_context),
    context: RequestContext = Depends(require_authenticated),
) -> list[ExportAuditRecord]:
    """List immutable audit records related to export governance."""
    authorize_action("layer4.tools.read_export_audit", context)
    query = """
        SELECT
            id,
            action,
            resource_id,
            tenant_id,
            user_id,
            timestamp,
            outcome,
            details
        FROM audit_events
        WHERE action IN ('export.requested', 'export.package_generated', 'export.download_accessed')
    """
    params: dict[str, Any] = {"limit": limit}
    if case_id:
        query += " AND resource_id = :case_id"
        params["case_id"] = case_id
    if workflow_id:
        query += " AND details->>'workflow_id' = :workflow_id"
        params["workflow_id"] = workflow_id
    query += " ORDER BY timestamp DESC LIMIT :limit"

    rows = (await db.execute(text(query), params)).mappings().all()
    records: list[ExportAuditRecord] = []
    for row in rows:
        details = row.get("details") or {}
        records.append(
            ExportAuditRecord(
                event_id=str(row["id"]),
                action=row["action"],
                case_id=row["resource_id"],
                workflow_id=details.get("workflow_id"),
                export_id=details.get("export_id"),
                actor_id=row.get("user_id"),
                tenant_id=str(row["tenant_id"]) if row.get("tenant_id") else None,
                timestamp=row["timestamp"].isoformat(),
                outcome=row["outcome"],
                details=details,
            )
        )
    return records


@router.get("/tools/categories", response_model=ToolCategoriesResponse)
async def list_tool_categories(
    ctx: RequestContext = Depends(require_authenticated),
) -> ToolCategoriesResponse:
    """List available tool categories."""
    authorize_action("layer4.tools.list", ctx)
    categories = [
        {"id": cat.value, "name": cat.value.replace("_", " ").title()} for cat in ToolCategory
    ]

    return ToolCategoriesResponse.model_validate({"categories": categories})
