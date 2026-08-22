from __future__ import annotations

"""Route-level tests for /v1/harness/* endpoints.

Covers:
  - Invalid state transition returns 422 (not 400)
  - Cancel of a terminal run returns 422
  - Cross-tenant run access returns 404
  - POST /v1/harness/gates/{gate_id}/decide uses decision_by from auth context
  - POST /v1/harness/gates/{gate_id}/decide calls registry.decide_gate (telemetry emitted inside)
"""


from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_TENANT_A = "tenant-a"
_TENANT_B = "tenant-b"
_USER_ID = "user-alice"
_RUN_ID = "run-001"
_GATE_ID = "gate-001"
_TRACE_ID = "trace-abc"


def _make_run(run_id=_RUN_ID, tenant_id=_TENANT_A, state=None, status=None):
    from layer4_agents.harness.models import (
        HarnessRun,
        HarnessRunStatus,
        HarnessState,
        HarnessWorkflowType,
        InitiatedBy,
    )
    return HarnessRun(
        id=run_id, tenant_id=tenant_id, account_id=None,
        workflow_type=HarnessWorkflowType.ROI_CALCULATOR_GENERATION,
        initiated_by=InitiatedBy.USER,
        status=status or HarnessRunStatus.RUNNING,
        current_state=state or HarnessState.VALIDATE_CLAIMS,
        value_pack_id=None, trace_id=_TRACE_ID, created_at=_NOW, updated_at=_NOW,
    )


def _make_gate(gate_id=_GATE_ID, run_id=_RUN_ID, tenant_id=_TENANT_A, status=None, decision_by=None):
    from layer4_agents.harness.models import GateStatus, GateType, HumanGate
    return HumanGate(
        id=gate_id, run_id=run_id, tenant_id=tenant_id,
        gate_type=GateType.APPROVE_CLAIMS,
        status=status or GateStatus.PENDING,
        decision_by=decision_by, decision_reason=None, created_at=_NOW, decided_at=None,
    )


def _build_app(registry_mock, tenant_id=_TENANT_A, user_id=_USER_ID):
    from fastapi import FastAPI
    from value_fabric.shared.error_handling.handlers import register_exception_handlers
    from value_fabric.shared.identity.context import RequestContext
    from value_fabric.shared.identity.dependencies import (
        require_authenticated,
        require_content_admin,
    )

    from layer4_agents.api.routes.harness import get_harness_registry
    from layer4_agents.api.routes.harness import router as harness_router

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(harness_router, prefix="/v1")

    async def _mock_ctx():
        return RequestContext(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=["content_admin"],
        )

    async def _mock_registry():
        return registry_mock

    app.dependency_overrides[require_authenticated] = _mock_ctx
    app.dependency_overrides[require_content_admin] = _mock_ctx
    app.dependency_overrides[get_harness_registry] = _mock_registry
    return app


@pytest.mark.asyncio
async def test_invalid_transition_returns_422():
    """Invalid state machine transition must return 422."""
    from httpx import ASGITransport, AsyncClient
    registry = MagicMock()
    registry.get_run = AsyncMock(return_value=_make_run())
    registry.transition = AsyncMock(side_effect=ValueError("Invalid transition: VALIDATE_CLAIMS -> INIT"))
    app = _build_app(registry)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/v1/harness/runs/{_RUN_ID}/transition", json={"to_state": "INIT"})
    assert response.status_code == 422
    assert "INIT" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_cancel_terminal_run_returns_422():
    """Cancelling a terminal run must return 422."""
    from httpx import ASGITransport, AsyncClient

    from layer4_agents.harness.models import HarnessRunStatus, HarnessState
    terminal_run = _make_run(state=HarnessState.DONE, status=HarnessRunStatus.COMPLETED)
    registry = MagicMock()
    registry.get_run = AsyncMock(return_value=terminal_run)
    app = _build_app(registry)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/v1/harness/runs/{_RUN_ID}")
    assert response.status_code == 422
    assert "terminal" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_cross_tenant_run_returns_404():
    """Registry raises RunNotFoundError for a run not visible to the requesting tenant; route returns 404."""
    from httpx import ASGITransport, AsyncClient

    from layer4_agents.harness.registry import RunNotFoundError
    registry = MagicMock()
    registry.get_run = AsyncMock(side_effect=RunNotFoundError(_RUN_ID))
    app = _build_app(registry, tenant_id=_TENANT_B)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/v1/harness/runs/{_RUN_ID}")
    assert response.status_code == 404
    # Verify the registry was called with the requesting tenant's context, not a leaked tenant_id.
    registry.get_run.assert_awaited_once_with(_RUN_ID, _TENANT_B)


