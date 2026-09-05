from __future__ import annotations

"""System Maintenance Identity and Authorization Framework.

Provides dedicated system maintenance identity separate from tenant admin roles.
All system-scoped operations must use this framework for proper authorization
and audit logging.

Usage:
    # Check authorization for system operation
    authorize_maintenance_operation("cleanup_old_content", tenant_id=None)
    
    # Execute tenant-iterated cleanup under RLS
    with maintenance_audit_log("cleanup_old_content", tenant_id="tenant-123"):
        # RLS-enforced operations only
        pass
    
    # Execute system-scoped maintenance (requires system identity)
    with system_maintenance_context():
        # Global table operations only
        pass
"""


import os
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog
from value_fabric.shared.error_handling import sanitize_log_error

from .exceptions import (
    SystemMaintenanceAuthorizationError,
)

logger = structlog.get_logger()


# Token type constants
MAINTENANCE_TOKEN_PREFIX = "fabric4l-maintenance"
TENANT_TOKEN_PREFIX = "fabric4l-tenant"
MAX_TOKEN_AGE_SECONDS = 86400  # 24 hours


class TokenType(Enum):
    """Types of authentication tokens."""
    MAINTENANCE = "maintenance"
    TENANT = "tenant"
    UNKNOWN = "unknown"
    INVALID = "invalid"


def detect_token_type(token: str | None) -> TokenType:
    """Detect the type of authentication token.
    
    Critical security check: prevents token confusion attacks where
    a tenant token is used as maintenance token or vice versa.
    
    Args:
        token: The token string to analyze
        
    Returns:
        TokenType enum indicating the token type
    """
    if not token:
        return TokenType.INVALID
    
    # Check for maintenance token prefix
    if token.startswith(f"{MAINTENANCE_TOKEN_PREFIX}:"):
        return TokenType.MAINTENANCE
    
    # Check for tenant token prefix (JWT or session tokens)
    if token.startswith(f"{TENANT_TOKEN_PREFIX}:"):
        return TokenType.TENANT
    
    # Check for common tenant token patterns
    if token.startswith("eyJ") or token.startswith("sk-") or token.startswith("clerk_"):
        return TokenType.TENANT
    
    return TokenType.UNKNOWN


class MaintenanceOperation(Enum):
    """Allowlisted system maintenance operations."""
    
    CLEANUP_OLD_CONTENT = "cleanup_old_content"
    MIGRATE_DATA = "migrate_data"
    SYSTEM_HEALTH_CHECK = "system_health_check"
    RECONCILE_STUCK_JOBS = "reconcile_stuck_jobs"
    CACHE_WARMING = "cache_warming"
    INDEX_REBUILD = "index_rebuild"
    AUDIT_EXPORT = "audit_export"
    
    @classmethod
    def has_value(cls, value: str) -> bool:
        """Check if operation is in allowlist."""
        return any(op.value == value for op in cls)


@dataclass
class MaintenanceAuditRecord:
    """Audit record for system maintenance operations."""
    
    operation: str
    tenant_id: str | None = None
    system_identity: str | None = None
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    rows_affected: int = 0
    success: bool = False
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "operation": self.operation,
            "tenant_id": self.tenant_id,
            "system_identity": self.system_identity,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rows_affected": self.rows_affected,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class SystemMaintenanceIdentity:
    """System maintenance identity for authorized operations."""
    
    def __init__(self, identity_token: str | None = None):
        """
        Initialize system maintenance identity.

        Args:
            identity_token: System maintenance token from environment or secure store.
                If omitted, the token is read lazily from FABRIC4L_MAINTENANCE_TOKEN
                so tests and runtime configuration can update it.
        """
        self._explicit_token = identity_token
        self.identity_name = "fabric4l-system-maintenance"

    @property
    def identity_token(self) -> str | None:
        """Return the configured token, falling back to the environment variable."""
        return self._explicit_token or os.getenv("FABRIC4L_MAINTENANCE_TOKEN")

    def is_valid(self) -> bool:
        """Validate the system maintenance identity."""
        if not self.identity_token:
            return False
        
        # Basic token validation - in production, use proper JWT or secure token validation
        # For now, check token format and expiration
        try:
            # Token format: fabric4l-maintenance:<timestamp>:<signature>
            parts = self.identity_token.split(":")
            if len(parts) != 3 or parts[0] != "fabric4l-maintenance":
                return False
            
            timestamp_str = parts[1]
            timestamp = int(timestamp_str)
            
            # Check token age (24 hours)
            now = int(datetime.now(UTC).timestamp())
            # Reject tokens from the future and tokens at or past the expiry boundary
            if timestamp > now or now - timestamp >= 86400:  # 24 hours
                return False
                
            return True
            
        except (ValueError, IndexError):
            return False
    
    def authorize_operation(self, operation: str, tenant_id: str | None = None) -> bool:
        """
        Authorize a system maintenance operation.
        
        Critical security checks:
        1. Token type must be MAINTENANCE (not TENANT)
        2. Token must not be expired
        3. Operation must be in allowlist
        4. System-wide ops require specific allowlist
        
        Args:
            operation: Operation name from MaintenanceOperation enum
            tenant_id: Target tenant ID (None for system-wide operations)
            
        Returns:
            True if operation is authorized
            
        Raises:
            SystemMaintenanceAuthorizationError: If authorization fails
        """
        # CRITICAL: Detect and reject token confusion attacks
        token_type = detect_token_type(self.identity_token)
        
        if token_type == TokenType.TENANT:
            # Tenant tokens CANNOT be used as maintenance tokens
            # This prevents privilege escalation attacks
            raise SystemMaintenanceAuthorizationError(
                "Tenant token cannot be used as maintenance token. "
                "System operations require a valid maintenance identity.",
                operation=operation
            )
        
        if token_type == TokenType.UNKNOWN:
            raise SystemMaintenanceAuthorizationError(
                "Unrecognized token type. System operations require a valid maintenance identity.",
                operation=operation
            )
        
        if token_type == TokenType.INVALID:
            raise SystemMaintenanceAuthorizationError(
                "Invalid or missing system maintenance identity",
                operation=operation
            )
        
        # Validate operation is allowlisted
        if not MaintenanceOperation.has_value(operation):
            raise SystemMaintenanceAuthorizationError(
                f"Operation '{operation}' is not in maintenance allowlist",
                operation=operation
            )
        
        # Validate system identity (checks expiration)
        if not self.is_valid():
            raise SystemMaintenanceAuthorizationError(
                "Expired or invalid system maintenance identity",
                operation=operation
            )
        
        # System-wide operations require additional validation
        if tenant_id is None:
            # Only certain operations are allowed system-wide
            system_only_ops = {
                MaintenanceOperation.SYSTEM_HEALTH_CHECK.value,
                MaintenanceOperation.INDEX_REBUILD.value,
                MaintenanceOperation.AUDIT_EXPORT.value,
            }
            
            if operation not in system_only_ops:
                raise SystemMaintenanceAuthorizationError(
                    f"Operation '{operation}' requires tenant_id for tenant-iterated execution",
                    operation=operation
                )
        
        return True


