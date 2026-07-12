from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)

from app.core.database import db
from app.core.security import TokenPayload, require_authenticated
from app.core.tenant_context import tenant_required
from app.models.schemas import DSARCreateResponse, DSARRequestCreate, DSARRequestRecord
from app.services import dsar_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/privacy", tags=["Privacy"])


async def _resolve_idempotent_dsar_response(
    *,
    request: Request,
    payload: DSARRequestCreate,
    idempotency_key: str,
    tenant_id: str,
    auth: TokenPayload,
) -> tuple[dict[str, Any] | None, Any | None, Any | None]:
    """Check for a cached DSAR response and return it if the key replays.

    Returns a tuple of (cached_response_body, idempotency_request, idempotency_service).
    If no idempotency service is configured or no cached response exists, the
    latter two items are ``None``.

    Raises:
        HTTPException: 409 if the same key is replayed with a different payload.
    """
    from value_fabric.shared.boundaries.tenant_boundary import get_tenant_context
    from value_fabric.shared.idempotency import (
        IdempotencyConflictError,
        IdempotencyRequest,
        build_request_fingerprint,
    )

    service = getattr(request.app.state, "idempotency_service", None)
    if not service:
        return None, None, None

    ctx = get_tenant_context()
    import json

    fingerprint = build_request_fingerprint(
        "POST",
        "/privacy/dsar",
        json.loads(payload.model_dump_json()),
    )
    idem_request = IdempotencyRequest(
        tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else tenant_id,
        endpoint_key="POST /privacy/dsar",
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
    )

    try:
        replay = service.check_replay(idem_request, tenant_id=tenant_id)
    except IdempotencyConflictError as exc:
        logger.info(
            "DSAR idempotency conflict: key replayed with different payload",
            tenant_id=tenant_id,
            user_id=auth.sub,
            operation="dsar_create",
            route="/privacy/dsar",
            idempotency_key=idempotency_key,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": "idempotency_conflict",
                "message": "Idempotency key replayed with different payload.",
            },
        ) from exc

    if replay is not None:
        logger.info(
            "DSAR request replayed from idempotency cache",
            tenant_id=tenant_id,
            user_id=auth.sub,
            operation="dsar_create",
            route="/privacy/dsar",
            idempotency_key=idempotency_key,
        )
        return replay.body, idem_request, service

    return None, idem_request, service


async def _store_idempotent_dsar_response(
    *,
    service: Any,
    idem_request: Any,
    tenant_id: str,
    auth: TokenPayload,
    response: dict[str, Any],
) -> None:
    """Persist a DSAR response for later idempotent replays.

    Failures are logged and swallowed: a successfully created DSAR must not be
    rolled back because the idempotency cache could not be written.
    """
    from value_fabric.shared.idempotency import IdempotencyRecord

    try:
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
        logger.warning(
            "Failed to store idempotency response",
            tenant_id=tenant_id,
            user_id=auth.sub,
            operation="dsar_create",
            route="/privacy/dsar",
            error=repr(e),
        )


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
    if idempotency_key and request:
        cached_response, idem_request, service = await _resolve_idempotent_dsar_response(
            request=request,
            payload=payload,
            idempotency_key=idempotency_key,
            tenant_id=tenant_id,
            auth=auth,
        )
        if cached_response is not None:
            return cached_response
    else:
        idem_request = None
        service = None

    record = await dsar_service.register_request(payload, tenant_id=tenant_id, requester_user_id=auth.sub)
    package = await dsar_service.launch_export_pipeline(record)
    refreshed = await db.dsar_requests.get(record.id, tenant_id=tenant_id)
    try:
        complete = await dsar_service.reconcile_package(refreshed)
    except ValueError as exc:
        logger.warning("DSAR reconciliation failed", tenant_id=tenant_id, user_id=auth.sub, operation="dsar_reconcile", route="/privacy/dsar", error=str(exc))
        raise ValidationError(message="Invalid DSAR request") from exc

    response = {"request": complete, "download_url": dsar_service.issue_download_url(package)}

    if idempotency_key and idem_request and service:
        await _store_idempotent_dsar_response(
            service=service,
            idem_request=idem_request,
            tenant_id=tenant_id,
            auth=auth,
            response=response,
        )

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
