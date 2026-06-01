from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
)

"""Signal lifecycle API routes."""

import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
from pydantic import BaseModel, ConfigDict

from layer2_extraction.models.signal_lifecycle import (
    OperationalSignalLifecycleRecord,
    SignalLifecycleActor,
)
from layer2_extraction.services.signal_lifecycle_service import (
    InvalidLifecycleTransitionError,
    SignalLifecycleService,
)

router = APIRouter(prefix="/signals", tags=["signal-lifecycle"])
_service = SignalLifecycleService()


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_signal_id: str


def _actor_from_request(request: Request) -> SignalLifecycleActor:
    if not hasattr(request.state, "governance_context"):
        raise AuthenticationError(message = "Tenant context required")
    ctx = request.state.governance_context
    tenant_id = getattr(ctx, "tenant_id", None)
    account_id = getattr(ctx, "account_id", None)
    actor_id = getattr(ctx, "user_id", None) or getattr(ctx, "subject", None)
    if not tenant_id or not account_id or not actor_id:
        raise AuthenticationError(message = "Tenant/account context required")
    return SignalLifecycleActor(actor_id=str(actor_id), account_id=str(account_id))


@router.post("/{signal_id}", response_model=OperationalSignalLifecycleRecord)
async def create_signal(signal_id: str, request: Request) -> OperationalSignalLifecycleRecord:
    actor = _actor_from_request(request)
    tenant_id = str(request.state.governance_context.tenant_id)
    return _service.create_signal(signal_id=signal_id, tenant_id=tenant_id, actor=actor)


@router.post("/{signal_id}/supersede", response_model=OperationalSignalLifecycleRecord)
async def supersede_signal(signal_id: str, body: TransitionRequest, request: Request) -> OperationalSignalLifecycleRecord:
    actor = _actor_from_request(request)
    tenant_id = str(request.state.governance_context.tenant_id)
    try:
        return _service.supersede_signal(signal_id, body.target_signal_id, tenant_id, actor)
    except KeyError as exc:
        raise NotFoundError(message = "Signal not found") from exc
    except InvalidLifecycleTransitionError as exc:
        logger.warning("Invalid signal supersede transition: %s", exc)
        raise ConflictError(message="Invalid lifecycle transition") from exc


@router.post("/{signal_id}/merge", response_model=OperationalSignalLifecycleRecord)
async def merge_signal(signal_id: str, body: TransitionRequest, request: Request) -> OperationalSignalLifecycleRecord:
    actor = _actor_from_request(request)
    tenant_id = str(request.state.governance_context.tenant_id)
    try:
        return _service.merge_signal(signal_id, body.target_signal_id, tenant_id, actor)
    except KeyError as exc:
        raise NotFoundError(message = "Signal not found") from exc
    except InvalidLifecycleTransitionError as exc:
        logger.warning("Invalid signal merge transition: %s", exc)
        raise ConflictError(message="Invalid lifecycle transition") from exc
