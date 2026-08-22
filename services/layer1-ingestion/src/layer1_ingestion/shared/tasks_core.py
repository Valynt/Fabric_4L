"""Core Celery bootstrap and shared task machinery (facade).

This module re-exports core names from ``layer1_ingestion.shared.tasks``,
which remains the single source of truth. It provides a cohesive import
surface for the Celery app, the DLQ signal handler, job-failure helpers, and
generic pipeline orchestration without moving any implementation.

Important: these bindings are snapshots of the canonical module. Persistent
patches and mock targets must continue to address
``layer1_ingestion.shared.tasks.<name>`` exactly as before.
"""

from .tasks import (
    MAX_DISPATCH_ATTEMPTS,
    TenantKillSwitchUnavailable,
    _check_tenant_kill_switch_sync,
    _fail_job,
    _update_stage,
    celery_app,
    execute_pipeline_stage,
    record_dead_lettered_task,
    route_exhausted_task_to_dlq,
)

__all__ = [
    "MAX_DISPATCH_ATTEMPTS",
    "TenantKillSwitchUnavailable",
    "_check_tenant_kill_switch_sync",
    "_fail_job",
    "_update_stage",
    "celery_app",
    "execute_pipeline_stage",
    "record_dead_lettered_task",
    "route_exhausted_task_to_dlq",
]
