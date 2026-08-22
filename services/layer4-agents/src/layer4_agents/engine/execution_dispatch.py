from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..models.run_envelope import RunEnvelope
from ..workflows import create_workflow
from .types import ScheduledTask


def initialize_workflow_run_context(
    *,
    workflow_type: str,
    input_data: dict[str, Any],
    tool_registry: Any,
    checkpoint_saver: Any,
    workflow_id: str | None,
    tenant_id: str | None,
    user_id: str | None,
    priority_value: int,
    approval_evidence: Any,
    resolved_timeout_seconds: int,
    timeout_source: str,
) -> tuple[str, str, str, Any, Any, dict[str, Any]]:
    """Initialize workflow run identity, state, envelope, and metadata dictionary."""
    wf_id = workflow_id or str(uuid4())
    run_id = str(uuid4())
    trace_id = str(uuid4())

    workflow = create_workflow(workflow_type, tool_registry, checkpoint_saver)
    initial_state = workflow.create_initial_state(
        input_data,
        tenant_id=tenant_id,
        run_id=run_id,
        trace_id=trace_id,
        workflow_id=wf_id,
    )

    envelope = RunEnvelope(
        run_id=run_id,
        workflow_id=wf_id,
        trace_id=trace_id,
        tenant_id=str(tenant_id) if tenant_id else "",
        workflow_type=workflow_type,
    )

    initial_state.run_envelope = envelope
    if approval_evidence is not None:
        initial_state.metadata["approval_decision"] = approval_evidence
    initial_state.metadata["workflow_timeout_seconds"] = resolved_timeout_seconds
    initial_state.metadata["workflow_timeout_source"] = timeout_source

    envelope_data = envelope.model_dump()
    if approval_evidence:
        envelope_data["approval_decision"] = approval_evidence

    metadata: dict[str, Any] = {
        "workflow_type": workflow_type,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "priority": priority_value,
        "started_at": datetime.now(UTC).isoformat(),
        "timeout_seconds": resolved_timeout_seconds,
        "timeout_resolution": {
            "tenant_id": tenant_id,
            "selected_timeout_seconds": resolved_timeout_seconds,
            "source": timeout_source,
        },
        "run_envelope": envelope_data,
        "approval_decision": approval_evidence,
    }

    return wf_id, run_id, trace_id, workflow, initial_state, metadata


def build_workflow_task(*, priority: int, workflow_id: str, tenant_id: str | None, user_id: str | None, workflow_type: str, workflow: Any, initial_state: Any, checkpoint_interval: int, handler: Any) -> ScheduledTask:
    return ScheduledTask(
        priority=priority,
        scheduled_time=datetime.now(UTC),
        task_id=f"wf-{workflow_id}",
        workflow_instance_id=workflow_id,
        capability="workflow_execution",
        agent_type="OrchestrationController",
        context={"tenant_id": tenant_id, "user_id": user_id, "workflow_type": workflow_type},
        parameters={
            "workflow": workflow,
            "initial_state": initial_state,
            "workflow_id": workflow_id,
            "checkpoint_interval": checkpoint_interval,
            "handler": handler,
        },
        tenant_id=tenant_id,
        tenant_context={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "workflow_type": workflow_type,
            "auth_source": "workflow_execution",
        },
    )

