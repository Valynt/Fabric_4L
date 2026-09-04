"""Runtime context propagation via ContextVar."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

from .errors import TenantRequiredError
from .models import RuntimeContext

RuntimeContextVar: ContextVar[RuntimeContext | None] = ContextVar(
    "runtime_context", default=None
)


def current_context() -> RuntimeContext | None:
    """Return the current runtime context, if set."""
    return RuntimeContextVar.get()


def get_tenant_id() -> str:
    """Return the current tenant_id or fail closed."""
    ctx = current_context()
    if ctx is None or not ctx.tenant_id:
        raise TenantRequiredError("Cannot resolve tenant_id from current runtime context")
    return ctx.tenant_id


@contextmanager
def with_context(ctx: RuntimeContext) -> Generator[RuntimeContext, None, None]:
    """Run a block of code under an explicit runtime context."""
    token = RuntimeContextVar.set(ctx)
    try:
        yield ctx
    finally:
        RuntimeContextVar.reset(token)
