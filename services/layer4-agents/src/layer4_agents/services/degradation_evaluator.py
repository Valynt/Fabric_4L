from __future__ import annotations

"""Degradation policy evaluation and execution tracking (ADR-031, Pass 1).

Evaluates declarative degradation ladders defined in `harness.runtime.yaml`,
tracks ladder rungs and fallback transitions, and produces contract-compliant
audit payloads and generation metadata.
"""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

import yaml

from value_fabric.shared.error_handling import sanitize_log_error

from ..models.degradation_policy import (
    DegradationPoliciesConfig,
    DegradationPolicy,
    DegradationRungKind,
    OutputMarking,
)

logger = logging.getLogger(__name__)

import os

_SERVICE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_RUNTIME_CONFIG_PATH = _SERVICE_ROOT / "config" / "harness.runtime.yaml"

T = TypeVar("T")


class DegradationPolicyError(RuntimeError):
    """Raised when degradation policy evaluation encounters an unrecoverable failure."""


def _resolve_runtime_config_path(path: Path | None = None) -> Path:
    """Resolve runtime config path from candidates if default does not exist."""
    if path is not None and path.exists():
        return path
    env_path = os.getenv("HARNESS_RUNTIME_CONFIG_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    candidate_paths = [
        _DEFAULT_RUNTIME_CONFIG_PATH,
        Path("/app/config/harness.runtime.yaml"),
        Path("/app/src/config/harness.runtime.yaml"),
        Path.cwd() / "services" / "layer4-agents" / "config" / "harness.runtime.yaml",
        Path.cwd() / "config" / "harness.runtime.yaml",
    ]
    for cp in candidate_paths:
        if cp.exists():
            return cp
    return path or _DEFAULT_RUNTIME_CONFIG_PATH


def load_degradation_policies(path: Path | None = None) -> DegradationPoliciesConfig:
    """Load and validate all degradation policies from harness.runtime.yaml.

    Fails closed if the configuration file is missing, unreadable, or invalid.
    """
    config_path = _resolve_runtime_config_path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Runtime configuration file not found at {config_path}")

    raw_text = config_path.read_text(encoding="utf-8")
    parsed_yaml = yaml.safe_load(raw_text)
    if not isinstance(parsed_yaml, dict):
        raise ValueError(f"Expected YAML dictionary in {config_path}, got {type(parsed_yaml).__name__}")

    return DegradationPoliciesConfig.model_validate(parsed_yaml)


def validate_degradation_runtime_config(path: Path | None = None) -> DegradationPoliciesConfig:
    """Validate degradation policies in the runtime configuration (startup check)."""
    return load_degradation_policies(path)


