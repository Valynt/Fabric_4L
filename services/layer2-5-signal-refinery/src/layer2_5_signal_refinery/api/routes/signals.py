from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling.exceptions import ConflictError, NotFoundError, ValidationError

from ...clients.l3_graph_client import get_l3_client
from ...database import get_db_from_context
from ...repositories.signal_repository import SignalRepository
from ...services.signal_refinery import refine_batch
from ..auth import get_tenant_id_from_context

"""Signal API routes for L2.5 Signal Refinery.

All endpoints enforce tenant_id from authenticated context.
No endpoint accepts tenant_id from request body.

Routes:
  POST   /api/v1/signals                        Create a ValueSignal
  GET    /api/v1/signals                        List signals (account-scoped)
  GET    /api/v1/signals/account/{account_id}   All signals for an account
  GET    /api/v1/signals/{signal_id}            Get a single signal
  PATCH  /api/v1/signals/{signal_id}            Partial update
  DELETE /api/v1/signals/{signal_id}            Soft-delete
  POST   /api/v1/signals/{signal_id}/review     Human review (approve/reject)
  POST   /api/v1/signals/{signal_id}/promote    Promote to hypothesis
  POST   /api/v1/signals/refine                 Trigger L2.5 refinement batch
"""

try:  # noqa: E402
    from value_fabric.shared.models.value_signal import (  # noqa: E402
        SignalPromoteRequest,
        SignalRefineRequest,
        SignalReviewRequest,
        ValueSignalCreate,
        ValueSignalListResponse,
        ValueSignalUpdate,
    )
except ImportError:
    # Fallback: use local Pydantic models when shared package unavailable
    from pydantic import BaseModel  # noqa: E402
    from typing import Optional  # noqa: E402

    class ValueSignalCreate(BaseModel):  # type: ignore[no-redef]
        account_id: str
        type: str
        content: str
        confidence: float
        trust_score: float = 0.0
        lifecycle_state: str = "draft"
        evidence: list = []
        provenance: dict = {}
        source_refs: list = []

    class ValueSignalUpdate(BaseModel):  # type: ignore[no-redef]
        lifecycle_state: Optional[str] = None
        validation_notes: Optional[str] = None
        reviewer_id: Optional[str] = None
        impact_area: Optional[str] = None
        estimated_value: Optional[float] = None
        currency: Optional[str] = None
        time_horizon: Optional[str] = None
        value_driver_id: Optional[str] = None

    class SignalReviewRequest(BaseModel):  # type: ignore[no-redef]
        status: str
        notes: Optional[str] = None

    class SignalPromoteRequest(BaseModel):  # type: ignore[no-redef]
        value_path_category: str
        value_driver_id: Optional[str] = None

    class RawSignalInput(BaseModel):  # type: ignore[no-redef]
        account_id: str
        type: str = "pain"
        content: str
        confidence: float
        evidence: list = []
        provenance: dict = {}
        source_refs: list = []

    class SignalRefineRequest(BaseModel):  # type: ignore[no-redef]
        account_id: str
        raw_signals: Optional[list] = None
        source_refs: list = []
        extraction_run_id: Optional[str] = None

    class ValueSignalListResponse(BaseModel):  # type: ignore[no-redef]
        items: list
        total: int
        limit: int
        offset: int


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])

_VALID_REVIEW_STATES = {"validated", "rejected"}


def _get_repo(db: AsyncSession, tenant_id: str) -> SignalRepository:
    return SignalRepository(db, tenant_id)


