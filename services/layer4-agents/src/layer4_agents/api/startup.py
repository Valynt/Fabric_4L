from __future__ import annotations

"""Startup lifecycle management and dependency checks for Layer 4 API."""


import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, cast

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from value_fabric.shared.identity.feature_flags import (
    init_feature_flags,
    register_feature_flag_lookup,
)
from value_fabric.shared.identity.vault_check import is_vault_healthy
from value_fabric.shared.redis_ha import create_async_redis_client

from ..config import configure_settings
from ..config.checkpoint import CheckpointConfig, get_checkpoint_saver
from ..database import (
    close_db,
    db_session_for_context,
    get_session_factory,
    init_db,
    set_tenant_context,
)
from ..engine.executor import OrchestrationController
from ..engine.state_manager import StateManager
from ..feature_flags.service import FeatureFlagService
from ..resilience import TenantRateLimiter
from ..services.crm_sync_job_runner import CRMSyncJobRunner
from ..services.crm_sync_scheduler import get_crm_sync_scheduler
from ..services.health_tracker import get_health_tracker
from ..services.value_flow_facade import ValueFlowFacadeService
from ..tools import create_default_registry
from .runtime_state import RuntimeState as RuntimeState
from .runtime_state import runtime_state
from .websocket import get_ws_manager

logger = logging.getLogger(__name__)


@dataclass
class StartupCheckResult:
    name: str
    ok: bool
    detail: str | None = None


async def check_database_ready() -> StartupCheckResult:
    try:
        await init_db()
        return StartupCheckResult(name="database", ok=True)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("database_startup_check_failed", extra={"error_type": type(exc).__name__, "error_code": "DB_CONN_FAILED"})
        return StartupCheckResult(name="database", ok=False, detail="Database connection failed")


async def check_redis_ready(redis_client: Any) -> StartupCheckResult:
    if redis_client is None:
        return StartupCheckResult(name="redis", ok=False, detail="Redis client not configured")
    try:
        await redis_client.ping()
        return StartupCheckResult(name="redis", ok=True)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("redis_startup_check_failed", extra={"error_type": type(exc).__name__, "error_code": "REDIS_CONN_FAILED"})
        return StartupCheckResult(name="redis", ok=False, detail="Redis connection failed")


async def check_vault_ready(*, environment: str, vault_addr: str | None) -> StartupCheckResult:
    if environment != "production" or not vault_addr:
        return StartupCheckResult(name="vault", ok=True, detail="check skipped")
    ok = await is_vault_healthy(vault_addr)
    return StartupCheckResult(name="vault", ok=ok, detail=None if ok else "Vault unreachable")