class DegradationExecutionTracker:
    """Tracks execution of a single task through its degradation policy ladder."""

    def __init__(
        self,
        *,
        task_name: str,
        policy: DegradationPolicy,
        tenant_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> None:
        self.task_name = task_name
        self.policy = policy
        self.tenant_id = tenant_id
        self.trace_id = trace_id
        self.workflow_id = workflow_id

        self.attempts: int = 0
        self.failed_rungs: list[dict[str, Any]] = []
        self.selected_tier: str | None = None
        self.provider: str | None = None
        self.model: str | None = None
        self.completed: bool = False

    @property
    def failed_tiers(self) -> list[str]:
        """List of tiers that failed during execution."""
        return [f["tier"] for f in self.failed_rungs]

    @property
    def is_degraded(self) -> bool:
        """True if any fallback was needed or a non-primary tier was selected."""
        if bool(self.failed_rungs):
            return True
        if self.selected_tier in ("heuristic", "template"):
            return True
        return False

    @property
    def degradation_reason(self) -> str | None:
        """Joined string of failed rung reasons, or None if no failure occurred."""
        if not self.failed_rungs:
            if self.selected_tier in ("heuristic", "template"):
                return f"{self.selected_tier}_fallback_applied"
            return None
        return ",".join(f["reason"] for f in self.failed_rungs)

    @property
    def output_marking_required(self) -> bool:
        """Whether output marking is required per policy."""
        return self.policy.output_marking == OutputMarking.REQUIRED

    def record_attempt(self) -> int:
        """Increment and return the current attempt count."""
        self.attempts += 1
        return self.attempts

    def record_failure(
        self,
        *,
        rung_kind: DegradationRungKind | str,
        tier: str,
        reason: str,
        exc: Exception | None = None,
    ) -> None:
        """Record a failure of a specific rung / tier."""
        kind_str = rung_kind.value if isinstance(rung_kind, DegradationRungKind) else str(rung_kind)
        failure_record = {
            "rung_kind": kind_str,
            "tier": tier,
            "reason": reason,
            "attempt": self.attempts,
            "error": sanitize_log_error(exc) if exc is not None else None,
        }
        self.failed_rungs.append(failure_record)
        logger.warning(
            "Degradation rung failed for task=%s, tier=%s, reason=%s",
            self.task_name, tier, reason,
        )

    def record_success(
        self,
        *,
        tier: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        """Record successful execution at a specific tier."""
        self.selected_tier = tier
        self.provider = provider
        self.model = model
        self.completed = True

    def build_generation_metadata(
        self, extra: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Build response metadata matching the AgentStreamResponse contract."""
        meta: dict[str, Any] = {
            "response_tier": self.selected_tier or "unknown",
            "provider": self.provider,
            "fallback": self.is_degraded,
            "degraded": self.is_degraded,
            "degradation_reason": self.degradation_reason,
        }
        if extra:
            meta.update(extra)
        return meta

    def build_audit_details(
        self, *, resource_id: str = "conversation-agent"
    ) -> dict[str, Any]:
        """Build details dict for the llm_degradation_applied audit event."""
        return {
            "event_type": "llm_degradation_applied",
            "tenant_id": self.tenant_id,
            "run_id": self.workflow_id,
            "trace_id": self.trace_id,
            "selected_tier": self.selected_tier or "unknown",
            "reason": self.degradation_reason or "degradation_policy_applied",
            "degraded": True,
        }


class DegradationEvaluator:
    """Evaluates degradation policies and executes fallback ladders."""

    def __init__(
        self,
        policy: DegradationPolicy | None = None,
        *,
        task_name: str = "conversation",
        runtime_config_path: Path | None = None,
    ) -> None:
        self.task_name = task_name
        if policy is not None:
            self.policy = policy
        else:
            try:
                all_policies = load_degradation_policies(runtime_config_path)
                resolved_policy = all_policies.get_policy(task_name)
                if resolved_policy is None:
                    # Default minimal policy with 1 retry and required marking
                    self.policy = DegradationPolicy()
                else:
                    self.policy = resolved_policy
            except (FileNotFoundError, ValueError) as exc:
                logger.warning(
                    "Degradation runtime config not loadable (%s); using default DegradationPolicy for task=%s",
                    exc,
                    task_name,
                )
                self.policy = DegradationPolicy()

    @classmethod
    def from_task(
        cls,
        task_name: str,
        *,
        runtime_config_path: Path | None = None,
    ) -> DegradationEvaluator:
        """Factory method to construct an evaluator for a specific task."""
        return cls(task_name=task_name, runtime_config_path=runtime_config_path)

    def create_tracker(
        self,
        *,
        tenant_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> DegradationExecutionTracker:
        """Create a new execution tracker for a single run."""
        return DegradationExecutionTracker(
            task_name=self.task_name,
            policy=self.policy,
            tenant_id=tenant_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
        )

    async def execute_cascade(
        self,
        *,
        primary_fn: Callable[[], Awaitable[T | None]],
        failover_fn: Callable[[], Awaitable[T | None]] | None = None,
        heuristic_fn: Callable[[], Awaitable[T | None] | T | None] | None = None,
        template_fn: Callable[[], Awaitable[T | None] | T | None] | None = None,
        tracker: DegradationExecutionTracker | None = None,
        tenant_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> tuple[T, DegradationExecutionTracker]:
        """Execute callable tiers following the declared ladder order."""
        exec_tracker = tracker or self.create_tracker(
            tenant_id=tenant_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
        )

        # 1. Primary execution with configured retry limit
        max_retries = max(1, self.policy.max_retries)
        for attempt in range(1, max_retries + 1):
            exec_tracker.record_attempt()
            try:
                result = await primary_fn()
                if result is not None:
                    exec_tracker.record_success(tier="primary")
                    return result, exec_tracker
                exec_tracker.record_failure(
                    rung_kind=DegradationRungKind.RETRY,
                    tier="primary",
                    reason=f"primary_empty_attempt_{attempt}",
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                exec_tracker.record_failure(
                    rung_kind=DegradationRungKind.RETRY,
                    tier="primary",
                    reason=f"primary_failed_attempt_{attempt}",
                    exc=exc,
                )

        # 2. Iterate remaining rungs in ladder order
        for step in self.policy.ladder:
            if step.kind == DegradationRungKind.RETRY:
                continue  # already exhausted above

            if step.kind == DegradationRungKind.FAILOVER:
                if failover_fn is not None:
                    try:
                        result = await failover_fn()
                        if result is not None:
                            exec_tracker.record_success(
                                tier=step.failover.tier if step.failover else "failover",
                                provider=step.failover.provider if step.failover else None,
                                model=step.failover.model if step.failover else None,
                            )
                            return result, exec_tracker
                        exec_tracker.record_failure(
                            rung_kind=DegradationRungKind.FAILOVER,
                            tier=step.failover.tier if step.failover else "failover",
                            reason="failover_empty",
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        exec_tracker.record_failure(
                            rung_kind=DegradationRungKind.FAILOVER,
                            tier=step.failover.tier if step.failover else "failover",
                            reason="failover_failed",
                            exc=exc,
                        )

            elif step.kind == DegradationRungKind.HEURISTIC:
                if heuristic_fn is not None:
                    try:
                        res = heuristic_fn()
                        if inspect.isawaitable(res):
                            res = await res
                        if res is not None:
                            exec_tracker.record_success(
                                tier="heuristic",
                            )
                            return res, exec_tracker
                        exec_tracker.record_failure(
                            rung_kind=DegradationRungKind.HEURISTIC,
                            tier="heuristic",
                            reason="heuristic_empty",
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        exec_tracker.record_failure(
                            rung_kind=DegradationRungKind.HEURISTIC,
                            tier="heuristic",
                            reason="heuristic_failed",
                            exc=exc,
                        )

            elif step.kind == DegradationRungKind.TEMPLATE:
                if template_fn is not None:
                    try:
                        res = template_fn()
                        if inspect.isawaitable(res):
                            res = await res
                        if res is not None:
                            exec_tracker.record_success(
                                tier="template",
                            )
                            return res, exec_tracker
                        exec_tracker.record_failure(
                            rung_kind=DegradationRungKind.TEMPLATE,
                            tier="template",
                            reason="template_empty",
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        exec_tracker.record_failure(
                            rung_kind=DegradationRungKind.TEMPLATE,
                            tier="template",
                            reason="template_failed",
                            exc=exc,
                        )

        raise DegradationPolicyError(
            f"All rungs in degradation policy ladder exhausted for task {self.task_name}. "
            f"Failed rungs: {exec_tracker.failed_rungs}"
        )
