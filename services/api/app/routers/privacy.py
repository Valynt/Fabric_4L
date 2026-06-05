from __future__ import annotations

import structlog

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response
from value_fabric.shared.error_handling.exceptions import AuthorizationError, NotFoundError, ValidationError

from app.core.security import TokenPayload, require_authenticated
from app.core.tenant_context import tenant_required
from app.models.schemas import DSARCreateResponse, DSARRequestCreate, DSARRequestRecord
from app.services import dsar_service
from app.core.database import db

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/privacy", tags=["Privacy"])


@router.post('/dsar', status_code=202, response_model=DSARCreateResponse)
async def create_dsar(
    payload: DSARRequestCreate,
    request: Request,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Create a DSAR (Data Subject Access Request) for privacy compliance.

    This endpoint supports idempotency via the Idempotency-Key header.
    Retrying the same request with the same key will return the cached response
    without creating duplicate DSAR records or export jobs.
    """
    # Check for idempotency replay if key is provided
    idem_request = None
    service = None
    if idempotency_key and request:
        try:
            from value_fabric.shared.idempotency import (
                IdempotencyRequest,
                build_request_fingerprint,
            )
            from value_fabric.shared.boundaries.tenant_boundary import get_tenant_context

            ctx = get_tenant_context()
            # Get service from request state (set by middleware)
            service = getattr(request.app.state, "idempotency_service", None)

            if service:
                import json
                fingerprint = build_request_fingerprint(
                    "POST",
                    "/privacy/dsar",
                    json.loads(payload.model_dump_json())
                )
                idem_request = IdempotencyRequest(
                    tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else tenant_id,
                    endpoint_key="POST /privacy/dsar",
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                )

                replay = service.check_replay(idem_request, tenant_id=tenant_id)
                if replay is not None:
                    logger.info("DSAR request replayed from idempotency cache", tenant_id=tenant_id, user_id=auth.sub, operation="dsar_create", route="/privacy/dsar", idempotency_key=idempotency_key)
                    return replay.body
        except Exception as e:
            logger.warning("Idempotency check failed, proceeding with request", tenant_id=tenant_id, user_id=auth.sub, operation="dsar_create", route="/privacy/dsar", error=repr(e))
    
    record = await dsar_service.register_request(payload, tenant_id=tenant_id, requester_user_id=auth.sub)
    package = await dsar_service.launch_export_pipeline(record)
    refreshed = await db.dsar_requests.get(record.id, tenant_id=tenant_id)
    try:
        complete = await dsar_service.reconcile_package(refreshed)
    except ValueError as exc:
        logger.warning("DSAR reconciliation failed", tenant_id=tenant_id, user_id=auth.sub, operation="dsar_reconcile", route="/privacy/dsar", error=str(exc))
        raise ValidationError(message="Invalid DSAR request") from exc
    
    response = {"request": complete, "download_url": dsar_service.issue_download_url(package)}
    
    # Store response for idempotency if key was provided
    if idempotency_key and idem_request and service:
        try:
            from value_fabric.shared.idempotency import IdempotencyRecord
            
            service.store_response(
                idem_request,
                IdempotencyRecord(
                    status_code=202,
                    body=response,
                    headers={},
                ),
                tenant_id=tenant_id,
            )
        except Exception as e:
            logger.warning("Failed to store idempotency response", tenant_id=tenant_id, user_id=auth.sub, operation="dsar_create", route="/privacy/dsar", error=repr(e))
    
    return response


@router.get('/dsar/{request_id}', response_model=DSARRequestRecord)
async def get_dsar(request_id: str, tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)):
    request = await db.dsar_requests.get(request_id, tenant_id=tenant_id)
    if not request:
        raise NotFoundError(message='DSAR request not found')
    return await dsar_service.maybe_escalate(request)


@router.get('/dsar/packages/{package_id}/download')
async def download_dsar_package(package_id: str, token: str = Query(...), tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)):
    package = await db.dsar_packages.get(package_id, tenant_id=tenant_id)
    if not package:
        raise NotFoundError(message='DSAR package not found')
    try:
        dsar_service.validate_download_access(package, requester_user_id=auth.sub, token=token)
    except PermissionError as exc:
        logger.warning("DSAR download access denied", tenant_id=tenant_id, user_id=auth.sub, operation="dsar_download", route="/privacy/dsar/packages/download", error=str(exc))
        raise AuthorizationError(message="Access denied") from exc
    return Response(content=dsar_service.serialize_package(package), media_type='application/json')