def build_lifespan(
    *,
    validate_production_safety: Callable[[], None],
    init_telemetry: Callable[[], Any],
    configure_optional_integrations: Callable[[FastAPI], Awaitable[None]],
) -> Callable[[FastAPI], Any]:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        validate_production_safety()
        configure_settings()
        app.state.tracer_provider = init_telemetry()
        ws_manager = get_ws_manager()
        health_tracker = get_health_tracker()

        db_status = await check_database_ready()
        if not db_status.ok:
            raise RuntimeError(f"Database initialization failed - cannot start without persistence: {db_status.detail}")

        vault_status = await check_vault_ready(
            environment=os.getenv("ENVIRONMENT", "development"),
            vault_addr=os.getenv("VAULT_ADDR"),
        )
        if not vault_status.ok:
            raise RuntimeError("Vault unreachable - cannot start in production without secrets backend")

        redis_url = os.getenv("REDIS_URL")
        startup_redis_client = create_async_redis_client(redis_url, decode_responses=True) if redis_url else None
        runtime_state.state_manager = StateManager(startup_redis_client)

        # The tool registry must share the production Redis client so that
        # idempotent tool results survive pod restarts.
        tool_config = {
            "neo4j_uri": os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
            "neo4j_password": os.getenv("NEO4J_PASSWORD"),
            "database": os.getenv("NEO4J_DATABASE", "valuefabric"),
        }
        tool_registry = create_default_registry(config=tool_config, redis_client=startup_redis_client)

        # Graph-backed routes (value hypotheses, narratives, agent context)
        # read request.app.state.neo4j_driver; provision it from the same
        # NEO4J_* env used by the tool registry. Without this, those routes
        # fail at runtime with a None driver.
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if neo4j_uri and neo4j_password:
            from neo4j import AsyncGraphDatabase

            app.state.neo4j_driver = AsyncGraphDatabase.driver(
                neo4j_uri,
                auth=(os.getenv("NEO4J_USER", "neo4j"), neo4j_password),
            )
            logger.info("L4: Neo4j driver initialized for graph-backed routes")
        else:
            app.state.neo4j_driver = None
            logger.warning("L4: NEO4J_URI/NEO4J_PASSWORD unset; graph-backed routes will fail closed")

        redis_status = await check_redis_ready(getattr(runtime_state.state_manager, "redis_client", None))
        if not redis_status.ok:
            raise RuntimeError(f"Redis connectivity failed - cannot start without cache: {redis_status.detail}")

        init_feature_flags(runtime_state.state_manager.redis_client)
        app.state.value_flow_facade = ValueFlowFacadeService(runtime_state.state_manager.redis_client)
        app.state.rate_limiter = TenantRateLimiter()

        async def _feature_flag_lookup(flag_key: str, tenant_id):
            from value_fabric.shared.identity.context import RequestContext

            if tenant_id is None:
                return None
            context = RequestContext(tenant_id=tenant_id)
            async with db_session_for_context(context) as db:
                return await FeatureFlagService.lookup_flag(db, flag_key, tenant_id)

        register_feature_flag_lookup(_feature_flag_lookup)
        runtime_state.state_manager.set_ws_manager(ws_manager)

        try:
            runtime_state.checkpoint_saver = await get_checkpoint_saver()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Checkpoint saver failed - cannot start without workflow resumption: {exc}") from exc

        runtime_state.workflow_executor = OrchestrationController(
            tool_registry, runtime_state.state_manager, checkpoint_saver=runtime_state.checkpoint_saver
        )
        await runtime_state.workflow_executor.start()
        await runtime_state.workflow_executor.recover_workflows()

        # The canonical runtime is additive: legacy orchestration remains
        # booted for existing routes while new consumers use the provider-
        # agnostic runtime ports and tenant-scoped HTTP surface.
        # Import dynamically because database.py registers runtime ORM models
        # at module load; a top-level runtime import would create a database
        # <-> runtime.orm import cycle during application bootstrap.
        import importlib

        runtime_module = importlib.import_module("layer4_agents.runtime")
        # The shared session factory yields tenant-enforced sessions (a
        # TenantEnforcedAsyncSession subclass of AsyncSession) that fail closed
        # without per-session tenant context, so the Postgres CheckpointPort is
        # wired with the set_tenant_context hook (marks the session + sets the
        # RLS app.tenant_id variable). Without this checkpoint port, every
        # production resume would fail RESUME_UNAVAILABLE.
        runtime_sessions = cast(async_sessionmaker[AsyncSession], get_session_factory())
        runtime_state.runtime_metrics = runtime_module.RuntimeMetrics()
        runtime_events = runtime_module.RuntimeEventBus()
        runtime_events.register(runtime_state.runtime_metrics)
        runtime_state.agent_runtime = runtime_module.AgentRuntimeImpl(
            workflow_engine=runtime_module.LangGraphWorkflowEngineAdapter(
                tool_registry=tool_registry,
                checkpoint_saver=runtime_state.checkpoint_saver,
                checkpoint_port=runtime_module.PostgresCheckpointAdapter(
                    runtime_sessions,
                    tenant_context_setter=set_tenant_context,
                ),
            ),
            tool_registry=runtime_module.LegacyToolRegistryAdapter(tool_registry),
            event_bus=runtime_events,
        )
        await runtime_state.agent_runtime.start()
        app.state.agent_runtime = runtime_state.agent_runtime
        app.state.runtime_metrics = runtime_state.runtime_metrics

        # Schedule periodic stuck-workflow detection (OBS-L4-006)
        async def _stuck_workflow_detector() -> None:
            while True:
                try:
                    await asyncio.sleep(60)
                    if runtime_state.workflow_executor is not None:
                        await runtime_state.workflow_executor.detect_and_record_stuck_workflows(
                            threshold_seconds=600
                        )
                except asyncio.CancelledError:
                    break
                except Exception:
                    logger.exception("Stuck workflow detector failed")

        runtime_state.stuck_workflow_task = asyncio.create_task(_stuck_workflow_detector())

        await ws_manager.start()
        await health_tracker.start()
        await configure_optional_integrations(app)

        yield

        if runtime_state.workflow_executor:
            await runtime_state.workflow_executor.stop()
        if runtime_state.agent_runtime:
            await runtime_state.agent_runtime.stop()
        await ws_manager.stop()
        await health_tracker.stop()
        if runtime_state.crm_sync_scheduler:
            await runtime_state.crm_sync_scheduler.stop()
        if runtime_state.crm_sync_job_runner:
            await runtime_state.crm_sync_job_runner.stop()
        if runtime_state.oidc_cleanup_task:
            await runtime_state.oidc_cleanup_task.stop()
        if runtime_state.gate_timeout_scheduler is not None:
            await runtime_state.gate_timeout_scheduler.stop()
        if runtime_state.stuck_workflow_task is not None:
            runtime_state.stuck_workflow_task.cancel()
            try:
                await runtime_state.stuck_workflow_task
            except asyncio.CancelledError:
                pass
        if runtime_state.checkpoint_saver:
            await CheckpointConfig.close_saver(runtime_state.checkpoint_saver)
        neo4j_driver = getattr(app.state, "neo4j_driver", None)
        if neo4j_driver is not None:
            await neo4j_driver.close()
        if runtime_state.state_manager and getattr(runtime_state.state_manager, "redis_client", None):
            redis_client = runtime_state.state_manager.redis_client
            if redis_client is not None:
                await redis_client.aclose()
        await close_db()
        if getattr(app.state, "tracer_provider", None):
            app.state.tracer_provider.shutdown()

    return lifespan


