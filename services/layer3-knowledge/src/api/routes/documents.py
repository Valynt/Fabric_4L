from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""Documents domain router — business case PDF export via Layer 4.

Migrated from app_monolith.py as part of ARCH-L3-011 (Sprint 3 cutover).
"""


import logging
import os
import uuid
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from ...api.dependencies import AppState, get_app_state
from ...api.models import DocumentExportRequest, DocumentExportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Documents"])


def _tenant_headers_from_request(http_request: Request) -> dict[str, str]:
    state = getattr(http_request, "state", None)
    for attr in ("governance_context", "auth_context"):
        context = getattr(state, attr, None)
        tenant_id = getattr(context, "tenant_id", None)
        if tenant_id:
            resolved = str(tenant_id)
            return {"X-Tenant-ID": resolved, "X-Value-Fabric-Tenant-ID": resolved}
    raise ValidationError(message="tenant_id is required for document export")


@router.post("/documents/export", response_model=DocumentExportResponse)
async def export_document(
    request: DocumentExportRequest,
    http_request: Request,
    app_state: AppState = Depends(get_app_state),
) -> DocumentExportResponse:
    """Export a business case to PDF via the Layer 4 DocumentExportTool."""
    export_id = f"exp-{uuid.uuid4().hex[:8]}"
    l4_api_url = os.getenv("LAYER4_API_URL", "http://layer4-agents:8004")

    try:
        tenant_headers = _tenant_headers_from_request(http_request)
        async with httpx.AsyncClient(timeout=60.0) as client:
            l4_response = await client.get(
                f"{l4_api_url}/v1/analysis/cases/{request.business_case_id}/export",
                params={"format": request.format},
                headers={"Content-Type": "application/json", **tenant_headers},
            )

            if l4_response.status_code == 404:
                raise NotFoundError(message = str(f"Business case {request.business_case_id} not found"))
            if l4_response.status_code != 200:
                logger.error(
                    "L4 export service returned %s for case %s: %s",
                    l4_response.status_code,
                    request.business_case_id,
                    l4_response.text,
                )
                raise ServiceUnavailableError(message="Export service error")

            l4_data = l4_response.json()

            if not l4_data.get("download_ready"):
                gen_response = await client.post(
                    f"{l4_api_url}/v1/tools/export-document",
                    json={
                        "document_type": request.document_type,
                        "business_case_id": request.business_case_id,
                        "format": request.format,
                        "include_provenance": request.include_provenance,
                    },
                    headers={"Content-Type": "application/json", **tenant_headers},
                    timeout=120.0,
                )
                if gen_response.status_code != 200:
                    logger.error(
                        "L4 document generation returned %s for case %s: %s",
                        gen_response.status_code,
                        request.business_case_id,
                        gen_response.text,
                    )
                    raise ServiceUnavailableError(
                        message="Document generation failed"
                    )
                gen_data = gen_response.json()
                return DocumentExportResponse(
                    export_id=export_id,
                    status="completed" if gen_data.get("success") else "failed",
                    download_url=gen_data.get("download_url"),
                    format=request.format,
                    expires_at=(
                        datetime.utcnow() + timedelta(hours=24)
                        if gen_data.get("success")
                        else None
                    ),
                    message=(
                        "PDF generated successfully"
                        if gen_data.get("success")
                        else gen_data.get("error")
                    ),
                )

            return DocumentExportResponse(
                export_id=export_id,
                status="completed",
                download_url=l4_data.get("document_url"),
                format=request.format,
                expires_at=datetime.utcnow() + timedelta(hours=24),
                message="Document ready for download",
            )

    except httpx.TimeoutException:
        logger.error(
            "Document export timed out for case %s", request.business_case_id
        )
        raise ServiceUnavailableError(message="Document generation timed out")
    except httpx.ConnectError as e:
        logger.error("Cannot connect to L4 service: %s", e)
        raise ServiceUnavailableError(message = "Document generation service unavailable")
    except (NotFoundError, ServiceUnavailableError, ValidationError):
        raise
    except HTTPException:
        raise
    except Exception as exc:
        request_id = getattr(getattr(http_request, "state", None), "request_id", None)
        logger.exception("Document export failed", extra={"request_id": request_id, "correlation_id": request_id, "exception_type": type(exc).__name__})
        raise ServiceUnavailableError(
            message="Document export failed",
            details={"error_code": "L3_DOCUMENT_EXPORT_FAILED", "request_id": request_id}
        )
