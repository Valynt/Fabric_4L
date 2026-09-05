from __future__ import annotations

"""FastAPI routes for the Fabric Harness.

Exposes the SqlHarnessRegistry as a REST API under /v1/harness/*.

All routes:
  - Extract tenant_id from authenticated RequestContext (never from request body).
  - Inject SqlHarnessRegistry via get_harness_registry() dependency.
  - Return 404 on missing resources, 403 on tenant mismatch, 422 on semantic
    validation failures (invalid transitions, terminal-state violations).
  - Follow the same error shape as /v1/workflows/*.
"""
import asyncio
import logging
import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling import sanitize_log_error
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated, require_content_admin

from ...database import get_db_from_context
from ...harness.api_models import (
    CheckpointListResponse,
    CheckpointResponse,
    CreateGateRequest,
    CreateRunRequest,
    GateDecisionRequest,
    GateListResponse,
    GateResponse,
    HarnessHealthResponse,
    RunListResponse,
    RunResponse,
    TraceEventResponse,
    TransitionRequest,
    TransitionResponse,
    ValidateClaimsRequest,
    ValidateClaimsResponse,
    ValidationResultResponse,
    ValidationSummaryResponse,
)
from ...harness.factory import make_live_l5_registry, make_sql_registry
from ...harness.models import GateStatus, HarnessRunStatus, HarnessState, HarnessWorkflowType
from ...harness.policies import aggregate_validation_results
from ...harness.registry import HarnessRegistryError
from ...harness.sql_stores import SqlHarnessRegistry
from ...harness.validation_hooks import ClaimValidationRequest as DomainClaimValidationRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["harness"])


# ---------------------------------------------------------------------------
# Dependency: registry
# ---------------------------------------------------------------------------


