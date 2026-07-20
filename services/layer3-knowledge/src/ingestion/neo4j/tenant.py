from __future__ import annotations

from uuid import UUID


class TenantValidationError(ValueError):
    """Raised when tenant context is missing or malformed for ingestion."""


def validate_ingestion_tenant_id(tenant_id: str | None) -> str:
    """Validate public ingestion tenant scope.

    Public Layer 3 ingestion paths are tenant-bound and must not implicitly
    default to platform scope. The accepted format is a non-empty UUID string.
    """
    if tenant_id is None:
        raise TenantValidationError("tenant_id is required for Layer 3 ingestion")

    normalized = str(tenant_id).strip()
    if not normalized:
        raise TenantValidationError("tenant_id is required for Layer 3 ingestion")

    try:
        return str(UUID(normalized))
    except ValueError as exc:
        raise TenantValidationError(
            f"Invalid tenant_id format: {tenant_id}. Expected UUID."
        ) from exc


def _validate_internal_system_tenant_id(tenant_id: str) -> str:
    """Validate the explicit internal-only platform ingestion scope."""
    normalized = str(tenant_id).strip().lower()
    if normalized != "system":
        raise TenantValidationError(
            "internal system ingestion requires tenant_id='system'"
        )
    return normalized
