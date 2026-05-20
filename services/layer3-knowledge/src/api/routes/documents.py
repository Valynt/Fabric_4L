"""Documents domain router — business case PDF export via Layer 4.

Migrated from app_monolith.py as part of ARCH-L3-011 (Sprint 3 cutover).
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException

from ...api.dependencies import AppState, get_app_state
from ...api.models import DocumentExportRequest, DocumentExportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Documents"])


@router.post("/documents/export", response_model=DocumentExportResponse)
async def export_document(
    request: DocumentExportRequest,
    app_state: AppState = Depends(get_app_state),
) -> DocumentExportResponse:
    """Export a business case to PDF via the Layer 4 DocumentExportTool."""
    export_id = f"exp-{uuid.uuid4().hex[:8]}"
    l4_api_url = os.getenv("LAYER4_API_URL", "http://layer4-agents:8004")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            l4_response = await client.get(
                f"{l4_api_url}/v1/analysis/cases/{request.business_case_id}/export",
                params={"format": request.format},
                headers={"Content-Type": "application/json"},
            )

            if l4_response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Business case {request.business_case_id} not found",
                )
            if l4_response.status_code != 200:
                logger.error(
                    "L4 export service returned %s for case %s: %s",
                    l4_response.status_code,
                    request.business_case_id,
                    l4_response.text,
                )
                raise HTTPException(status_code=502, detail="Export service error")

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
                    timeout=120.0,
                )
                if gen_response.status_code != 200:
                    logger.error(
                        "L4 document generation returned %s for case %s: %s",
                        gen_response.status_code,
                        request.business_case_id,
                        gen_response.text,
                    )
                    raise HTTPException(
                        status_code=502, detail="Document generation failed"
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
        raise HTTPException(status_code=504, detail="Document generation timed out")
    except httpx.ConnectError as e:
        logger.error("Cannot connect to L4 service: %s", e)
        raise HTTPException(
            status_code=503, detail="Document generation service unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document export failed: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Document export failed: {str(e)}"
        )
