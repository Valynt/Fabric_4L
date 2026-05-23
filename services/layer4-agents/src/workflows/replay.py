"""Replay harness for Layer 4 workflow state reconstruction.

This module defines an immutable event envelope contract and a non-production
replay harness that can rebuild workflow state from an ordered event stream.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ..models.agent_state import BaseAgentState, WorkflowStatus, WorkflowType


class ReplayEventEnvelopeV1(BaseModel):
    """Immutable replay event envelope used for deterministic reconstruction."""

    event_id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    timestamp: datetime
    correlation_id: str = Field(..., min_length=1)
    schema_version: str = Field(default="1.0")
    domain: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    payload_pointer: str = Field(..., min_length=1)
    payload_checksum: str = Field(..., min_length=1)
    payload_redacted: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")


class ReplayAuthorizationContext(BaseModel):
    """AuthN/AuthZ context required to run a replay job."""

    tenant_id: str
    actor: str
    roles: tuple[str, ...] = ()
    environment: str = "non-production"
    ticket_id: str | None = None


class ReplayAuditSink(Protocol):
    """Sink for replay audit trails."""

    def record(self, action: str, details: dict[str, Any]) -> None:
        """Record an auditable replay activity entry."""


class ReplayEventStream(Protocol):
    """Repository boundary for replay event retrieval."""

    def list_events(
        self, *, tenant_id: str, workflow_id: str, domain: str = "layer4.workflow_state"
    ) -> list[ReplayEventEnvelopeV1]:
        """Return immutable replay events for the requested tenant/workflow/domain."""


@dataclass(frozen=True)
class ReplayResult:
    state: BaseAgentState
    applied_event_ids: list[str]


class Layer4WorkflowReplayHarness:
    """Rebuild Layer 4 workflow state from immutable event envelopes.

    SECURITY: Harness is intentionally restricted to non-production environments.
    """

    ALLOWED_ENVIRONMENTS = {"local", "dev", "test", "staging", "non-production"}
    REQUIRED_ROLE = "replay:execute"

    def __init__(self, audit_sink: ReplayAuditSink) -> None:
        self._audit_sink = audit_sink

    def replay(
        self,
        *,
        workflow_id: str,
        workflow_type: WorkflowType,
        events: list[ReplayEventEnvelopeV1],
        authz: ReplayAuthorizationContext,
    ) -> ReplayResult:
        self._authorize(authz=authz)

        ordered_events = sorted(events, key=lambda e: (e.timestamp, e.event_id))
        state = BaseAgentState(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            tenant_id=getattr(authz, "tenant_id", "replay-tenant"),
        )
        applied: list[str] = []

        for event in ordered_events:
            self._validate_tenant(event=event, authz=authz)
            self._apply_event(state=state, event=event)
            applied.append(event.event_id)

        self._audit_sink.record(
            "layer4.workflow.replay.executed",
            {
                "tenant_id": authz.tenant_id,
                "actor": authz.actor,
                "workflow_id": workflow_id,
                "workflow_type": workflow_type.value,
                "event_count": len(applied),
                "event_ids": applied,
                "ticket_id": authz.ticket_id,
            },
        )
        return ReplayResult(state=state, applied_event_ids=applied)

    def replay_from_stream(
        self,
        *,
        workflow_id: str,
        workflow_type: WorkflowType,
        stream: ReplayEventStream,
        authz: ReplayAuthorizationContext,
        domain: str = "layer4.workflow_state",
    ) -> ReplayResult:
        """Rebuild state from the service-boundary event stream interface."""
        events = stream.list_events(tenant_id=authz.tenant_id, workflow_id=workflow_id, domain=domain)
        return self.replay(workflow_id=workflow_id, workflow_type=workflow_type, events=events, authz=authz)

    def _authorize(self, *, authz: ReplayAuthorizationContext) -> None:
        if authz.environment not in self.ALLOWED_ENVIRONMENTS:
            raise PermissionError("Replay is restricted to non-production environments")
        if self.REQUIRED_ROLE not in set(authz.roles):
            raise PermissionError("Missing replay role: replay:execute")

    @staticmethod
    def _validate_tenant(*, event: ReplayEventEnvelopeV1, authz: ReplayAuthorizationContext) -> None:
        if event.tenant_id != authz.tenant_id:
            raise PermissionError("Cross-tenant replay is forbidden")

    @staticmethod
    def _apply_event(*, state: BaseAgentState, event: ReplayEventEnvelopeV1) -> None:
        if event.domain != "layer4.workflow_state":
            return

        if event.event_type == "workflow.created":
            state.status = WorkflowStatus.PENDING
            state.started_at = event.timestamp
        elif event.event_type == "workflow.started":
            state.status = WorkflowStatus.RUNNING
            state.started_at = event.timestamp
        elif event.event_type == "workflow.node_transition":
            node_name = str(event.payload_redacted.get("current_node") or "")
            state.current_node = node_name or state.current_node
        elif event.event_type == "workflow.paused":
            state.status = WorkflowStatus.PAUSED
            state.paused_at = event.timestamp
            state.pause_count = state.pause_count + 1
        elif event.event_type == "workflow.resumed":
            state.status = WorkflowStatus.RUNNING
            state.resumed_at = event.timestamp
        elif event.event_type == "workflow.failed":
            state.status = WorkflowStatus.FAILED
            state.completed_at = event.timestamp
            reason = event.payload_redacted.get("error")
            if reason:
                state.errors.append(str(reason))
        elif event.event_type == "workflow.completed":
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = event.timestamp
            if event.payload_redacted:
                state.output_data = {**(state.output_data or {}), **event.payload_redacted}
