"""Admin-only write guards for audit tables.

Phase 1: Add admin-only write path guards for audit tables
Issue B: Audit log tamper resistance is not proven
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..api.auth import TokenClaims

_audit_write_stats = {"failures_total": 0, "admin_bypasses": 0}

logger = logging.getLogger(__name__)

# List of roles that can bypass audit write restrictions
ADMIN_ROLES = {"admin", "system", "auditor"}


def is_admin_user(caller: "TokenClaims | None") -> bool:
    """Check if the caller has admin privileges for audit writes.

    Args:
        caller: Token claims from authentication context

    Returns:
        True if caller has admin role, False otherwise
    """
    if caller is None:
        return False
    return any(role in ADMIN_ROLES for role in getattr(caller, "roles", []))


def require_admin_for_audit_write(caller: "TokenClaims | None", operation: str) -> None:
    """Require admin privileges for audit table write operations.

    Args:
        caller: Token claims from authentication context
        operation: Description of the operation being attempted

    Raises:
        PermissionError: If caller lacks admin privileges
    """
    if not is_admin_user(caller):
        _audit_write_stats["failures_total"] += 1
        logger.warning(
            "audit_write_permission_denied",
            extra={
                "operation": operation,
                "user_id": getattr(caller, "user_id", "unknown") if caller else "unknown",
                "tenant_id": str(getattr(caller, "tenant_id", "unknown")) if caller else "unknown",
            },
        )
        try:
            from metrics.prometheus_metrics import get_metrics

            metrics = get_metrics()
            if metrics is not None:
                metrics.increment_audit_write_denials(operation=operation)
        except Exception:
            pass
        raise PermissionError(
            f"Admin privileges required for audit write operation: {operation}. "
            f"User lacks required role from {ADMIN_ROLES}."
        )
    else:
        _audit_write_stats["admin_bypasses"] += 1
        logger.info(
            "audit_write_admin_bypass",
            extra={
                "operation": operation,
                "user_id": getattr(caller, "user_id", "unknown") if caller else "unknown",
            },
        )


def record_audit_write_failure() -> None:
    _audit_write_stats["failures_total"] += 1
    try:
        from metrics.prometheus_metrics import get_metrics

        metrics = get_metrics()
        if metrics is not None:
            metrics.increment_audit_write_failures()
    except Exception:
        return


def get_audit_write_stats() -> Mapping[str, int]:
    return dict(_audit_write_stats)
