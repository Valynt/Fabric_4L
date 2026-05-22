from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.security import TokenPayload, require_authenticated
from app.core.tenant_context import tenant_required
from app.models.schemas import DSARRequestCreate
from app.services import dsar_service
from app.core.database import db

router = APIRouter(prefix="/privacy", tags=["Privacy"])


@router.post('/dsar', status_code=202)
async def create_dsar(payload: DSARRequestCreate, tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)):
    record = dsar_service.register_request(payload, tenant_id=tenant_id, requester_user_id=auth.sub)
    package = dsar_service.launch_export_pipeline(record)
    refreshed = db.dsar_requests.get(record.id, tenant_id=tenant_id)
    complete = dsar_service.reconcile_package(refreshed)
    return {"request": complete, "download_url": dsar_service.issue_download_url(package)}


@router.get('/dsar/{request_id}')
async def get_dsar(request_id: str, tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)):
    request = db.dsar_requests.get(request_id, tenant_id=tenant_id)
    if not request:
        raise HTTPException(status_code=404, detail='DSAR request not found')
    return dsar_service.maybe_escalate(request)


@router.get('/dsar/packages/{package_id}/download')
async def download_dsar_package(package_id: str, token: str = Query(...), tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)):
    package = db.dsar_packages.get(package_id, tenant_id=tenant_id)
    if not package:
        raise HTTPException(status_code=404, detail='DSAR package not found')
    try:
        dsar_service.validate_download_access(package, requester_user_id=auth.sub, token=token)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return Response(content=dsar_service.serialize_package(package), media_type='application/json')
