from __future__ import annotations

"""Shared runtime state holder for the Layer 4 API.

This module is intentionally a leaf in the import graph: it must not import
any other ``layer4_agents.api`` module at runtime. ``api.startup`` populates
the state during the application lifespan, while route and WebSocket modules
read from it. Keeping the holder here (instead of in ``api.startup``) breaks
the import cycle::

    websocket/routes.py -> routes/workflows.py -> startup.py
        -> websocket/__init__.py -> websocket/routes.py
"""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from ..engine.executor import OrchestrationController
    from ..engine.state_manager import StateManager
    from ..harness.gate_timeout_scheduler import GateTimeoutScheduler
    from ..runtime.core import AgentRuntimeImpl
    from ..runtime.observability import RuntimeMetrics
    from ..services.crm_sync_job_runner import CRMSyncJobRunner
    from ..services.crm_sync_scheduler import CRMSyncScheduler
    from ..services.oidc_cleanup import OIDCCleanupTask


class RuntimeState:
    workflow_executor: OrchestrationController | None = None
    agent_runtime: AgentRuntimeImpl | None = None
    runtime_metrics: RuntimeMetrics | None = None
    state_manager: StateManager | None = None
    checkpoint_saver: AsyncPostgresSaver | None = None
    crm_sync_scheduler: CRMSyncScheduler | None = None
    crm_sync_job_runner: CRMSyncJobRunner | None = None
    oidc_cleanup_task: OIDCCleanupTask | None = None
    gate_timeout_scheduler: GateTimeoutScheduler | None = None
    stuck_workflow_task: asyncio.Task | None = None


runtime_state = RuntimeState()
