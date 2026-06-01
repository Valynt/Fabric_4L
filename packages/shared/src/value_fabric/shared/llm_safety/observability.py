"""Observability and tracing for LLM operations (F-18).

Provides OpenTelemetry tracing, structured logging, and metrics for LLM calls.
Enables request correlation and safety event tracking.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Generator
from value_fabric.shared.models.typed_dict import TypedDictModel


class LLMCallContext_to_dictResult(TypedDictModel):
    extraction_job_id: Any
    llm_call_id: Any
    model: Any
    provider: Any
    request_id: Any
    tenant_id: Any
    trace_id: Any

class LLMCallMetrics_to_dictResult(TypedDictModel):
    cost_usd: Any
    error_type: Any
    input_tokens: Any
    latency_ms: Any
    output_tokens: Any
    retry_count: Any
    safety_checks: Any
    total_tokens: Any

# Try to import OpenTelemetry
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None  # type: ignore
    Status = None  # type: ignore
    StatusCode = None  # type: ignore

logger = logging.getLogger(__name__)

# Context variable for current trace/span ID
_current_llm_span: ContextVar[str | None] = ContextVar("current_llm_span", default=None)


@dataclass
class LLMCallContext:
    """Context for an LLM call operation."""

    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str | None = None
    tenant_id: str | None = None
    request_id: str | None = None
    extraction_job_id: str | None = None
    model: str | None = None
    provider: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return LLMCallContext_to_dictResult.model_validate({
            "llm_call_id": self.call_id,
            "trace_id": self.trace_id,
            "tenant_id": self.tenant_id,
            "request_id": self.request_id,
            "extraction_job_id": self.extraction_job_id,
            "model": self.model,
            "provider": self.provider,
        })


@dataclass
class LLMCallMetrics:
    """Metrics for an LLM call."""

    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    retry_count: int = 0
    error_type: str | None = None
    safety_checks: list[str] = field(default_factory=list)

    @property
    def latency_ms(self) -> float:
        """Calculate latency in milliseconds."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        return LLMCallMetrics_to_dictResult.model_validate({
            "latency_ms": round(self.latency_ms, 2),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "retry_count": self.retry_count,
            "error_type": self.error_type,
            "safety_checks": self.safety_checks,
        })


class LLMObservability:
    """Observability provider for LLM operations.

    Integrates with OpenTelemetry for distributed tracing and provides
    structured logging for LLM safety events.
    """

    def __init__(self) -> None:
        """Initialize observability."""
        self.enabled = OPENTELEMETRY_AVAILABLE
        self.tracer = trace.get_tracer(__name__) if self.enabled else None

    def create_call_context(
        self,
        tenant_id: str | None = None,
        request_id: str | None = None,
        extraction_job_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> LLMCallContext:
        """Create a new LLM call context.

        Args:
            tenant_id: Tenant identifier
            request_id: Parent request ID
            extraction_job_id: Extraction job ID for tracking
            model: Model name being called
            provider: Provider name (openai, anthropic)

        Returns:
            LLMCallContext with generated call_id
        """
        # Get trace ID from current span if available
        trace_id = None
        if self.enabled and trace is not None:
            current_span = trace.get_current_span()
            if current_span:
                ctx = current_span.get_span_context()
                trace_id = format(ctx.trace_id, "032x") if ctx.trace_id else None

        return LLMCallContext(
            trace_id=trace_id,
            tenant_id=tenant_id,
            request_id=request_id,
            extraction_job_id=extraction_job_id,
            model=model,
            provider=provider,
        )

    @contextmanager
    def trace_llm_call(
        self,
        context: LLMCallContext,
        operation: str = "chat_completion",
    ) -> Generator[LLMCallMetrics, None, None]:
        """Context manager for tracing an LLM call.

        Args:
            context: LLM call context
            operation: Operation name for span

        Yields:
            LLMCallMetrics for recording call details
        """
        metrics = LLMCallMetrics()
        span = None

        # Set context variable for nested operations
        token = _current_llm_span.set(context.call_id)

        try:
            if self.enabled and self.tracer:
                with self.tracer.start_as_current_span(
                    f"llm.{operation}",
                    attributes={
                        "llm.provider": context.provider or "unknown",
                        "llm.model": context.model or "unknown",
                        "llm.tenant_id": context.tenant_id or "unknown",
                        "llm.extraction_job_id": context.extraction_job_id or "",
                        "llm.call_id": context.call_id,
                    },
                ) as span:
                    yield metrics
                    # Set span status based on error (only if Status available)
                    if Status is not None and StatusCode is not None:
                        if metrics.error_type:
                            span.set_status(
                                Status(StatusCode.ERROR, description=metrics.error_type)
                            )
                        else:
                            span.set_status(Status(StatusCode.OK))
            else:
                yield metrics

        finally:
            metrics.end_time = time.time()
            _current_llm_span.reset(token)

            # Log completion
            self._log_call_completion(context, metrics)

    def record_safety_event(
        self,
        event_type: str,
        severity: str,
        details: dict[str, Any],
        context: LLMCallContext | None = None,
    ) -> None:
        """Record a safety-related event.

        Args:
            event_type: Type of safety event (injection, pii, validation)
            severity: Event severity (critical, high, medium, low)
            details: Event details
            context: Optional LLM call context
        """
        ctx = context.to_dict() if context else {}

        logger.warning(
            f"LLM safety event: {event_type}",
            extra={
                "event_type": event_type,
                "severity": severity,
                "details": details,
                **ctx,
            },
        )

    def record_error(
        self,
        error: Exception,
        error_type: str,
        context: LLMCallContext | None = None,
    ) -> None:
        """Record an LLM-related error.

        Args:
            error: The exception that occurred
            error_type: Classified error type
            context: Optional LLM call context
        """
        ctx = context.to_dict() if context else {}

        logger.error(
            f"LLM error: {error_type}",
            extra={
                "error_type": error_type,
                "error_message": str(error),  # ban-str-e-allow: structured-log
                "error_class": error.__class__.__name__,
                **ctx,
            },
            exc_info=error,
        )

    def _log_call_completion(
        self,
        context: LLMCallContext,
        metrics: LLMCallMetrics,
    ) -> None:
        """Log LLM call completion with metrics."""
        logger.info(
            "LLM call completed",
            extra={
                **context.to_dict(),
                **metrics.to_dict(),
            },
        )

    def get_current_call_id(self) -> str | None:
        """Get the current LLM call ID from context.

        Returns:
            Current call ID or None
        """
        return _current_llm_span.get()


def get_observability() -> LLMObservability:
    """Get or create singleton observability instance."""
    # Simple singleton pattern
    if not hasattr(get_observability, "_instance"):
        get_observability._instance = LLMObservability()  # type: ignore
    return get_observability._instance  # type: ignore