async def start_optional_integrations(app: FastAPI) -> None:
    from ..config.settings import get_settings
    from ..services.oidc_cleanup import create_oidc_cleanup_task

    if get_settings().enable_crm_scheduler:
        runtime_state.crm_sync_scheduler = await get_crm_sync_scheduler()
        await runtime_state.crm_sync_scheduler.start()
    if runtime_state.state_manager and getattr(runtime_state.state_manager, "redis_client", None):
        redis_client = runtime_state.state_manager.redis_client
        if redis_client is not None:
            runtime_state.crm_sync_job_runner = CRMSyncJobRunner(redis_client)
            await runtime_state.crm_sync_job_runner.start()

    if get_settings().enable_oidc_cleanup:
        from ..database import get_session_factory
        runtime_state.oidc_cleanup_task = await create_oidc_cleanup_task(
            db_session_factory=get_session_factory(),
            interval_seconds=300.0,
        )

    # Gate timeout scheduler — expires PENDING gates after deadline (WF-001).
    # Background tasks need a plain async-session factory (async context manager),
    # not the request-scoped get_db_from_context() dependency which is an async
    # generator and requires a RequestContext.
    from ..database import get_session_factory
    from ..harness.gate_timeout_scheduler import create_gate_timeout_scheduler
    runtime_state.gate_timeout_scheduler = create_gate_timeout_scheduler(get_session_factory())
    await runtime_state.gate_timeout_scheduler.start()
