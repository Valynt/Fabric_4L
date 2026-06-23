"""Shared tenant validation utilities for Value Fabric services.

Provides common tenant ID validation and context management
to reduce code duplication across services and ensure
consistent tenant isolation security policies.
"""

import logging
from uuid import UUID

from value_fabric.shared.tenant_context_metrics import record_inconsistent_tenant_context_access

logger = logging.getLogger(__name__)

# Canonical name for the privileged system tenant.  All code that needs to
# pass or compare the system-tenant ID must use this constant — never a bare
# string literal — so that typos are caught at import time and grep searches
# are reliable.
SYSTEM_TENANT_ID: str = "system"

# Reserved tenant keywords for system/admin operations
RESERVED_TENANT_KEYWORDS: frozenset[str] = frozenset({SYSTEM_TENANT_ID, "admin", "internal"})


class TenantContextError(Exception):
    """Raised when tenant context is missing or invalid."""

    pass


class MissingTenantContextError(TenantContextError, PermissionError):
    """Raised when tenant-scoped persistence is attempted without tenant context."""

    pass


def validate_tenant_id(
    tenant_id: UUID | str | None,
    fail_safe_mode: bool = True,
    reserved_keywords: frozenset[str] = RESERVED_TENANT_KEYWORDS,
) -> str:
    """
    Validate tenant_id format and return normalized string.

    SECURITY: Strict validation to prevent tenant confusion attacks.

    Args:
        tenant_id: Tenant identifier to validate (UUID object, UUID string, or None)
        fail_safe_mode: If True, reject missing tenant_id. If False, return empty string.
        reserved_keywords: Set of reserved keywords allowed (e.g., 'system', 'admin')

    Returns:
        Normalized tenant ID string (lowercase UUID format or reserved keyword)

    Raises:
        TenantContextError: If tenant_id is invalid or missing in fail-safe mode

    Examples:
        >>> validate_tenant_id(UUID('550e8400-e29b-41d4-a716-446655440000'))
        '550e8400-e29b-41d4-a716-446655440000'
        >>> validate_tenant_id('system')
        'system'
    """
    if tenant_id is None:
        if fail_safe_mode:
            raise TenantContextError(
                "Tenant context is mandatory. Ensure request includes valid tenant_id "
                "in JWT token or X-Tenant-ID header. For admin operations, use "
                "appropriate admin bypass mechanisms."
            )
        return ""

    # Convert to string and normalize
    normalized = str(tenant_id).strip()

    # Fail-safe: empty tenant_id is not allowed
    if not normalized:
        raise TenantContextError(
            "Empty tenant_id is not allowed. Provide a valid tenant context."
        )

    # Validate UUID format for strict tenant isolation
    if normalized.lower() not in reserved_keywords:
        try:
            UUID(normalized)
        except ValueError:
            raise TenantContextError(
                f"Invalid tenant_id format: '{normalized}'. Expected valid UUID or "
                f"reserved keyword ({', '.join(sorted(reserved_keywords))})."
            )

    return normalized


def require_tenant_context(
    tenant_id: UUID | str | None,
    *,
    operation: str = "tenant-scoped persistence access",
    reserved_keywords: frozenset[str] = RESERVED_TENANT_KEYWORDS,
) -> str:
    """Require tenant context for a tenant-scoped operation.

    This is stricter than ``validate_tenant_id`` only in the sense that the
    exception type is authorization-oriented, making it suitable for
    repository/session boundaries where unscoped access must hard-fail.
    """
    try:
        return validate_tenant_id(
            tenant_id,
            fail_safe_mode=True,
            reserved_keywords=reserved_keywords,
        )
    except TenantContextError as exc:
        raise MissingTenantContextError(
            f"{operation} requires authenticated tenant context."
        ) from exc
