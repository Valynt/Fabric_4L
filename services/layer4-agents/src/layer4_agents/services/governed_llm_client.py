from __future__ import annotations

"""GovernedLLMClient — harness-aware LLM call wrapper.

Responsibilities:
- Resolve the correct model for a given ``model_task`` from ``harness.runtime.yaml``
- Enforce per-call token budget caps
- Emit ``llm_call_start`` / ``llm_call_complete`` / ``llm_call_failed`` trace events
- Track cost via ``LLMCostCalculator``
- Retry on transient errors (TIMEOUT, RATE_LIMIT) with exponential backoff
- Return ``LLMCallResult`` carrying usage, cost, and the raw text response

Agents call ``GovernedLLMClient.call()`` instead of touching a provider directly.
The client is constructed once per workflow run and carries the ``HarnessRun``
context so every trace event is correctly attributed.
"""


import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from value_fabric.shared.llm_safety import PromptGuard

from .llm_output_parser import parse_llm_json, validate_llm_output_schema


class LLMOutputValidationError(RuntimeError):
    """Raised when a structured LLM call fails schema validation (ADR-031).

    Carries the model task, call id, and the first validation errors so the
    failure is typed and observable instead of a silent empty payload.
    """

    def __init__(self, *, model_task: str, call_id: str | None, errors: list[str]) -> None:
        preview = "; ".join(errors[:5])
        super().__init__(
            f"structured LLM output failed schema validation for {model_task!r}"
            f" (call_id={call_id!r}): {preview}"
        )
        self.model_task = model_task
        self.call_id = call_id
        self.errors = errors


if TYPE_CHECKING:
    from layer4_agents.harness.models import HarnessRun
    from layer4_agents.harness.telemetry import TelemetryEmitter

    from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal exceptions
# ---------------------------------------------------------------------------


class _CostCapExceeded(Exception):
    """Raised internally when a call's computed cost exceeds max_cost_per_call_usd.

    Never retried. Telemetry is emitted at the raise site before this is raised.
    """


class ModelResolutionError(RuntimeError):
    """Raised when the authoritative runtime map cannot resolve a model."""


# ---------------------------------------------------------------------------
# Config path
# ---------------------------------------------------------------------------

_SERVICE_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_CONFIG_PATH = _SERVICE_ROOT / "config" / "harness.runtime.yaml"


# ---------------------------------------------------------------------------
# Extracted pure helper functions
# ---------------------------------------------------------------------------


def classify_llm_error(exc: Exception) -> str:
    """Classify an LLM call exception into a standard error category.

    Standard categories:
    - TIMEOUT: timeouts / request deadlines
    - RATE_LIMIT: rate limits / throttling
    - AUTH: 401 / unauthorized
    - PROVIDER: generic provider error
    """
    msg = str(exc).lower()
    if "timeout" in msg:
        return "TIMEOUT"
    if "rate" in msg and "limit" in msg:
        return "RATE_LIMIT"
    if "401" in msg or "unauthorized" in msg:
        return "AUTH"
    return "PROVIDER"


