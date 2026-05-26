from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.core.tenant_enforcement import enforce_authenticated_tenant
from app.models.schemas import (
    Account,
    AccountShareLinkResponse,
    AccountShareRevokeResponse,
    AccountSummaryResponse,
    PaginatedResponse,
)
from app.repositories.session_store import ShareLinkRepository
from app.services.distributed_store import StoreUnavailableError, get_distributed_store

router = APIRouter(prefix="/accounts", tags=["Accounts"])


def get_share_link_repo() -> ShareLinkRepository:
    return ShareLinkRepository(get_distributed_store())


@router.get("", response_model=PaginatedResponse[Account])
async def list_accounts(
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items = db.accounts.list(tenant_id=tenant_id, limit=limit, offset=offset)
    total = len(db.accounts.list(tenant_id=tenant_id))
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=Account, status_code=201)
async def create_account(account: Account, tenant_id: str = Depends(tenant_required)):
    enforce_authenticated_tenant(
        body_tenant_id=account.tenant_id,
        authenticated_tenant_id=tenant_id,
        route="/v1/accounts",
        operation="create_account",
    )
    account.tenant_id = tenant_id
    db.accounts.insert(account.id, account)
    return account


@router.get("/{account_id}", response_model=Account)
async def get_account(account_id: str, tenant_id: str = Depends(tenant_required)):
    acc = db.accounts.get(account_id, tenant_id=tenant_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


@router.patch("/{account_id}", response_model=Account)
async def update_account(
    account_id: str,
    fields: dict[str, Any],
    tenant_id: str = Depends(tenant_required),
):
    acc = db.accounts.update(account_id, tenant_id=tenant_id, **fields)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


@router.get("/{account_id}/summary", response_model=AccountSummaryResponse)
async def get_account_summary(account_id: str, tenant_id: str = Depends(tenant_required)):
    acc = db.accounts.get(account_id, tenant_id=tenant_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    signals = db.signals.list(
        tenant_id=tenant_id,
        filter_fn=lambda s: s.account_id == account_id,
    )
    hypotheses = db.hypotheses.list(
        tenant_id=tenant_id,
        filter_fn=lambda h: h.account_id == account_id,
    )
    roi_calcs = db.roi_calculations.list(
        tenant_id=tenant_id,
        filter_fn=lambda r: r.account_id == account_id,
    )

    return AccountSummaryResponse(
        account=acc,
        signal_count=len(signals),
        hypothesis_count=len(hypotheses),
        roi_calculation_count=len(roi_calcs),
    )


@router.post("/{account_id}/share", response_model=AccountShareLinkResponse)
async def create_share_link(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    repo: ShareLinkRepository = Depends(get_share_link_repo),
):
    acc = db.accounts.get(account_id, tenant_id=tenant_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    raw_token = secrets.token_urlsafe(32)
    token_fingerprint_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=7)

    try:
        repo.create(
            tenant_id=tenant_id,
            account_id=account_id,
            fingerprint_hash=token_fingerprint_hash,
            expires_at_ts=int(expires_at.timestamp()),
        )
    except StoreUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Share-link store unavailable; try again later",
        )

    return AccountShareLinkResponse(
        share_token=raw_token,
        account_id=account_id,
        role="read_only",
    )


@router.delete("/{account_id}/share", response_model=AccountShareRevokeResponse)
async def revoke_share_link(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    repo: ShareLinkRepository = Depends(get_share_link_repo),
):
    acc = db.accounts.get(account_id, tenant_id=tenant_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        repo.revoke(tenant_id=tenant_id, account_id=account_id)
    except StoreUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Share-link store unavailable; try again later",
        )

    return AccountShareRevokeResponse(
        revoked=True,
        account_id=account_id,
    )