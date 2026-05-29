from __future__ import annotations

"""File tools with tenant isolation and path traversal protection.
"""


import logging
import os
from pathlib import Path

from value_fabric.shared.identity.context import RequestContext, require_context

logger = logging.getLogger(__name__)

# Base directory for tenant file storage (configured via env var)
TENANT_STORAGE_ROOT = Path(os.getenv("TENANT_STORAGE_PATH", "/var/lib/services/tenant-files"))


class TenantRequiredError(RuntimeError):
    """Raised when a file operation is attempted without tenant context."""


def _get_tenant_id(context: RequestContext | None = None) -> str:
    """Retrieve tenant ID from explicit context or request context.

    Fails closed — raises TenantRequiredError if no tenant context is available.
    Never falls back to a shared "default" tenant directory.
    """
    if context is not None and context.tenant_id:
        return str(context.tenant_id)

    try:
        ctx = require_context()
        if ctx.tenant_id:
            return str(ctx.tenant_id)
    except RuntimeError:
        pass

    raise TenantRequiredError(
        "Tenant context is required for file operations. "
        "Pass an explicit RequestContext or ensure the call runs inside an authenticated request."
    )


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
    tenant_id = _get_tenant_id(context)

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
    except (OSError, UnicodeDecodeError):
        logger.error(
            "Failed to read file",
            extra={"file_path": str(validated_path), "tenant_id": tenant_id, "error_code": "FILE_READ_ERROR"}
        )
        return None


async def write_file(
    file_path: str,
    content: str,
    context: RequestContext | None = None
) -> bool:
    """Write file with tenant scoping and path validation.

    Args:
        file_path: Relative path within tenant's storage area
        content: Text content to write
        context: Request context (optional, for tenant identification)

    Returns:
        True on success, False on failure
    """
    tenant_id = _get_tenant_id(context)

    validated_path = _validate_path(file_path, tenant_id)
    if validated_path is None:
        return False

    try:
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        validated_path.write_text(content, encoding="utf-8")
        logger.info(
            "File written",
            extra={"file_path": str(validated_path), "tenant_id": tenant_id}
        )
        return True
    except (OSError, ValueError):
        logger.error(
            "Failed to write file",
            extra={"file_path": str(validated_path), "tenant_id": tenant_id, "error_code": "FILE_WRITE_ERROR"}
        )
        return False


async def delete_file(
    file_path: str,
    context: RequestContext | None = None
) -> bool:
    """Delete file with tenant scoping and path validation.

    Args:
        file_path: Relative path within tenant's storage area
        context: Request context (optional, for tenant identification)

    Returns:
        True on success, False on failure or if path is invalid
    """
    tenant_id = _get_tenant_id(context)

    validated_path = _validate_path(file_path, tenant_id)
    if validated_path is None:
        return False

    try:
        if not validated_path.exists():
            logger.info(
                "File not found for deletion",
                extra={"file_path": str(validated_path), "tenant_id": tenant_id}
            )
            return False
        validated_path.unlink()
        logger.info(
            "File deleted",
            extra={"file_path": str(validated_path), "tenant_id": tenant_id}
        )
        return True
    except OSError:
        logger.error(
            "Failed to delete file",
            extra={"file_path": str(validated_path), "tenant_id": tenant_id, "error_code": "FILE_DELETE_ERROR"}
        )
        return False