# ---------------------------------------------------------------------------
# POST /api/v1/signals — create
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_signal(
    body: ValueSignalCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    tenant_id = get_tenant_id_from_context()
    repo = _get_repo(db, tenant_id)

    data = body.model_dump(mode="json")
    # Ensure evidence items have IDs
    for item in data.get("evidence") or []:
        if not item.get("id"):
            item["id"] = str(uuid.uuid4())
    # Stringify UUIDs for storage (model_dump(mode='json') already converts most,
    # but belt-and-suspenders for any nested objects that may have slipped through)
    for field in ("account_id", "opportunity_id", "value_driver_id", "stakeholder_id", "reviewer_id"):
        if data.get(field):
            data[field] = str(data[field])

    signal = await repo.create(data)

    # Push to L3 asynchronously (best-effort, non-blocking)
    try:
        asyncio.create_task(
            get_l3_client().push_signal(
                signal,
                tenant_id,
                request.headers.get("X-Request-ID"),
                request.headers.get("X-Correlation-ID")
            )
        )
    except RuntimeError:
        # No running event loop in test environments — skip background push
        pass

    return signal


# ---------------------------------------------------------------------------
# GET /api/v1/signals — list (account-scoped)
# ---------------------------------------------------------------------------


@router.get("")
async def list_signals(
    request: Request,
    account_id: str = Query(...),
    types: list[str] | None = Query(None),
    lifecycle_state: list[str] | None = Query(None),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    min_trust_score: float | None = Query(None, ge=0.0, le=1.0),
    impact_area: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    tenant_id = get_tenant_id_from_context()
    repo = _get_repo(db, tenant_id)

    items, total = await repo.list(
        account_id,
        types=types,
        lifecycle_states=lifecycle_state,
        min_confidence=min_confidence,
        min_trust_score=min_trust_score,
        impact_area=impact_area,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------------------------------------------------------------------------
# GET /api/v1/signals/account/{account_id} — all signals for account
# ---------------------------------------------------------------------------


@router.get("/account/{account_id}")
async def get_account_signals(
    account_id: str,
    request: Request,
    lifecycle_state: list[str] | None = Query(None),
    types: list[str] | None = Query(None),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    tenant_id = get_tenant_id_from_context()
    repo = _get_repo(db, tenant_id)

    items, total = await repo.list(
        account_id,
        types=types,
        lifecycle_states=lifecycle_state,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------------------------------------------------------------------------
# GET /api/v1/signals/{signal_id} — single signal
# ---------------------------------------------------------------------------


@router.get("/{signal_id}")
async def get_signal(
    signal_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    tenant_id = get_tenant_id_from_context()
    repo = _get_repo(db, tenant_id)

    signal = await repo.get(signal_id)
    if not signal:
        raise NotFoundError(message = "Signal not found")
    return signal


# ---------------------------------------------------------------------------
# PATCH /api/v1/signals/{signal_id} — partial update
# ---------------------------------------------------------------------------


@router.patch("/{signal_id}")
async def update_signal(
    signal_id: str,
    body: ValueSignalUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    tenant_id = get_tenant_id_from_context()
    repo = _get_repo(db, tenant_id)

    updates = {k: v for k, v in body.model_dump(mode="json").items() if v is not None}
    if not updates:
        raise ValidationError(message = "No fields to update")

    # Stringify UUID fields
    for field in ("reviewer_id", "value_driver_id", "supersedes_signal_id"):
        if updates.get(field):
            updates[field] = str(updates[field])
    if updates.get("related_signal_ids"):
        updates["related_signal_ids"] = [str(x) for x in updates["related_signal_ids"]]
    if updates.get("lifecycle_state"):
        updates["lifecycle_state"] = str(updates["lifecycle_state"])
    if updates.get("impact_area"):
        updates["impact_area"] = str(updates["impact_area"])

    signal = await repo.update(signal_id, updates)
    if not signal:
        raise NotFoundError(message = "Signal not found")
    return signal


# ---------------------------------------------------------------------------
# DELETE /api/v1/signals/{signal_id} — soft-delete
# ---------------------------------------------------------------------------


@router.delete("/{signal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_signal(
    signal_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_from_context),
) -> None:
    tenant_id = get_tenant_id_from_context()
    repo = _get_repo(db, tenant_id)

    deleted = await repo.soft_delete(signal_id)
    if not deleted:
        raise NotFoundError(message = "Signal not found")


# ---------------------------------------------------------------------------
# POST /api/v1/signals/{signal_id}/review — human review
# ---------------------------------------------------------------------------


@router.post("/{signal_id}/review")
async def review_signal(
    signal_id: str,
    body: SignalReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    tenant_id = get_tenant_id_from_context()
    repo = _get_repo(db, tenant_id)

    new_state = body.status.value if hasattr(body.status, "value") else str(body.status)
    if new_state not in _VALID_REVIEW_STATES:
        raise ValidationError(message=f"Review status must be one of: {_VALID_REVIEW_STATES}")

    updates: dict[str, Any] = {
        "lifecycle_state": new_state,
        "reviewed_at": datetime.now(UTC),  # datetime object, not ISO string
    }
    if body.notes:
        updates["validation_notes"] = body.notes

    signal = await repo.update(signal_id, updates)
    if not signal:
        raise NotFoundError(message = "Signal not found")
    return signal


# ---------------------------------------------------------------------------
# POST /api/v1/signals/{signal_id}/promote — promote to hypothesis
# ---------------------------------------------------------------------------


@router.post("/{signal_id}/promote")
async def promote_signal(
    signal_id: str,
    body: SignalPromoteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    tenant_id = get_tenant_id_from_context()
    repo = _get_repo(db, tenant_id)

    signal = await repo.get(signal_id)
    if not signal:
        raise NotFoundError(message = "Signal not found")

    if signal["lifecycle_state"] not in ("validated", "extracted"):
        raise ConflictError(message=f"Cannot promote signal in state '{signal['lifecycle_state']}'. Must be validated or extracted.")

    updates: dict[str, Any] = {"lifecycle_state": "promoted"}
    if body.value_driver_id:
        updates["value_driver_id"] = str(body.value_driver_id)

    promoted = await repo.update(signal_id, updates)
    if not promoted:
        raise NotFoundError(message = "Signal not found")

    return {
        **promoted,
        "value_path_category": body.value_path_category,
    }


# ---------------------------------------------------------------------------
# POST /api/v1/signals/refine — trigger L2.5 refinement batch
# ---------------------------------------------------------------------------


@router.post("/refine", status_code=status.HTTP_202_ACCEPTED)
async def refine_signals(
    body: SignalRefineRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Trigger L2.5 refinement on a batch of raw L2 extraction payloads.

    Accepts ``raw_signals`` (preferred) — actual L2 extraction output — or
    falls back to ``source_refs`` for backward compatibility. The fallback
    produces signals with synthetic content and should not be used in production.
    """
    tenant_id = get_tenant_id_from_context()
    repo = _get_repo(db, tenant_id)

    now = datetime.now(UTC).isoformat()

    if body.raw_signals:
        # Preferred path: caller supplied actual L2 extraction payloads.
        raws = []
        for rs in body.raw_signals:
            raw = rs.model_dump(mode="json") if hasattr(rs, "model_dump") else dict(rs)
            raw["account_id"] = str(raw["account_id"])
            # Ensure provenance has required fields
            prov = raw.get("provenance") or {}
            prov.setdefault("extractor", "system")
            prov.setdefault("method", "l2_extraction")
            prov.setdefault("source_system", "layer2_extraction")
            prov.setdefault("extracted_at", now)
            if body.extraction_run_id:
                prov.setdefault("run_id", body.extraction_run_id)
            raw["provenance"] = prov
            raws.append(raw)
    else:
        # Backward-compatible fallback: source_refs only.
        # Produces signals with synthetic content — not suitable for production use.
        if not body.source_refs:
            raise ValidationError(message="Provide raw_signals (preferred) or source_refs.")
        raws = [
            {
                "account_id": str(body.account_id),
                "type": "pain",
                "content": f"Signal from source: {ref}",
                "confidence": 0.5,
                "provenance": {
                    "extractor": "system",
                    "method": "l2_extraction",
                    "run_id": body.extraction_run_id,
                    "source_system": "layer2_extraction",
                    "extracted_at": now,
                },
                "source_refs": [ref],
                "evidence": [],
            }
            for ref in body.source_refs
        ]

    refined = refine_batch(raws)
    created = []
    for r in refined:
        r["tenant_id"] = tenant_id
        signal = await repo.create(r)
        created.append(signal)
        try:
            asyncio.create_task(
                get_l3_client().push_signal(
                    signal,
                    tenant_id,
                    request.headers.get("X-Request-ID"),
                    request.headers.get("X-Correlation-ID")
                )
            )
        except RuntimeError:
            pass

    return {
        "refined": len(created),
        "signal_ids": [s["id"] for s in created],
    }
