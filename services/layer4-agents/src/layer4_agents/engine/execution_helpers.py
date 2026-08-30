from __future__ import annotations

"""Pure, stateless execution helpers for the orchestration executor.

Extracted from ``executor.OrchestrationController`` so the controller keeps
only orchestration state and delegation. These helpers carry no controller
state; the controller methods delegate to them so invocations and mocking
patterns that target the instance methods continue to work unchanged.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from ..models.agent_state import AgentState, WorkflowStatus
from ..observability import Layer4EventContext

logger = logging.getLogger(__name__)

TENANT_WORKFLOW_TIMEOUT_SETTINGS_PATHS: tuple[tuple[str, ...], ...] = (
    ("layer4", "workflow", "timeout_seconds"),
    ("layer4", "workflow_timeout_seconds"),
    ("workflow", "timeout_seconds"),
    ("workflow_timeout_seconds",),
)


def fmt_enum(value: Any) -> str:
    """Serialize an enum-like value consistently."""
    return value.value if hasattr(value, "value") else str(value)


def fmt_dt(dt: datetime | None) -> str | None:
    """Serialize a datetime to ISO format."""
    return dt.isoformat() if dt else None


def build_lifecycle_context(
    workflow_metadata: dict[str, dict[str, Any]],
    workflow_id: str,
    *,
    tenant_id: str | None = None,
    checkpoint_id: str | None = None,
) -> Layer4EventContext:
    """Build a Layer4EventContext for lifecycle logging.

    Falls back to workflow metadata when no explicit tenant_id is provided.
    Uses distinct run_id and trace_id from the canonical run envelope when available.
    """
    meta = workflow_metadata.get(workflow_id, {})
    envelope_data = meta.get("run_envelope", {})

    kwargs: dict[str, Any] = {
        "request_id": workflow_id,
        "trace_id": envelope_data.get("trace_id") or workflow_id,
        "tenant_id": tenant_id or str(meta.get("tenant_id") or "unknown"),
        "workflow_id": workflow_id,
        "run_id": envelope_data.get("run_id") or workflow_id,
        "provider_name": "langgraph",
    }
    if checkpoint_id is not None:
        kwargs["checkpoint_id"] = checkpoint_id
    return Layer4EventContext(**kwargs)


def extract_tenant_timeout(tenant_settings: dict[str, Any] | None) -> int | None:
    """Resolve a tenant-scoped workflow timeout override, if configured.

    Walks ``TENANT_WORKFLOW_TIMEOUT_SETTINGS_PATHS`` and returns the first
    integral timeout found, or ``None`` when absent/malformed.
    """
    if not tenant_settings:
        return None
    cursor: Any
    for path in TENANT_WORKFLOW_TIMEOUT_SETTINGS_PATHS:
        cursor = tenant_settings
        for key in path:
            if not isinstance(cursor, dict) or key not in cursor:
                cursor = None
                break
            cursor = cursor[key]
        if isinstance(cursor, int):
            return cursor
    return None


async def resolve_workflow_timeout_seconds(tenant_id: str | None) -> tuple[int, str]:
    """Resolve the effective workflow timeout and its provenance source.

    Returns a ``(seconds, source)`` pair where source is one of
    ``service_default``, ``tenant_settings``, or ``safe_fallback``.
    """
    from ..config.settings import get_settings

    source = "service_default"
    selected = get_settings().workflow_timeout_seconds

    if tenant_id:
        try:
            from value_fabric.shared.identity.context import RequestContext

            from ..database import db_session_for_context
            from ..tenants.service import get_tenant_settings

            tenant_uuid = UUID(str(tenant_id))
            async with db_session_for_context(RequestContext(tenant_id=tenant_uuid)) as db:
                tenant_settings = await get_tenant_settings(db, tenant_uuid)
            tenant_timeout = extract_tenant_timeout(tenant_settings)
            if tenant_timeout is not None:
                selected = tenant_timeout
                source = "tenant_settings"
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.debug(
                "Tenant timeout override resolution failed for tenant_id=%s",
                tenant_id,
                exc_info=True,
            )

    min_timeout = get_settings().workflow_timeout_min_seconds
    max_timeout = get_settings().workflow_timeout_max_seconds
    if not isinstance(selected, int) or selected < min_timeout or selected > max_timeout:
        source = "safe_fallback"
        selected = get_settings().workflow_timeout_fallback_seconds

    if selected < min_timeout:
        selected = min_timeout
    if selected > max_timeout:
        selected = max_timeout
    return selected, source


async def wait_for_workflow(state_manager: Any, workflow_id: str) -> AgentState:
    """Wait for workflow completion (legacy, no timeout).

    Args:
        state_manager: State manager used to poll workflow state.
        workflow_id: Workflow to wait for.

    Returns:
        Final workflow state.
    """
    while True:
        state = await state_manager.load_state(workflow_id)

        if state and state.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.INTERRUPTED,
        ]:
            return state

        await asyncio.sleep(0.5)


def calculate_progress(state: AgentState) -> int:
    """Calculate workflow progress percentage.

    Args:
        state: Current workflow state.

    Returns:
        Progress percentage (0-100).
    """
    status_progress = {
        WorkflowStatus.PENDING: 0,
        WorkflowStatus.RUNNING: 50,
        WorkflowStatus.PAUSED: 50,
        WorkflowStatus.INTERRUPTED: 25,
        WorkflowStatus.COMPLETED: 100,
        WorkflowStatus.FAILED: 100,
        WorkflowStatus.CANCELLED: 100,
    }

    return status_progress.get(state.status, 0)
