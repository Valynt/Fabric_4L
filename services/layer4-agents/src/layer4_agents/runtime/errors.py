"""Structured errors for the Agent Runtime."""

from __future__ import annotations

from typing import Any


class AgentRuntimeError(Exception):
    """Base runtime error with structured metadata."""

    def __init__(self, message: str, *, code: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class TenantRequiredError(AgentRuntimeError):
    """Raised when a runtime operation is missing a tenant context."""

    def __init__(self, message: str = "Tenant context is required", *, details: dict[str, Any] | None = None):
        super().__init__(message, code="TENANT_REQUIRED", details=details)


class WorkflowTypeNotFoundError(AgentRuntimeError):
    """Raised when an unknown workflow type is requested."""

    def __init__(self, workflow_type: str):
        super().__init__(
            f"Unknown workflow type: {workflow_type}",
            code="WORKFLOW_TYPE_NOT_FOUND",
            details={"workflow_type": workflow_type},
        )


class ProviderNotFoundError(AgentRuntimeError):
    """Raised when a model provider is not registered."""

    def __init__(self, provider: str):
        super().__init__(
            f"Model provider not found: {provider}",
            code="PROVIDER_NOT_FOUND",
            details={"provider": provider},
        )


class ToolForbiddenError(AgentRuntimeError):
    """Raised when a tool call is not authorized."""

    def __init__(self, tool_name: str, *, reason: str | None = None):
        super().__init__(
            f"Tool call forbidden: {tool_name}",
            code="TOOL_FORBIDDEN",
            details={"tool_name": tool_name, "reason": reason or "policy denied"},
        )


class ToolRegistryUnavailableError(AgentRuntimeError):
    """Raised when a tool is invoked without a configured tool registry."""

    def __init__(self, tool_name: str):
        super().__init__(
            "Tool registry is not configured",
            code="TOOL_REGISTRY_UNAVAILABLE",
            details={"tool_name": tool_name},
        )


class CheckpointConflictError(AgentRuntimeError):
    """Raised when a resume request references a stale checkpoint hash."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message, code="CHECKPOINT_CONFLICT", details=details)


class RunNotFoundError(AgentRuntimeError):
    """Raised when a run is missing or not visible to the requesting tenant."""

    def __init__(self, run_id: str):
        super().__init__(
            f"Run not found: {run_id}",
            code="RUN_NOT_FOUND",
            details={"run_id": run_id},
        )
