"""Shared Pydantic contracts for the Agent Runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RunStatus(str, Enum):
    """Canonical runtime run statuses."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class RuntimeContext(BaseModel):
    """Execution context propagated through every runtime port."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    user_id: str | None = None
    trace_id: str
    run_id: str
    workflow_id: str
    workflow_type: str
    priority: int = Field(default=3, ge=1, le=5)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunRequest(BaseModel):
    """Request to submit a new workflow run."""

    model_config = ConfigDict(extra="forbid")

    workflow_type: str = Field(..., min_length=1)
    input_data: dict[str, Any] = Field(default_factory=dict)
    workflow_id: str | None = None
    priority: int = Field(default=3, ge=1, le=5)
    timeout_seconds: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunEnvelope(BaseModel):
    """Stable identity envelope for a run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow_id: str
    trace_id: str
    tenant_id: str
    workflow_type: str
    status: RunStatus = RunStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    completed_at: str | None = None


class RunResult(BaseModel):
    """Result/status of a workflow run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow_id: str
    trace_id: str
    tenant_id: str
    workflow_type: str
    status: RunStatus
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None


class RunSummary(BaseModel):
    """Lightweight run listing entry."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow_id: str
    workflow_type: str
    status: RunStatus
    created_at: str


class ResumeRequest(BaseModel):
    """Request to resume a paused/interrupted run."""

    model_config = ConfigDict(extra="forbid")

    resume_data: dict[str, Any] = Field(default_factory=dict)
    checkpoint_id: str | None = None
    checkpoint_hash: str | None = None


class ToolSchema(BaseModel):
    """Public schema for a registered tool."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    category: str
    tenant_scoped: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    version: str = "1.0.0"


class ToolDef(BaseModel):
    """Definition used to register a tool."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: str = "utility"
    tenant_scoped: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    handler: Any = Field(..., exclude=True)


class ToolCall(BaseModel):
    """Canonical tool invocation payload."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    run_id: str | None = None


class ToolResult(BaseModel):
    """Canonical tool execution result."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "error"]
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class Checkpoint(BaseModel):
    """Portable checkpoint metadata."""

    model_config = ConfigDict(extra="forbid")

    checkpoint_id: str
    run_id: str
    thread_id: str
    tenant_id: str
    state_hash: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] | None = None


class WorkflowResult(BaseModel):
    """Result returned by a WorkflowEnginePort adapter."""

    model_config = ConfigDict(extra="forbid")

    status: RunStatus
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    checkpoint: Checkpoint | None = None


class ModelConfig(BaseModel):
    """Provider-agnostic model request configuration."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    extra: dict[str, Any] | None = None


class Message(BaseModel):
    """Provider-agnostic chat message."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class ModelResponse(BaseModel):
    """Provider-agnostic model response."""

    model_config = ConfigDict(extra="forbid")

    content: str | None = None
    finish_reason: str | None = None
    usage: dict[str, int] | None = None
    raw_response: dict[str, Any] | None = None


class AuthzDecision(BaseModel):
    """Authorization decision for a runtime action."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason: str | None = None
