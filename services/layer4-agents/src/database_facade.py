from __future__ import annotations

"""Stable Layer 4 database facade used by cross-repo tests.

This module prefers the canonical implementation at
``services/layer4-agents/src/database.py`` and falls back to a lightweight,
dependency-minimal shim when optional service dependencies are unavailable.
"""


import importlib
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import ModuleType
from uuid import UUID

logger = logging.getLogger(__name__)

_CANONICAL: ModuleType | None = None
_CANONICAL_IMPORT_ERROR: Exception | None = None

try:
    _SERVICE_ROOT = Path(__file__).resolve().parents[2] / "services" / "layer4-agents"
    if str(_SERVICE_ROOT) not in sys.path:
        sys.path.insert(0, str(_SERVICE_ROOT))
    _CANONICAL = importlib.import_module("src.database")
except (ImportError, ModuleNotFoundError) as exc:  # pragma: no cover
    _CANONICAL_IMPORT_ERROR = exc

if _CANONICAL is not None:
    for _name in dir(_CANONICAL):
        if not _name.startswith("__"):
            globals()[_name] = getattr(_CANONICAL, _name)
else:
    FAIL_SAFE_MODE = True
    RESERVED_TENANT_KEYWORDS = frozenset({"system", "admin", "internal"})

    try:
        from sqlalchemy.orm import DeclarativeBase

        class Base(DeclarativeBase):
            """Fail-safe declarative base for model imports in constrained tests."""

    except Exception:  # pragma: no cover - only used if SQLAlchemy is unavailable
        class Base:  # type: ignore[no-redef]
            """Minimal fallback so fail-safe imports do not hide auth regressions."""

    class TenantContextError(Exception):
        """Raised when tenant context is missing or invalid in fail-safe mode."""

    _tenant_validation_metrics: dict[str, int] = {
        "validations_total": 0,
        "validation_failures": 0,
        "uuid_format_errors": 0,
        "missing_context_errors": 0,
        "empty_tenant_errors": 0,
    }

    def get_tenant_validation_metrics() -> dict[str, int]:
        return _tenant_validation_metrics.copy()

    def reset_tenant_validation_metrics() -> None:
        _tenant_validation_metrics.update(dict.fromkeys(_tenant_validation_metrics, 0))

    def validate_tenant_id(tenant_id: UUID | str | None) -> str:
        _tenant_validation_metrics["validations_total"] += 1

        if tenant_id is None:
            _tenant_validation_metrics["validation_failures"] += 1
            _tenant_validation_metrics["missing_context_errors"] += 1
            raise TenantContextError("tenant_id is required in fail-safe mode")

        normalized = str(tenant_id).strip().lower()
        if not normalized:
            _tenant_validation_metrics["validation_failures"] += 1
            _tenant_validation_metrics["empty_tenant_errors"] += 1
            raise TenantContextError("tenant_id must not be empty")

        if normalized in RESERVED_TENANT_KEYWORDS:
            return normalized

        try:
            return str(UUID(normalized))
        except ValueError as exc:
            _tenant_validation_metrics["validation_failures"] += 1
            _tenant_validation_metrics["uuid_format_errors"] += 1
            raise TenantContextError("tenant_id must be a valid UUID") from exc

    AUDIT_AVAILABLE = False
    emit_audit_event = None
    AuditAction = None
    AuditOutcome = None
    TenantContextSetDetails = None

    async def _emit_tenant_context_set_audit(
        context,
        tenant_id: str | None,
        *,
        is_bypass: bool = False,
        bypass_reason: str | None = None,
    ) -> None:
        if not AUDIT_AVAILABLE:
            return
        try:
            details = TenantContextSetDetails(
                tenant_id=tenant_id,
                isolation_tier=context.isolation_tier,
                bypass=is_bypass,
                bypass_reason=bypass_reason,
                context_source="request_context",
            )
            await emit_audit_event(
                action=AuditAction.TENANT_CONTEXT_SET,
                outcome=AuditOutcome.SUCCESS,
                resource_type="database_session",
                resource_id=tenant_id,
                actor_id=context.user_id or context.api_key_id or context.service_account_id,
                tenant_id=context.tenant_id,
                request_id=context.request_id,
                details=details.model_dump(exclude_none=True),
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("Tenant context audit emission failed (non-critical): %s", exc)

    async def get_db_from_context(*args, **kwargs):
        """Fail closed when the canonical tenant-enforced DB dependency is unavailable."""
        raise RuntimeError(
            "Canonical Layer 4 get_db_from_context is unavailable; "
            f"refusing to create an unscoped database session: {_CANONICAL_IMPORT_ERROR!r}"
        )

    async def get_db_with_optional_tenant(*args, **kwargs):
        """Fail closed when optional tenant-aware DB dependency cannot delegate."""
        raise RuntimeError(
            "Canonical Layer 4 get_db_with_optional_tenant is unavailable; "
            f"refusing to create an unscoped database session: {_CANONICAL_IMPORT_ERROR!r}"
        )

    @asynccontextmanager
    async def get_tiered_db_session(*args, **kwargs):
        """Fail closed when tier-aware DB sessions cannot delegate."""
        raise RuntimeError(
            "Canonical Layer 4 get_tiered_db_session is unavailable; "
            f"refusing to create an unscoped database session: {_CANONICAL_IMPORT_ERROR!r}"
        )
        yield  # pragma: no cover


def __getattr__(name: str):
    if _CANONICAL is not None:
        return getattr(_CANONICAL, name)
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}. "
        f"Canonical database module unavailable: {_CANONICAL_IMPORT_ERROR!r}"
    )
