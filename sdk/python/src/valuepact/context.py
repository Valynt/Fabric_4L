"""Execution context binding for ValuePact CLI commands."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable command execution identity."""

    environment: str
    tenant_id: str
    actor_id: str
    actor_type: Literal["user", "service_account", "system"]
    scopes: frozenset[str]
    request_id: str
    workspace_id: str | None = None
    profile_name: str | None = None


active_execution_context: ContextVar[ExecutionContext | None] = ContextVar(
    "active_execution_context",
    default=None,
)


def get_active_execution_context() -> ExecutionContext | None:
    """Return the currently bound execution context, if any."""

    return active_execution_context.get()


@contextmanager
def bind_execution_context(context: ExecutionContext) -> Generator[None, None, None]:
    """Bind context and restore the previous token on every exit path."""

    token = active_execution_context.set(context)
    try:
        yield
    finally:
        active_execution_context.reset(token)
