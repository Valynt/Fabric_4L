from __future__ import annotations

"""Layer 4 observability schema and lifecycle logger helpers."""


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
