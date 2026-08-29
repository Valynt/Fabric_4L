from __future__ import annotations

from fastapi import APIRouter, Depends, status
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated, require_tenant_admin

from app.core.api_key_hash import generate_api_key
from app.core.security import require_bearer_declaration
from app.models.api_key import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListResponse,
)
from app.repositories.api_key_repository import APIKeyRepository

router = APIRouter(
    prefix="/auth/api-keys",
    tags=["API Keys"],
    dependencies=[Depends(require_bearer_declaration)],
)


def _get_repo() -> APIKeyRepository:
    return APIKeyRepository()


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    request: APIKeyCreateRequest,
    ctx: RequestContext = Depends(require_tenant_admin),
    repo: APIKeyRepository = Depends(_get_repo),
) -> APIKeyCreateResponse:
    raw, key_id, prefix = generate_api_key(name=request.name)
    record = repo.create_key(
        tenant_id=str(ctx.tenant_id),
        request=request,
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    return APIKeyCreateResponse(
        key_id=record.key_id,
        name=record.name,
        api_key=raw,
        prefix=record.prefix,
        tenant_id=record.tenant_id,
        role=record.role,
        permissions=record.permissions,
        created_at=record.created_at,
    )


@router.get("", response_model=APIKeyListResponse)
def list_api_keys(
    ctx: RequestContext = Depends(require_authenticated),
    repo: APIKeyRepository = Depends(_get_repo),
) -> APIKeyListResponse:
    items = repo.list_for_tenant(str(ctx.tenant_id))
    return APIKeyListResponse(items=items)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: str,
    ctx: RequestContext = Depends(require_tenant_admin),
    repo: APIKeyRepository = Depends(_get_repo),
) -> None:
    repo.revoke_key(str(ctx.tenant_id), key_id)
