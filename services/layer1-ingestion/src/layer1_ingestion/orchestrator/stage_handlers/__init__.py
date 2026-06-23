"""Stage handlers for the source ingestion pipeline.

Each handler implements a single pipeline stage. Handlers are idempotent: they
verify the run's current state and step before doing work.
"""

from __future__ import annotations

from layer1_ingestion.shared.models import IngestionRunStatus

from .applying_policy import ApplyingPolicyHandler
from .base import StageHandler

# Import concrete handlers here as they are implemented.
from .fetching_source import FetchingSourceHandler
from .noop import NoopStageHandler
from .validating_access import ValidatingAccessHandler

_STAGE_HANDLER_REGISTRY: dict[str, type[StageHandler]] = {
    IngestionRunStatus.VALIDATING_ACCESS.value: ValidatingAccessHandler,
    IngestionRunStatus.RESOLVING_CONNECTOR.value: NoopStageHandler,
    IngestionRunStatus.FETCHING_SOURCE.value: FetchingSourceHandler,
    IngestionRunStatus.APPLYING_POLICY.value: ApplyingPolicyHandler,
    IngestionRunStatus.NORMALIZING.value: NoopStageHandler,
    IngestionRunStatus.CHUNKING.value: NoopStageHandler,
    IngestionRunStatus.EXTRACTING.value: NoopStageHandler,
    IngestionRunStatus.BUILDING_CLAIMS.value: NoopStageHandler,
    IngestionRunStatus.VALIDATING_CLAIMS.value: NoopStageHandler,
    IngestionRunStatus.PROJECTING_SUMMARY.value: NoopStageHandler,
    IngestionRunStatus.NEEDS_USER_ACTION.value: NoopStageHandler,
    IngestionRunStatus.FAILED_RETRYABLE.value: NoopStageHandler,
}


def get_stage_handler(stage_name: str) -> StageHandler:
    """Return a handler instance for ``stage_name``."""
    handler_cls = _STAGE_HANDLER_REGISTRY.get(stage_name)
    if handler_cls is None:
        raise ValueError(f"No stage handler registered for {stage_name!r}")
    return handler_cls()


def register_stage_handler(stage_name: str, handler_cls: type[StageHandler]) -> None:
    """Register or override a stage handler (useful for tests)."""
    _STAGE_HANDLER_REGISTRY[stage_name] = handler_cls


__all__ = [
    "StageHandler",
    "NoopStageHandler",
    "ValidatingAccessHandler",
    "FetchingSourceHandler",
    "ApplyingPolicyHandler",
    "get_stage_handler",
    "register_stage_handler",
]
