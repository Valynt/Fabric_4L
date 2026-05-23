"""File tools with tenant isolation and path traversal protection.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from value_fabric.shared.identity.context import RequestContext, require_context

logger = logging.getLogger(__name__)

# Base directory for tenant file storage (configured via env var)
TENANT_STORAGE_ROOT = Path(os.getenv("TENANT_STORAGE_PATH", "/var/lib/services/tenant-files"))


def _get_tenant_id() -> str:
    """Safely retrieve tenant ID from request context.

    Returns "default" if context is not available (e.g., in tests or background tasks).
    """
    try:
        return str(require_context().tenant_id)
    except RuntimeError:
        return "default"


def _validate_path(file_path: str, tenant_id: str) -> Path | None:
    """Validate and resolve a tenant-scoped file path.

    Args:
        file_path: Relative path within tenant's storage
        tenant_id: Tenant identifier for isolation

    Returns:
        Resolved Path if valid, None if traversal attack detected
    """
    # Reject absolute paths and traversal attempts early
    if os.path.isabs(file_path) or ".." in file_path:
        logger.warning(
            "Path traversal attempt detected",
            extra={"file_path": file_path, "tenant_id": tenant_id}
        )
        return None

    # Build tenant-scoped base directory
    tenant_base = TENANT_STORAGE_ROOT / tenant_id

    # Resolve the full path and verify it's within tenant's scope
    try:
        requested_path = (tenant_base / file_path).resolve()
        resolved_base = tenant_base.resolve()

        # Ensure resolved path is within tenant's directory (prevents symlink attacks)
        if not str(requested_path).startswith(str(resolved_base) + os.sep):
            logger.warning(
                "Path escapes tenant directory",
                extra={
                    "requested": str(requested_path),
                    "tenant_base": str(resolved_base),
                    "tenant_id": tenant_id
                }
            )
            return None

        return requested_path
    except (OSError, ValueError) as e:
        logger.error(
            "Path resolution failed",
            extra={"file_path": file_path, "tenant_id": tenant_id, "error_code": "PATH_RESOLUTION_ERROR"}
        )
        return None


async def read_file(
    file_path: str,
    context: RequestContext | None = None
) -> str | None:
    """Read file with tenant scoping and path validation.

    Args:
        file_path: Relative path within tenant's storage area
        context: Request context (optional, for tenant identification)

    Returns:
        File contents or None if invalid path/not found
    """
    tenant_id = _get_tenant_id()

    validated_path = _validate_path(file_path, tenant_id)
    if validated_path is None:
        return None

    if not validated_path.exists():
        logger.info(
            "File not found",
            extra={"file_path": str(validated_path), "tenant_id": tenant_id}
        )
        return None

    try:
        return validated_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.error(
            "Failed to read file",
            extra={"file_path": str(validated_path), "tenant_id": tenant_id, "error_code": "FILE_READ_ERROR"}
        )
        return None