def estimate_prompt_tokens_from_messages(
    messages: list[dict[str, Any]] | None,
    fallback_tokens: int = 0,
) -> int:
    """Estimate prompt tokens from message content or fall back to budget cap.

    Approximates ~4 characters per token when messages are present.
    """
    if messages is not None:
        text = " ".join(m.get("content", "") for m in messages if isinstance(m, dict))
        return max(1, len(text) // 4)
    return fallback_tokens


def calculate_llm_call_cost(
    cost_calc: Any | None,
    provider_name: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calculate call cost in USD using the cost calculator if available."""
    if cost_calc is None:
        return 0.0
    return cost_calc.calculate_cost(provider_name, model, prompt_tokens, completion_tokens)


def format_structured_llm_messages(
    messages: list[dict[str, str]],
    schema: dict[str, Any],
) -> list[dict[str, str]]:
    """Append JSON schema instructions to message payload for structured LLM output."""
    augmented = list(messages)
    schema_hint = json.dumps(schema, indent=2)
    json_instruction = (
        f"\n\nRespond with valid JSON only, conforming to this schema:\n{schema_hint}"
    )
    if augmented and augmented[-1].get("role") == "user":
        augmented[-1] = {
            **augmented[-1],
            "content": augmented[-1]["content"] + json_instruction,
        }
    else:
        augmented.append({"role": "user", "content": json_instruction})
    return augmented


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class LLMCallResult:
    """Outcome of a single governed LLM call."""

    content: str
    model: str
    provider: str
    model_task: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    attempt: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


# ---------------------------------------------------------------------------
# GovernedLLMClient
# ---------------------------------------------------------------------------


class GovernedLLMClient:
    """Harness-aware wrapper around an ``LLMProvider``.

    Parameters
    ----------
    provider:
        The underlying ``LLMProvider`` (``TogetherAIProvider``, ``OpenAIProvider``, …).
    provider_name:
        Canonical provider identifier used for cost lookup (``"together"``, ``"openai"``, …).
    run:
        The active ``HarnessRun`` — used to attribute trace events.
    telemetry:
        ``TelemetryEmitter`` instance.  If ``None``, trace events are logged only.
    runtime_config_path:
        Override for the ``harness.runtime.yaml`` path (useful in tests).
    """

    def __init__(
        self,
        provider: LLMProvider,
        provider_name: str,
        run: HarnessRun | None = None,
        telemetry: TelemetryEmitter | None = None,
        runtime_config_path: Path | None = None,
    ) -> None:
        self._provider = provider
        self._provider_name = (
            provider_name.strip().lower() if isinstance(provider_name, str) else provider_name
        )
        self._run = run
        self._telemetry = telemetry
        self._config = self._load_runtime_config(runtime_config_path or _RUNTIME_CONFIG_PATH)
        self._cost_calc = self._build_cost_calculator()
        self._max_cost_per_call_usd: float | None = self._config.get("llm", {}).get(
            "max_cost_per_call_usd"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def call(
        self,
        *,
        model_task: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        call_id: str | None = None,
    ) -> LLMCallResult:
        """Execute a governed LLM call.

        Parameters
        ----------
        model_task:
            One of ``"reasoning"``, ``"extraction"``, ``"narrative"``.
            Used to resolve the model from ``harness.runtime.yaml`` and apply
            token budget caps.
        messages:
            OpenAI-style message list.
        temperature:
            Override the prompt-level temperature.  If ``None``, uses the
            value from the prompt template (caller's responsibility to pass it).
        max_tokens:
            Override the budget cap.  Capped at the configured maximum.
        response_format:
            Passed through to the provider (e.g. ``{"type": "json_object"}``).
        call_id:
            Optional identifier for correlating trace events with a specific
            prompt invocation.
        """
        model = self._resolve_model(model_task)
        budget = self._resolve_budget(model_task)
        effective_max_tokens = self._cap_tokens(max_tokens, budget.get("max_completion_tokens"))

        # Pre-call cost guard: estimate cost from actual message length where
        # possible, falling back to budget caps.  Rejects before touching the
        # provider to prevent billing surprises.
        estimated_cost = self._estimate_call_cost(model_task, model, messages)
        if self._max_cost_per_call_usd is not None and estimated_cost > self._max_cost_per_call_usd:
            self._emit_raw(
                "llm_call_failed",
                {
                    "model_task": model_task,
                    "model": model,
                    "provider": self._provider_name,
                    "error": "cost_cap_exceeded",
                    "cost_usd": estimated_cost,
                    "max_cost_usd": self._max_cost_per_call_usd,
                    "pre_call": True,
                    **({"call_id": call_id} if call_id else {}),
                },
            )
            raise _CostCapExceeded()

        self._emit_call_start(model_task, model, call_id)

        retry_cfg = self._config.get("llm", {}).get("retry", {})
        max_attempts = int(retry_cfg.get("max_attempts", 3))
        backoff = float(retry_cfg.get("backoff_seconds", 2.0))
        retryable = set(retry_cfg.get("retryable_categories", ["TIMEOUT", "RATE_LIMIT"]))

        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            t0 = time.monotonic()
            try:
                self._scan_for_prompt_injection(
                    messages, model_task=model_task, model=model, call_id=call_id
                )
                response = await self._provider.complete_text(
                    model=model,
                    messages=messages,
                    temperature=temperature if temperature is not None else 0.2,
                    max_tokens=effective_max_tokens,
                    response_format=response_format,
                )
                latency_ms = (time.monotonic() - t0) * 1000
                cost = self._calculate_cost(
                    model,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )
                # Post-call secondary guard: actual cost may exceed the pre-call
                # estimate (e.g. when the model returns more tokens than budgeted).
                # llm_call_failed is emitted here to close the open llm_call_start
                # trace event — without it the start event would be left dangling
                # with no matching complete or failed counterpart.
                if self._max_cost_per_call_usd is not None and cost > self._max_cost_per_call_usd:
                    self._emit_raw(
                        "llm_call_failed",
                        {
                            "model_task": model_task,
                            "model": model,
                            "provider": self._provider_name,
                            "error": "cost_cap_exceeded",
                            "cost_usd": cost,
                            "max_cost_usd": self._max_cost_per_call_usd,
                            "pre_call": False,
                            **({"call_id": call_id} if call_id else {}),
                        },
                    )
                    raise _CostCapExceeded()
                result = LLMCallResult(
                    content=response.content,
                    model=model,
                    provider=self._provider_name,
                    model_task=model_task,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    attempt=attempt,
                )
                self._emit_call_complete(result, call_id)
                return result

            except _CostCapExceeded:
                # Telemetry already emitted at the raise site. Never retry.
                raise
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                latency_ms = (time.monotonic() - t0) * 1000
                last_exc = exc
                category = self._classify_error(exc)
                logger.warning(
                    "LLM call failed (attempt %d/%d, category=%s, model=%s)",
                    attempt,
                    max_attempts,
                    category,
                    model,
                )
                if category not in retryable or attempt == max_attempts:
                    self._emit_call_failed(model_task, model, category, call_id)
                    raise
                await asyncio.sleep(backoff * (2 ** (attempt - 1)))

        # Should not reach here, but satisfy type checker
        self._emit_call_failed(model_task, model, "exhausted_attempts", call_id)
        raise RuntimeError(f"LLM call exhausted {max_attempts} attempts") from last_exc

    async def call_structured(
        self,
        *,
        model_task: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        temperature: float | None = None,
        max_tokens: int | None = None,
        call_id: str | None = None,
    ) -> tuple[dict[str, Any], LLMCallResult]:
        """Call the LLM and parse the response as structured JSON.

        Always routes through ``call()`` so that token usage, cost, and trace
        events are captured correctly.  The ``schema`` is appended to the last
        user message as a JSON instruction so the model knows the expected shape.

        Returns ``(parsed_dict, LLMCallResult)``.
        """
        # Append schema hint to the last user message so the model returns JSON
        augmented = format_structured_llm_messages(messages, schema)

        result = await self.call(
            model_task=model_task,
            messages=augmented,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            call_id=call_id,
        )
        parsed = parse_llm_json(
            result.content,
            call_site="governed_llm_client.call_structured",
            strict=True,
        )
        errors = validate_llm_output_schema(
            parsed,
            schema,
            call_site="governed_llm_client.call_structured",
        )
        if errors:
            raise LLMOutputValidationError(
                model_task=model_task,
                call_id=call_id,
                errors=errors,
            )
        return parsed, result

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _resolve_model(self, model_task: str) -> str:
        """Resolve model name from layer4_agents.harness.runtime.yaml for the active provider."""
        llm_cfg = self._config.get("llm", {})
        raw_provider = os.getenv(
            "LAYER4_LLM_PROVIDER", llm_cfg.get("provider", self._provider_name)
        )
        provider = raw_provider.strip().lower() if isinstance(raw_provider, str) else raw_provider
        models = llm_cfg.get("models", {}).get(provider, {})
        model = models.get(model_task)
        if not model:
            self._emit_raw(
                "llm_routing_rejected",
                {
                    "provider": provider,
                    "model_task": model_task,
                    "reason": "unresolvable_model",
                },
            )
            raise ModelResolutionError(
                f"No model configured for provider={provider!r}, task={model_task!r}"
            )
        return str(model)

    def _resolve_budget(self, model_task: str) -> dict[str, int]:
        return self._config.get("llm", {}).get("token_budgets", {}).get(model_task, {})

    def _cap_tokens(self, requested: int | None, cap: int | None) -> int | None:
        if cap is None:
            return requested
        if requested is None:
            return cap
        return min(requested, cap)

    def _provider_default_model(self) -> str:
        """Return a safe fallback model for the active provider."""
        defaults = {
            "together": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
        }
        return defaults.get(self._provider_name, "meta-llama/Llama-3.3-70B-Instruct-Turbo")

    # ------------------------------------------------------------------
    # Cost
    # ------------------------------------------------------------------

    def _estimate_call_cost(
        self,
        model_task: str,
        model: str,
        messages: list[dict] | None = None,
    ) -> float:
        """Estimate cost for a call before it is made.

        Prompt-token estimate priority:
        1. ``len(concatenated message text) / 4`` when ``messages`` is provided
           (rough but accurate for typical prompts).
        2. ``max_prompt_tokens`` from the task budget cap as a fallback when
           messages are unavailable — this is a conservative upper bound that
           may produce false positives for small prompts against large budgets.

        Completion tokens always use ``max_completion_tokens`` from the budget
        (we cannot know actual completion length before the call).

        Returns 0.0 when no cost calculator is available.
        """
        if self._cost_calc is None:
            return 0.0
        budget = self._resolve_budget(model_task)
        max_completion = budget.get("max_completion_tokens", 0)
        budget_prompt_tokens = budget.get("max_prompt_tokens", 0)
        prompt_tokens = estimate_prompt_tokens_from_messages(messages, budget_prompt_tokens)

        return calculate_llm_call_cost(
            self._cost_calc,
            self._provider_name,
            model,
            prompt_tokens,
            max_completion,
        )

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        return calculate_llm_call_cost(
            self._cost_calc,
            self._provider_name,
            model,
            prompt_tokens,
            completion_tokens,
        )

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    def _emit_call_start(self, model_task: str, model: str, call_id: str | None) -> None:
        meta = {"model_task": model_task, "model": model, "provider": self._provider_name}
        if call_id:
            meta["call_id"] = call_id
        self._emit_raw("llm_call_start", meta)

    def _emit_call_complete(self, result: LLMCallResult, call_id: str | None) -> None:
        # Required structured log fields (S6-R4.2):
        # tenant_id and workflow_id are injected by _emit_raw via self._run.
        meta = {
            "model_task": result.model_task,
            "model": result.model,
            "provider": result.provider,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "cost_usd": result.cost_usd,
            "latency_ms": round(result.latency_ms, 1),
            "attempt": result.attempt,
        }
        if call_id:
            meta["call_id"] = call_id
        self._emit_raw("llm_call_complete", meta)

    def _emit_call_failed(
        self, model_task: str, model: str, error: str, call_id: str | None
    ) -> None:
        meta = {
            "model_task": model_task,
            "model": model,
            "provider": self._provider_name,
            "error": error[:500],
        }
        if call_id:
            meta["call_id"] = call_id
        self._emit_raw("llm_call_failed", meta)

    def _scan_for_prompt_injection(
        self,
        messages: list[dict[str, str]],
        *,
        model_task: str,
        model: str,
        call_id: str | None,
    ) -> None:
        """Screen non-system message content for prompt injection (V1-AI-001).

        System prompts are trusted (repository-authored). User-role content is
        where retrieved documents and caller input land. Definite injections
        (CRITICAL/HIGH per PromptGuard) raise ``PromptInjectionError`` and emit
        ``llm_call_failed`` so the trace event chain stays closed; weaker
        signals are logged by the guard and allowed through unless the
        environment escalates via ``LLM_SAFETY_FAIL_CLOSED``.
        """
        guard = PromptGuard(fail_closed=True)
        tenant_id = getattr(self._run, "tenant_id", None) if self._run else None
        for message in messages:
            if not isinstance(message, dict) or message.get("role") == "system":
                continue
            content = message.get("content")
            if not isinstance(content, str) or not content:
                continue
            result = guard.check(
                content,
                context={"tenant_id": tenant_id, "call_id": call_id, "model_task": model_task},
            )
            if result.is_injection:
                self._emit_call_failed(model_task, model, "prompt_injection_detected", call_id)
                # PromptGuard(fail_closed=True) already raised above; this is
                # unreachable but keeps the control flow explicit.
                raise AssertionError("unreachable")

    def _emit_raw(self, event_type: str, metadata: dict[str, Any]) -> None:
        """Emit a trace event if a run + telemetry emitter are available."""
        if self._run is None or self._telemetry is None:
            logger.debug("LLM trace [%s]: %s", event_type, metadata)
            return
        try:
            from layer4_agents.harness.models import HarnessTraceEvent

            event = HarnessTraceEvent(
                trace_id=self._run.trace_id,
                run_id=self._run.id,
                tenant_id=self._run.tenant_id,
                account_id=getattr(self._run, "account_id", None),
                workflow_type=self._run.workflow_type,
                event_type=event_type,
                metadata=metadata,
            )
            self._telemetry.emit(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Failed to emit LLM trace event %s: %s", event_type, exc)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _load_runtime_config(path: Path) -> dict[str, Any]:
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Could not load harness.runtime.yaml from %s: %s", path, exc)
            return {}

    @staticmethod
    def _build_cost_calculator() -> Any | None:
        try:
            from ..metrics.llm_cost_calculator import LLMCostCalculator

            return LLMCostCalculator()
        except asyncio.CancelledError:
            raise
        except Exception:
            return None

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        return classify_llm_error(exc)

    # _parse_json removed — use parse_llm_json (services.llm_output_parser) per §2.5
