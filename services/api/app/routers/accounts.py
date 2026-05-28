from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from value_fabric.shared.error_handling.exceptions import ConflictError, NotFoundError, ServiceUnavailableError, ValidationError

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.core.tenant_enforcement import enforce_authenticated_tenant
from app.models.schemas import (
    Account,
    AccountUpdateRequest,
    AccountShareLinkResponse,
    AccountShareRevokeResponse,
    AccountSummaryResponse,
    PaginatedResponse,
)
from app.repositories.session_store import ShareLinkRepository
from app.services.distributed_store import StorePayloadError, StoreUnavailableError, get_distributed_store
from value_fabric.shared.idempotency import (
    IdempotencyConflictError,
    IdempotencyRecord,
    IdempotencyRequest,
    IdempotencyService,
    InMemoryIdempotencyStore,
    build_request_fingerprint,
)

router = APIRouter(prefix="/accounts", tags=["Accounts"])
_idempotency_service = IdempotencyService(store=InMemoryIdempotencyStore())


def _idempotency_header_value(request: Request) -> str | None:
    return request.headers.get("Idempotency-Key")


def get_share_link_repo() -> ShareLinkRepository:
    return ShareLinkRepository(get_distributed_store())


@router.get("", response_model=PaginatedResponse[Account])
async def list_accounts(
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items = db.accounts.list(tenant_id=tenant_id, limit=limit, offset=offset)
    total = db.accounts.count(tenant_id=tenant_id)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=Account, status_code=201)
async def create_account(account: Account, request: Request, tenant_id: str = Depends(tenant_required)):
    key = _idempotency_header_value(request)
    replay_request: IdempotencyRequest | None = None
    if key:
        replay_request = IdempotencyRequest(
            tenant_id=tenant_id,
            endpoint_key="POST:/v1/accounts",
            idempotency_key=key,
            request_fingerprint=build_request_fingerprint("POST", "/v1/accounts", account.model_dump()),
        )
        try:
            replay = _idempotency_service.check_replay(replay_request)
        except IdempotencyConflictError as exc:
            raise ConflictError(message=str(exc))
        if replay:
            headers = dict(replay.headers)
            headers["X-Idempotent-Replay"] = "true"
            return JSONResponse(status_code=replay.status_code, content=replay.body, headers=headers)

    enforce_authenticated_tenant(
        body_tenant_id=account.tenant_id,
        authenticated_tenant_id=tenant_id,
        route="/v1/accounts",
        operation="create_account",
    )
    account.tenant_id = tenant_id
    db.accounts.insert(account.id, account)
    if replay_request:
        _idempotency_service.store_response(
            replay_request,
            IdempotencyRecord(status_code=201, body=account.model_dump(), headers={"X-Idempotent-Replay": "false"}),
        )
    return account


@router.get("/{account_id}", response_model=Account)
async def get_account(account_id: str, tenant_id: str = Depends(tenant_required)):
    acc = db.accounts.get(account_id, tenant_id=tenant_id)
    if not acc:
        raise NotFoundError(message="Account not found")
    return acc


@router.patch("/{account_id}", response_model=Account)
async def update_account(
    account_id: str,
    fields: AccountUpdateRequest,
    request: Request,
    tenant_id: str = Depends(tenant_required),
):
    key = _idempotency_header_value(request)
    replay_request: IdempotencyRequest | None = None
    if key:
        replay_request = IdempotencyRequest(
            tenant_id=tenant_id,
            endpoint_key="PATCH:/v1/accounts/{account_id}",
            idempotency_key=key,
            request_fingerprint=build_request_fingerprint(
                "PATCH", f"/v1/accounts/{account_id}", fields.model_dump(exclude_unset=True)
            ),
        )
        try:
            replay = _idempotency_service.check_replay(replay_request)
        except IdempotencyConflictError as exc:
            raise ConflictError(message=str(exc))
        if replay:
            headers = dict(replay.headers)
            headers["X-Idempotent-Replay"] = "true"
            return JSONResponse(status_code=replay.status_code, content=replay.body, headers=headers)

    update_data = fields.model_dump(exclude_unset=True)
    if not update_data:
        raise ValidationError(message="No fields provided for update")

    acc = db.accounts.update(account_id, tenant_id=tenant_id, **update_data)
    if not acc:
        raise NotFoundError(message="Account not found")
    if replay_request:
        _idempotency_service.store_response(
            replay_request,
            IdempotencyRecord(status_code=200, body=acc.model_dump(), headers={"X-Idempotent-Replay": "false"}),
        )
    return acc


@router.get("/{account_id}/summary", response_model=AccountSummaryResponse)
async def get_account_summary(account_id: str, tenant_id: str = Depends(tenant_required)):
    acc = db.accounts.get(account_id, tenant_id=tenant_id)
    if not acc:
        raise NotFoundError(message="Account not found")

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
        raise NotFoundError(message="Account not found")

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
    except (StoreUnavailableError, StorePayloadError):
        raise ServiceUnavailableError(message="Share-link store unavailable; try again later")

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
        raise NotFoundError(message="Account not found")

    try:
        repo.revoke(tenant_id=tenant_id, account_id=account_id)
    except (StoreUnavailableError, StorePayloadError):
        raise ServiceUnavailableError(message="Share-link store unavailable; try again later")

    return AccountShareRevokeResponse(
        revoked=True,
        account_id=account_id,
    )