async def get_harness_registry(
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> SqlHarnessRegistry:
    """Inject a SqlHarnessRegistry wired to the current session and tenant."""
    l5_url = os.environ.get("LAYER5_GROUND_TRUTH_URL")
    if l5_url and os.environ.get("LAYER5_SERVICE_TOKEN"):
        try:
            return await make_live_l5_registry(
                session=db,
                tenant_id=_ctx.tenant_id,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "L5 registry initialization failed, falling back to SQL registry",
                extra={"error": sanitize_log_error(exc)},
            )
    return await make_sql_registry(session=db)


HarnessRegistryDep = Annotated[SqlHarnessRegistry, Depends(get_harness_registry)]
AuthCtxDep = Annotated[RequestContext, Depends(require_authenticated)]
# Gate decisions require content_admin or higher (reviewer/admin role).
ContentAdminCtxDep = Annotated[RequestContext, Depends(require_content_admin)]


def _raise_registry_access_denied(
    exc: HarnessRegistryError,
    *,
    event: str = "harness_registry_error",
    error_code: str = "HARNESS_REGISTRY_ERROR",
    message: str = "Harness registry access denied",
) -> None:
    logger.warning(
        event,
        extra={"error_code": error_code, "error": sanitize_log_error(exc)},
    )
    raise AuthorizationError(message=message)


async def _require_run(
    registry: SqlHarnessRegistry,
    *,
    run_id: str,
    tenant_id: str,
) -> Any:
    try:
        return await registry.get_run(run_id, tenant_id)
    except KeyError:
        raise NotFoundError(message=f"Run {run_id} not found")
    except HarnessRegistryError as exc:
        _raise_registry_access_denied(exc)


# ---------------------------------------------------------------------------
# Run management
# ---------------------------------------------------------------------------


@router.post(
    "/harness/runs",
    response_model=RunResponse,
    status_code=201,
    summary="Create a harness run",
)
async def create_run(
    body: CreateRunRequest,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> RunResponse:
    """Create a new HarnessRun for the authenticated tenant."""

    run = await registry.create_run(
        tenant_id=ctx.tenant_id,
        workflow_type=body.workflow_type,
        initiated_by=body.initiated_by,
        account_id=body.account_id,
        value_pack_id=body.value_pack_id,
    )
    return RunResponse.from_domain(run)


@router.get(
    "/harness/runs",
    response_model=RunListResponse,
    summary="List harness runs",
)
async def list_runs(
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
    status: HarnessRunStatus | None = Query(None),
    workflow_type: HarnessWorkflowType | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> RunListResponse:
    """List harness runs for the authenticated tenant."""
    runs, total = await registry.list_runs(
        tenant_id=ctx.tenant_id,
        status=status,
        workflow_type=workflow_type,
        limit=limit,
        offset=offset,
    )
    return RunListResponse(
        items=[RunResponse.from_domain(r) for r in runs],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(runs)) < total,
    )


@router.get(
    "/harness/runs/{run_id}",
    response_model=RunResponse,
    summary="Get a harness run",
)
async def get_run(
    run_id: str,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> RunResponse:
    """Get a single harness run by ID."""
    run = await _require_run(registry, run_id=run_id, tenant_id=ctx.tenant_id)
    return RunResponse.from_domain(run)


@router.post(
    "/harness/runs/{run_id}/transition",
    response_model=TransitionResponse,
    summary="Advance run state",
)
async def transition_run(
    run_id: str,
    body: TransitionRequest,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> TransitionResponse:
    """Advance the state machine for a harness run."""
    try:
        run, event = await registry.transition(
            run_id=run_id,
            tenant_id=ctx.tenant_id,
            to_state=body.to_state,
            validation_results=body.validation_results,
            human_override=body.human_override,
            state_payload=body.state_payload,
        )
    except KeyError:
        raise NotFoundError(message=f"Run {run_id} not found")
    except HarnessRegistryError as exc:
        _raise_registry_access_denied(exc)
    except ValueError as exc:
        # Do not forward raw exception text to HTTP responses: ValueError
        # messages from the registry may embed internal state. Log sanitized
        # details server-side and return a static, tenant-safe message.
        logger.warning(
            "Run transition rejected for run %s: %s",
            run_id,
            sanitize_log_error(exc),
        )
        raise ValidationError(message="Invalid run transition request")
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Unexpected error transitioning run %s", run_id)
        raise ValidationError(message="Run transition failed")

    return TransitionResponse(
        run=RunResponse.from_domain(run),
        trace_event=TraceEventResponse.from_domain(event) if event else None,
    )


@router.delete(
    "/harness/runs/{run_id}",
    status_code=204,
    summary="Cancel a harness run",
)
async def cancel_run(
    run_id: str,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> None:
    """Cancel (transition to CANCELLED) a harness run."""
    run = await _require_run(registry, run_id=run_id, tenant_id=ctx.tenant_id)

    if run.current_state.is_terminal:
        raise ValidationError(message=f"Run {run_id} is already in terminal state {run.current_state}")

    try:
        await registry.transition(
            run_id=run_id,
            tenant_id=ctx.tenant_id,
            to_state=HarnessState.CANCELLED,
            human_override=True,
        )
    except HarnessRegistryError as exc:
        _raise_registry_access_denied(exc)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Error cancelling run %s", run_id)
        raise ValidationError(message="Run cancellation failed")


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------


@router.get(
    "/harness/runs/{run_id}/checkpoints",
    response_model=CheckpointListResponse,
    summary="List checkpoints for a run",
)
async def list_checkpoints(
    run_id: str,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> CheckpointListResponse:
    """List all checkpoints for a harness run."""
    await _require_run(registry, run_id=run_id, tenant_id=ctx.tenant_id)

    checkpoints = await registry.get_checkpoints(run_id, ctx.tenant_id)
    return CheckpointListResponse(
        items=[CheckpointResponse.from_domain(c) for c in checkpoints],
        total=len(checkpoints),
    )


@router.get(
    "/harness/runs/{run_id}/checkpoints/latest",
    response_model=CheckpointResponse,
    summary="Get latest checkpoint for a run",
)
async def get_latest_checkpoint(
    run_id: str,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> CheckpointResponse:
    """Get the most recent checkpoint for a harness run."""
    await _require_run(registry, run_id=run_id, tenant_id=ctx.tenant_id)

    checkpoints = await registry.get_checkpoints(run_id, ctx.tenant_id)
    if not checkpoints:
        raise NotFoundError(message = str(f"No checkpoints found for run {run_id}"))
    latest = max(checkpoints, key=lambda c: c.created_at)
    return CheckpointResponse.from_domain(latest)


# ---------------------------------------------------------------------------
# Human gates
# ---------------------------------------------------------------------------


@router.get(
    "/harness/runs/{run_id}/gates",
    response_model=GateListResponse,
    summary="List gates for a run",
)
async def list_gates(
    run_id: str,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> GateListResponse:
    """List all human gates for a harness run."""
    await _require_run(registry, run_id=run_id, tenant_id=ctx.tenant_id)

    gates = await registry.list_gates_for_run(run_id, ctx.tenant_id)
    return GateListResponse(
        items=[GateResponse.from_domain(g) for g in gates],
        total=len(gates),
    )


@router.post(
    "/harness/runs/{run_id}/gates",
    response_model=GateResponse,
    status_code=201,
    summary="Create a human gate",
)
async def create_gate(
    run_id: str,
    body: CreateGateRequest,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> GateResponse:
    """Create a human gate for a harness run."""
    await _require_run(registry, run_id=run_id, tenant_id=ctx.tenant_id)

    gate = await registry.create_human_gate(
        run_id=run_id,
        tenant_id=ctx.tenant_id,
        gate_type=body.gate_type,
        action_class=body.action_class,
    )
    return GateResponse.from_domain(gate)


@router.post(
    "/harness/gates/{gate_id}/decide",
    response_model=GateResponse,
    summary="Decide a human gate",
)
async def decide_gate(
    gate_id: str,
    body: GateDecisionRequest,
    registry: HarnessRegistryDep,
    ctx: ContentAdminCtxDep,
) -> GateResponse:
    """Approve, reject, modify, or expire a human gate.

    Requires content_admin, tenant_admin, or super_admin role.
    decision_by is always server-derived from ctx.user_id — any
    body-supplied value is ignored to prevent spoofing.
    """
    try:
        _gate = await registry.get_gate(gate_id, ctx.tenant_id)
    except KeyError:
        raise NotFoundError(message=f"Gate {gate_id} not found")
    except HarnessRegistryError as exc:
        _raise_registry_access_denied(exc)

    decision_map = {
        "approved": GateStatus.APPROVED,
        "rejected": GateStatus.REJECTED,
        "modified": GateStatus.MODIFIED,
        "expired": GateStatus.EXPIRED,
    }

    # decision_by is always server-derived — never from request body.
    server_decision_by = ctx.user_id or ctx.tenant_id

    try:
        updated_gate = await registry.decide_gate(
            gate_id=gate_id,
            tenant_id=ctx.tenant_id,
            decision=decision_map[body.decision],
            decision_by=server_decision_by,
            decision_reason=body.decision_reason,
        )
    except (ValueError, HarnessRegistryError) as exc:
        logger.warning(
            "harness_gate_decision_error",
            extra={"error_code": "HARNESS_GATE_DECISION_ERROR", "error": sanitize_log_error(exc)},
        )
        raise ValidationError(message = "Invalid gate decision request")

    return GateResponse.from_domain(updated_gate)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@router.post(
    "/harness/runs/{run_id}/validate",
    response_model=ValidateClaimsResponse,
    summary="Validate claims for a run",
)
async def validate_claims(
    run_id: str,
    body: ValidateClaimsRequest,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> ValidateClaimsResponse:
    """Validate a list of claims through the L5 ValidationHook."""
    await _require_run(registry, run_id=run_id, tenant_id=ctx.tenant_id)

    domain_requests = [
        DomainClaimValidationRequest(
            tenant_id=ctx.tenant_id,
            claim_id=c.claim_id,
            claim_text=c.claim_text,
            evidence_refs=c.evidence_refs,
            value_pack_id=c.value_pack_id,
            account_id=c.account_id,
        )
        for c in body.claims
    ]

    try:
        results = await registry.validate_claims(ctx.tenant_id, domain_requests, run_id=run_id)
    except HarnessRegistryError as exc:
        logger.warning("harness_validation_error", extra={"error_code": "HARNESS_VALIDATION_ERROR", "error": sanitize_log_error(exc)})
        raise ValidationError(message = "Claim validation failed")

    summary = aggregate_validation_results(results)
    result_responses = [ValidationResultResponse.from_domain(r) for r in results]
    return ValidateClaimsResponse(
        results=result_responses,
        total=summary.total,
        passed=summary.passed,
        failed=summary.failed,
        needs_review=summary.needs_review,
        insufficient_evidence=summary.insufficient_evidence,
        summary=ValidationSummaryResponse.from_domain(summary),
    )


@router.get(
    "/harness/runs/{run_id}/validation",
    response_model=ValidateClaimsResponse,
    summary="Get validation results for a run",
)
async def get_run_validation(
    run_id: str,
    registry: HarnessRegistryDep,
    ctx: AuthCtxDep,
) -> ValidateClaimsResponse:
    """Return the stored validation results for a run.

    Returns an empty summary when no claims have been validated yet.
    Tenant-scoped: 403 if run belongs to a different tenant.
    """
    await _require_run(registry, run_id=run_id, tenant_id=ctx.tenant_id)

    # Retrieve stored validation results from the SQL registry if available.
    results = []
    if hasattr(registry, "get_validation_results"):
        try:
            results = await registry.get_validation_results(run_id, ctx.tenant_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("get_run_validation: failed to load results for run %s: %s", run_id, exc)

    summary = aggregate_validation_results(results)
    result_responses = [ValidationResultResponse.from_domain(r) for r in results]
    return ValidateClaimsResponse(
        results=result_responses,
        total=summary.total,
        passed=summary.passed,
        failed=summary.failed,
        needs_review=summary.needs_review,
        insufficient_evidence=summary.insufficient_evidence,
        summary=ValidationSummaryResponse.from_domain(summary),
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get(
    "/harness/health",
    response_model=HarnessHealthResponse,
    summary="Harness health check",
)
async def harness_health(
    registry: HarnessRegistryDep,
) -> HarnessHealthResponse:
    """Return harness health: validation availability and L5 connectivity."""
    validation_available = registry.validation_available

    l5_healthy = False
    if validation_available:
        try:
            l5_healthy = await registry._validation.is_available()
        except asyncio.CancelledError:
            raise
        except Exception:
            l5_healthy = False

    # DB health: if we got this far the session is alive
    db_healthy = True

    status = "ok" if (db_healthy and (not validation_available or l5_healthy)) else "degraded"

    return HarnessHealthResponse(
        status=status,
        validation_available=validation_available,
        l5_healthy=l5_healthy,
        db_healthy=db_healthy,
    )