# Global maintenance identity instance
_maintenance_identity = SystemMaintenanceIdentity()


def get_maintenance_identity() -> SystemMaintenanceIdentity:
    """Get the global system maintenance identity."""
    return _maintenance_identity


def authorize_maintenance_operation(operation: str, tenant_id: str | None = None) -> None:
    """
    Authorize a system maintenance operation.
    
    Args:
        operation: Operation name from MaintenanceOperation enum
        tenant_id: Target tenant ID (None for system-wide operations)
        
    Raises:
        SystemMaintenanceAuthorizationError: If authorization fails
    """
    identity = get_maintenance_identity()
    identity.authorize_operation(operation, tenant_id)
    
    logger.info(
        "System maintenance operation authorized",
        operation=operation,
        tenant_id=tenant_id,
        system_identity=identity.identity_name
    )


@contextmanager
def maintenance_audit_log(operation: str, tenant_id: str | None = None) -> Generator[MaintenanceAuditRecord, None, None]:
    """
    Context manager for maintenance operation audit logging.
    
    Args:
        operation: Operation name
        tenant_id: Target tenant ID (None for system-wide operations)
        
    Yields:
        MaintenanceAuditRecord for updating with operation details
    """
    # Authorize the operation first
    authorize_maintenance_operation(operation, tenant_id)
    
    # Create audit record
    record = MaintenanceAuditRecord(
        operation=operation,
        tenant_id=tenant_id,
        system_identity=get_maintenance_identity().identity_name,
        started_at=datetime.now(UTC)
    )
    
    logger.info(
        "System maintenance operation started",
        operation=operation,
        tenant_id=tenant_id,
        audit_id=f"{operation}_{record.timestamp.isoformat()}"
    )
    
    try:
        yield record
        record.success = True
        record.completed_at = datetime.now(UTC)
        
        logger.info(
            "System maintenance operation completed",
            operation=operation,
            tenant_id=tenant_id,
            rows_affected=record.rows_affected,
            duration_seconds=(record.completed_at - record.started_at).total_seconds() if record.started_at else 0.0
        )
        
    except Exception as e:
        record.success = False
        record.error_message = sanitize_log_error(e)
        record.completed_at = datetime.now(UTC)
        
        logger.error(
            "System maintenance operation failed",
            operation=operation,
            tenant_id=tenant_id,
            error=record.error_message,
            duration_seconds=(record.completed_at - record.started_at).total_seconds() if record.started_at else 0.0
        )
        raise
    
    finally:
        # Log audit record (in production, send to audit service)
        audit_data = record.to_dict()
        logger.info("System maintenance audit record", **audit_data)


@contextmanager
def system_maintenance_context() -> Generator[None, None, None]:
    """
    Context manager for system maintenance operations.
    
    This provides a system-level database context for operations that
    need to access global tables without tenant isolation.
    
    Usage:
        with system_maintenance_context():
            # Global table operations here
            pass
    """
    # Validate system identity
    identity = get_maintenance_identity()
    if not identity.is_valid():
        raise SystemMaintenanceAuthorizationError(
            "System maintenance context requires valid system identity"
        )
    
    logger.info(
        "System maintenance context established",
        system_identity=identity.identity_name
    )
    
    try:
        yield
    finally:
        logger.info(
            "System maintenance context released",
            system_identity=identity.identity_name
        )


def is_system_maintenance_request(headers: dict[str, str]) -> bool:
    """
    Check if a request is from system maintenance.
    
    Args:
        headers: Request headers
        
    Returns:
        True if request is from system maintenance
    """
    # Check for system maintenance header
    maintenance_header = headers.get("X-Fabric4L-Maintenance")
    if not maintenance_header:
        return False
    
    # Validate header format and token
    identity = get_maintenance_identity()
    return maintenance_header == identity.identity_token


def require_system_maintenance(headers: dict[str, str]) -> None:
    """
    Require system maintenance authorization for a request.
    
    Args:
        headers: Request headers
        
    Raises:
        SystemMaintenanceAuthorizationError: If not authorized
    """
    if not is_system_maintenance_request(headers):
        raise SystemMaintenanceAuthorizationError(
            "Request requires system maintenance authorization"
        )
