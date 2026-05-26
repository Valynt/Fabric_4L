from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.security import TokenPayload, require_authenticated
from app.core.tenant_context import tenant_required
from app.models.schemas import DSARRequestCreate
from app.services import dsar_service
from app.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/privacy", tags=["Privacy"])


@router.post('/dsar', status_code=202)
async def create_dsar(payload: DSARRequestCreate, tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)):
    record = await dsar_service.register_request(payload, tenant_id=tenant_id, requester_user_id=auth.sub)
    package = await dsar_service.launch_export_pipeline(record)
    refreshed = await dsar_service._run_blocking_repo_call("dsar_requests.get", db.dsar_requests.get, record.id, tenant_id=tenant_id)
    try:
        complete = await dsar_service.reconcile_package(refreshed)
    except ValueError as exc:
        logger.warning("DSAR reconciliation failed: %s", exc)
        raise HTTPException(status_code=422, detail="Invalid DSAR request") from exc
    return {"request": complete, "download_url": dsar_service.issue_download_url(package)}


@router.get('/dsar/{request_id}')
async def get_dsar(request_id: str, tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)):
    request = await dsar_service._run_blocking_repo_call("dsar_requests.get", db.dsar_requests.get, request_id, tenant_id=tenant_id)
    if not request:
        raise HTTPException(status_code=404, detail='DSAR request not found')
    return await dsar_service.maybe_escalate(request)


@router.get('/dsar/packages/{package_id}/download')
async def download_dsar_package(package_id: str, token: str = Query(...), tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)):
    package = await dsar_service._run_blocking_repo_call("dsar_packages.get", db.dsar_packages.get, package_id, tenant_id=tenant_id)
    if not package:
        raise HTTPException(status_code=404, detail='DSAR package not found')
    try:
        dsar_service.validate_download_access(package, requester_user_id=auth.sub, token=token)
    except PermissionError as exc:
        logger.warning("DSAR download access denied: %s", exc)
        raise HTTPException(status_code=403, detail="Access denied") from exc
    return Response(content=dsar_service.serialize_package(package), media_type='application/json')
