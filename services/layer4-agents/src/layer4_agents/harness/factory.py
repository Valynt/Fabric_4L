from __future__ import annotations

"""Factory functions for constructing harness registry instances.

This is the single decision point for choosing between in-memory (tests)
and SQL-backed (production) store implementations.

Usage:

    # Tests — no DB required
    registry = make_in_memory_registry()

    # Production — requires an AsyncSession with tenant context set
    registry = await make_sql_registry(session)

    # Production with live L5 validation
    registry = await make_live_l5_registry(session, tenant_id="...")
"""


import os

from .checkpoints import CheckpointManager
from .human_gates import HumanGateManager
from .registry import HarnessRegistry
from .state_machine import StateMachine
from .telemetry import TelemetryEmitter
from .tool_contracts import ToolContractRegistry
from .validation_hooks import ClaimValidator, ValidationHook


def make_in_memory_registry(
    primary_validator: ClaimValidator | None = None,
    fallback_validator: ClaimValidator | None = None,
) -> HarnessRegistry:
    """Return a HarnessRegistry backed by in-memory stores.

    Suitable for tests and local development without a database.
    All state is lost on process exit.
    """
    return HarnessRegistry(
        state_machine=StateMachine(),
        tool_registry=ToolContractRegistry(),
        gate_manager=HumanGateManager(),
        checkpoint_manager=CheckpointManager(),
        telemetry=TelemetryEmitter(),
        validation_hook=ValidationHook(
            primary_validator=primary_validator,
            fallback_validator=fallback_validator,
        ),
    )


async def make_sql_registry(
    session,  # AsyncSession — typed loosely to avoid hard import at module level
    primary_validator: ClaimValidator | None = None,
    fallback_validator: ClaimValidator | None = None,
) -> SqlHarnessRegistry:  # noqa: F821
    """Return a SqlHarnessRegistry backed by PostgreSQL stores.

    Requires an AsyncSession with tenant context already set via
    SET LOCAL app.tenant_id (handled by get_db_from_context or
    db_session_for_context).

    All five stores (runs, gates, checkpoints, tools, events) persist
    to the database. State survives process restarts.
    """
    from harness.sql_stores import (
        SqlCheckpointManager,
        SqlHarnessRegistry,
        SqlHumanGateManager,
        SqlTelemetryEmitter,
        SqlToolContractRegistry,
    )
    from harness.validation_hooks import ValidationHook

    return SqlHarnessRegistry(
        session=session,
        state_machine=StateMachine(),
        tool_registry=SqlToolContractRegistry(session),
        gate_manager=SqlHumanGateManager(session),
        checkpoint_manager=SqlCheckpointManager(session),
        telemetry=SqlTelemetryEmitter(session),
        validation_hook=ValidationHook(
            primary_validator=primary_validator,
            fallback_validator=fallback_validator,
        ),
    )


async def make_live_l5_registry(
    session,  # AsyncSession — typed loosely to avoid hard import at module level
    tenant_id: str,
    l5_base_url: str | None = None,
    l5_service_token: str | None = None,
    l5_stale_threshold_hours: int = 24,
    fallback_validator: ClaimValidator | None = None,
) -> SqlHarnessRegistry:  # noqa: F821
    """Return a SqlHarnessRegistry with a live Layer 5 Ground Truth validator.

    Reads L5 connection settings from environment variables when not supplied:
      - LAYER5_GROUND_TRUTH_URL (default: http://layer5-ground-truth:8005)
      - LAYER5_SERVICE_TOKEN

    The LiveL5Validator is used as the primary validator. On L5 outage,
    validation degrades to INSUFFICIENT_EVIDENCE — never silently approves.

    Args:
        session: AsyncSession with tenant context set.
        tenant_id: Tenant UUID — used to scope L5 client requests.
        l5_base_url: Override for L5 service base URL.
        l5_service_token: Override for L5 service-to-service JWT.
        l5_stale_threshold_hours: Approved truths older than this are
            downgraded to NEEDS_REVIEW.
        fallback_validator: Optional secondary validator when L5 is unavailable.
    """
    from harness.sql_stores import (
        SqlCheckpointManager,
        SqlHarnessRegistry,
        SqlHumanGateManager,
        SqlTelemetryEmitter,
        SqlToolContractRegistry,
    )
    from harness.validation_hooks import ValidationHook
    from layer4_agents.adapters.harness_l5_validation import create_live_l5_claim_validator

    base_url = l5_base_url or os.environ.get("LAYER5_GROUND_TRUTH_URL", "http://layer5-ground-truth:8005")
    service_token = l5_service_token or os.environ.get("LAYER5_SERVICE_TOKEN")

    primary_validator = create_live_l5_claim_validator(
        base_url=base_url,
        service_token=service_token,
        stale_threshold_hours=l5_stale_threshold_hours,
    )

    return SqlHarnessRegistry(
        session=session,
        state_machine=StateMachine(),
        tool_registry=SqlToolContractRegistry(session),
        gate_manager=SqlHumanGateManager(session),
        checkpoint_manager=SqlCheckpointManager(session),
        telemetry=SqlTelemetryEmitter(session),
        validation_hook=ValidationHook(
            primary_validator=primary_validator,
            fallback_validator=fallback_validator,
        ),
    )