@pytest.mark.asyncio
async def test_get_run_validation_checks_run_with_authenticated_tenant():
    """Validation lookup must await the tenant-scoped run check before returning results."""
    from httpx import ASGITransport, AsyncClient

    registry = MagicMock()
    registry.get_run = AsyncMock(return_value=_make_run())
    registry.get_validation_results = AsyncMock(return_value=[])
    app = _build_app(registry, tenant_id=_TENANT_A)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/v1/harness/runs/{_RUN_ID}/validation")

    assert response.status_code == 200
    registry.get_run.assert_awaited_once_with(_RUN_ID, _TENANT_A)
    registry.get_validation_results.assert_awaited_once_with(_RUN_ID, _TENANT_A)


@pytest.mark.asyncio
async def test_decide_gate_uses_auth_context_for_decision_by():
    """decision_by must come from ctx.user_id, not the request body."""
    from httpx import ASGITransport, AsyncClient

    from layer4_agents.harness.models import GateStatus
    decided_gate = _make_gate(status=GateStatus.APPROVED, decision_by=_USER_ID)
    decided_gate = decided_gate.model_copy(update={"decided_at": _NOW, "decision_reason": "Looks good"})
    registry = MagicMock()
    registry.get_gate = AsyncMock(return_value=_make_gate())
    registry.decide_gate = AsyncMock(return_value=decided_gate)
    app = _build_app(registry, user_id=_USER_ID)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/harness/gates/{_GATE_ID}/decide",
            json={"decision": "approved", "decision_reason": "Looks good"},
        )
    assert response.status_code == 200
    assert response.json()["decision_by"] == _USER_ID
    assert registry.decide_gate.call_args.kwargs["decision_by"] == _USER_ID


@pytest.mark.asyncio
async def test_decide_gate_decision_by_falls_back_to_tenant_id():
    """When ctx.user_id is None, decision_by falls back to ctx.tenant_id."""
    from httpx import ASGITransport, AsyncClient

    from layer4_agents.harness.models import GateStatus
    decided_gate = _make_gate(status=GateStatus.APPROVED, decision_by=_TENANT_A)
    decided_gate = decided_gate.model_copy(update={"decided_at": _NOW})
    registry = MagicMock()
    registry.get_gate = AsyncMock(return_value=_make_gate())
    registry.decide_gate = AsyncMock(return_value=decided_gate)
    app = _build_app(registry, user_id=None, tenant_id=_TENANT_A)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/v1/harness/gates/{_GATE_ID}/decide", json={"decision": "approved"})
    assert response.status_code == 200
    assert registry.decide_gate.call_args.kwargs["decision_by"] == _TENANT_A


@pytest.mark.asyncio
async def test_decide_gate_calls_registry_with_correct_args():
    """Route calls registry.decide_gate with gate_id, tenant_id, and decision_reason."""
    from httpx import ASGITransport, AsyncClient

    from layer4_agents.harness.models import GateStatus
    decided_gate = _make_gate(status=GateStatus.APPROVED, decision_by=_USER_ID)
    decided_gate = decided_gate.model_copy(update={"decided_at": _NOW})
    registry = MagicMock()
    registry.get_gate = AsyncMock(return_value=_make_gate())
    registry.decide_gate = AsyncMock(return_value=decided_gate)
    app = _build_app(registry)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/harness/gates/{_GATE_ID}/decide",
            json={"decision": "approved", "decision_reason": "Verified"},
        )
    assert response.status_code == 200
    registry.decide_gate.assert_awaited_once()
    kw = registry.decide_gate.call_args.kwargs
    assert kw["gate_id"] == _GATE_ID
    assert kw["tenant_id"] == _TENANT_A
    assert kw["decision_reason"] == "Verified"


@pytest.mark.asyncio
async def test_decide_gate_accepts_rejected_decision():
    """POST decide with 'rejected' must return 200 with status=rejected."""
    from httpx import ASGITransport, AsyncClient

    from layer4_agents.harness.models import GateStatus
    decided_gate = _make_gate(status=GateStatus.REJECTED, decision_by=_USER_ID)
    decided_gate = decided_gate.model_copy(update={"decided_at": _NOW, "decision_reason": "Insufficient evidence"})
    registry = MagicMock()
    registry.get_gate = AsyncMock(return_value=_make_gate())
    registry.decide_gate = AsyncMock(return_value=decided_gate)
    app = _build_app(registry)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/harness/gates/{_GATE_ID}/decide",
            json={"decision": "rejected", "decision_reason": "Insufficient evidence"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_decide_gate_rejects_unknown_decision_value():
    """An unknown decision value must be rejected by Pydantic (422)."""
    from httpx import ASGITransport, AsyncClient
    registry = MagicMock()
    registry.get_gate = AsyncMock(return_value=_make_gate())
    app = _build_app(registry)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/harness/gates/{_GATE_ID}/decide",
            json={"decision": "unknown_value"},
        )
    assert response.status_code == 422
