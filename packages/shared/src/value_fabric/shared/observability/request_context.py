from __future__ import annotations

from contextvars import ContextVar
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LoggingContext:
    request_id: str
    correlation_id: str
    tenant_id: str | None
    route: str
    method: str
    status: int
    latency_ms: float


_logging_context: ContextVar[LoggingContext | None] = ContextVar("logging_context", default=None)


def set_logging_context(context: LoggingContext) -> None:
    _logging_context.set(context)


def get_logging_context() -> LoggingContext | None:
    return _logging_context.get()


def clear_logging_context() -> None:
    _logging_context.set(None)


def logging_context_dict() -> dict[str, object]:
    context = get_logging_context()
    return asdict(context) if context is not None else {}
