"""Phase 3: Structured Logging Context Enrichment.

Provides context enrichment for all Layer 3 logs with:
- tenant_id: Tenant context for isolation
- account_id: Account context for authorization
- request_id: Request tracing ID
- entity_id: Entity being operated on
- operation_source: Source of the operation
"""

from contextvars import ContextVar
from typing import Any

from structlog.types import EventDict

# Context variables for request-scoped data
_tenant_id_ctx: ContextVar[str | None] = ContextVar("tenant_id", default=None)
_account_id_ctx: ContextVar[str | None] = ContextVar("account_id", default=None)
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_entity_id_ctx: ContextVar[str | None] = ContextVar("entity_id", default=None)
_operation_source_ctx: ContextVar[str | None] = ContextVar(
    "operation_source", default=None
)


def set_tenant_context(tenant_id: str | None) -> None:
    """Set tenant context for current request."""
    _tenant_id_ctx.set(tenant_id)


def set_account_context(account_id: str | None) -> None:
    """Set account context for current request."""
    _account_id_ctx.set(account_id)


def set_request_context(request_id: str | None) -> None:
    """Set request ID for tracing."""
    _request_id_ctx.set(request_id)


def set_entity_context(entity_id: str | None) -> None:
    """Set entity ID being operated on."""
    _entity_id_ctx.set(entity_id)


def set_operation_source(operation_source: str | None) -> None:
    """Set operation source for audit trail."""
    _operation_source_ctx.set(operation_source)


def get_tenant_context() -> str | None:
    """Get current tenant context."""
    return _tenant_id_ctx.get()


def get_account_context() -> str | None:
    """Get current account context."""
    return _account_id_ctx.get()


def get_request_context() -> str | None:
    """Get current request ID."""
    return _request_id_ctx.get()


def get_entity_context() -> str | None:
    """Get current entity ID."""
    return _entity_id_ctx.get()


def get_operation_source() -> str | None:
    """Get current operation source."""
    return _operation_source_ctx.get()


def clear_context() -> None:
    """Clear all context variables."""
    _tenant_id_ctx.set(None)
    _account_id_ctx.set(None)
    _request_id_ctx.set(None)
    _entity_id_ctx.set(None)
    _operation_source_ctx.set(None)


class ContextEnrichmentProcessor:
    """Structlog processor to enrich logs with context variables."""

    def __call__(
        self, logger: Any, method_name: str, event_dict: EventDict
    ) -> EventDict:
        """Enrich event dict with context variables."""
        tenant_id = _tenant_id_ctx.get()
        if tenant_id:
            event_dict["tenant_id"] = tenant_id

        account_id = _account_id_ctx.get()
        if account_id:
            event_dict["account_id"] = account_id

        request_id = _request_id_ctx.get()
        if request_id:
            event_dict["request_id"] = request_id

        entity_id = _entity_id_ctx.get()
        if entity_id:
            event_dict["entity_id"] = entity_id

        operation_source = _operation_source_ctx.get()
        if operation_source:
            event_dict["operation_source"] = operation_source

        return event_dict


class LoggingContextManager:
    """Context manager for setting logging context."""

    def __init__(
        self,
        tenant_id: str | None = None,
        account_id: str | None = None,
        request_id: str | None = None,
        entity_id: str | None = None,
        operation_source: str | None = None,
    ):
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.request_id = request_id
        self.entity_id = entity_id
        self.operation_source = operation_source
        self._prev_tenant = None
        self._prev_account = None
        self._prev_request = None
        self._prev_entity = None
        self._prev_source = None

    def __enter__(self):
        """Set context on entry."""
        self._prev_tenant = _tenant_id_ctx.get()
        self._prev_account = _account_id_ctx.get()
        self._prev_request = _request_id_ctx.get()
        self._prev_entity = _entity_id_ctx.get()
        self._prev_source = _operation_source_ctx.get()

        if self.tenant_id is not None:
            set_tenant_context(self.tenant_id)
        if self.account_id is not None:
            set_account_context(self.account_id)
        if self.request_id is not None:
            set_request_context(self.request_id)
        if self.entity_id is not None:
            set_entity_context(self.entity_id)
        if self.operation_source is not None:
            set_operation_source(self.operation_source)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous context on exit."""
        set_tenant_context(self._prev_tenant)
        set_account_context(self._prev_account)
        set_request_context(self._prev_request)
        set_entity_context(self._prev_entity)
        set_operation_source(self._prev_source)
        return False
