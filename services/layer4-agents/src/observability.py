"""Layer 4 observability schema and lifecycle logger helpers."""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger
from typing import Any


@dataclass(frozen=True)
class Layer4EventContext:
    request_id: str
    trace_id: str
    tenant_id: str
    workflow_id: str
    run_id: str
    provider_name: str
    checkpoint_id: str | None = None


class Layer4LifecycleLogger:
    """Enforces required structured fields for run lifecycle/tool events."""

    def __init__(self, logger: Logger) -> None:
        self._logger = logger

    def emit(
        self,
        *,
        stage: str,
        context: Layer4EventContext,
        error_class: str | None = None,
        error_code: str | None = None,
        **fields: Any,
    ) -> None:
        payload = {
            "event_stage": stage,
            "request_id": context.request_id,
            "trace_id": context.trace_id,
            "tenant_id": context.tenant_id,
            "workflow_id": context.workflow_id,
            "run_id": context.run_id,
            "provider_name": context.provider_name,
            "checkpoint_id": context.checkpoint_id,
            "error_class": error_class,
            "error_code": error_code,
            **fields,
        }
        self._logger.info("layer4.lifecycle.%s", stage, extra=payload)


@dataclass(frozen=True)
class Layer4LogContext:
    """Required structured context for layer4 workflow/tool lifecycle logs."""

    workflow_id: str
    run_id: str
    tenant_id: str
    request_id: str
    account_id: str | None = None
    tool: str | None = None
    checkpoint_id: str | None = None


class Layer4LogContractLogger:
    """Centralized wrapper enforcing layer4 logging contract fields."""

    def __init__(self, logger: Logger) -> None:
        self._logger = logger

    def emit(
        self,
        *,
        event: str,
        context: Layer4LogContext,
        level: str = "info",
        **fields: Any,
    ) -> None:
        payload = {
            "workflow_id": context.workflow_id,
            "run_id": context.run_id,
            "tenant_id": context.tenant_id,
            "request_id": context.request_id,
            "account_id": context.account_id,
            "tool": context.tool,
            "checkpoint_id": context.checkpoint_id,
            **fields,
        }
        log_fn = getattr(self._logger, level, self._logger.info)
        log_fn("layer4.log.%s", event, extra=payload)
