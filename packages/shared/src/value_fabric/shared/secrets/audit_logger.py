#!/usr/bin/env python3
"""
Secret Access Audit Logger

Provides comprehensive audit logging for secret access, rotation, and configuration changes.
Integrates with the shared audit system for compliance and security monitoring.

Usage:
    from value_fabric.shared.secrets.audit_logger import SecretAuditLogger
    
    logger = SecretAuditLogger()
    logger.log_secret_access(
        secret_type="database",
        secret_name="postgres-credentials",
        action="read",
        user="app-user",
        source_ip="10.0.1.5"
    )
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from dataclasses import dataclass, asdict

# Try to import shared audit components
try:
    from value_fabric.shared.audit import AuditEvent, AuditLogger
    SHARED_AUDIT_AVAILABLE = True
except ImportError:
    SHARED_AUDIT_AVAILABLE = False


class SecretAction(Enum):
    """Types of secret actions that can be audited."""
    READ = "read"
    ROTATE = "rotate"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REVOKE = "revoke"
    ACCESS_DENIED = "access_denied"


class SecretType(Enum):
    """Types of secrets managed in the system."""
    DATABASE = "database"
    API_KEY = "api_key"
    JWT_SIGNING = "jwt_signing"
    HMAC_KEY = "hmac_key"
    LLM_API_KEY = "llm_api_key"
    REDIS = "redis"
    NEO4J = "neo4j"
    VAULT_TOKEN = "vault_token"
    INFISICAL_TOKEN = "infisical_token"


@dataclass
class SecretAuditEvent:
    """Structured secret audit event."""
    timestamp: str
    event_type: str
    secret_type: str
    secret_name: str
    secret_hash: str  # Hashed secret identifier, not the secret itself
    action: str
    actor: str
    actor_type: str  # 'service', 'user', 'system', 'pipeline'
    source_ip: Optional[str] = None
    environment: str = "production"
    correlation_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class SecretAuditLogger:
    """
    Audit logger for secret management operations.
    
    Logs all secret access, rotation, and configuration changes.
    Supports both structured logging and integration with shared audit system.
    """
    
    def __init__(
        self,
        environment: Optional[str] = None,
        enable_file_output: bool = True,
        log_file_path: Optional[str] = None
    ):
        self.environment = environment or os.getenv("ENVIRONMENT", "production")
        self.enable_file_output = enable_file_output
        
        # Validate and sanitize log file path to prevent path traversal
        self.log_file_path = self._validate_and_sanitize_path(
            log_file_path or os.getenv("SECRET_AUDIT_LOG_PATH", "/var/log/services/secret-audit.log")
        )
        
        # Setup logger
        self.logger = logging.getLogger("secret_audit")
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # Try to use shared audit logger
        self.shared_audit = None
        if SHARED_AUDIT_AVAILABLE:
            try:
                self.shared_audit = AuditLogger()
            except Exception as e:
                self.logger.warning(f"Failed to initialize shared audit: {e}")
    
    def _validate_and_sanitize_path(self, path: str) -> str:
        """Validate path is within allowed base directory to prevent path traversal.
        
        Args:
            path: The requested log file path
            
        Returns:
            The sanitized path
            
        Raises:
            ValueError: If path attempts directory traversal outside base directory
        """
        # Normalize the path to resolve any .. sequences
        normalized = os.path.abspath(os.path.normpath(path))
        
        # Define allowed base directories
        allowed_bases = [
            "/var/log/services",
            "/tmp",
            os.path.expanduser("~/.services/logs"),
        ]
        
        # Check if normalized path starts with any allowed base
        for base in allowed_bases:
            if normalized.startswith(os.path.abspath(base)):
                return normalized
        
        # If path is relative, make it absolute under default base
        if not path.startswith("/"):
            default_base = "/var/log/services"
            return os.path.abspath(os.path.join(default_base, path))
        
        # Path is outside allowed directories - reject it
        raise ValueError(
            f"Log path '{path}' is outside allowed directories: {allowed_bases}"
        )

    def _hash_secret_identifier(self, secret_name: str) -> str:
        """
        Create a hash of the secret identifier for audit logs.
        Never log actual secret values.
        """
        return hashlib.sha256(secret_name.encode()).hexdigest()[:16]
    
    def _write_to_audit_file(self, event: SecretAuditEvent) -> None:
        """Write audit event to dedicated audit log file."""
        if not self.enable_file_output:
            return
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
            
            # Append to audit log
            with open(self.log_file_path, 'a') as f:
                f.write(event.to_json() + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write to audit file: {e}")
    
    def _send_to_shared_audit(self, event: SecretAuditEvent) -> None:
        """Send event to shared audit system if available."""
        if not self.shared_audit:
            return
        
        try:
            audit_event = AuditEvent(
                timestamp=event.timestamp,
                event_type=f"secret_{event.action}",
                severity="INFO" if event.success else "ERROR",
                actor=event.actor,
                resource=event.secret_name,
                resource_type="secret",
                action=event.action,
                status="success" if event.success else "failure",
                details=event.metadata or {}
            )
            self.shared_audit.log(audit_event)
        except Exception as e:
            self.logger.warning(f"Failed to send to shared audit: {e}")
    
    def log_secret_access(
        self,
        secret_type: SecretType | str,
        secret_name: str,
        action: SecretAction | str,
        actor: str,
        actor_type: str = "service",
        source_ip: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> SecretAuditEvent:
        """
        Log a secret access event.
        
        Args:
            secret_type: Type of secret (database, api_key, etc.)
            secret_name: Name/identifier of the secret
            action: Action performed (read, rotate, etc.)
            actor: Who/what accessed the secret
            actor_type: Type of actor (service, user, system, pipeline)
            source_ip: IP address of the requester
            success: Whether the operation succeeded
            error_message: Error details if failed
            correlation_id: Trace/correlation ID
            metadata: Additional context
        
        Returns:
            The created audit event
        """
        # Convert enums if needed
        if isinstance(secret_type, SecretType):
            secret_type = secret_type.value
        if isinstance(action, SecretAction):
            action = action.value
        
        event = SecretAuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="secret_access",
            secret_type=secret_type,
            secret_name=secret_name,
            secret_hash=self._hash_secret_identifier(secret_name),
            action=action,
            actor=actor,
            actor_type=actor_type,
            source_ip=source_ip,
            environment=self.environment,
            correlation_id=correlation_id or os.getenv("CORRELATION_ID"),
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        
        # Log to standard logger
        log_level = logging.INFO if success else logging.WARNING
        self.logger.log(
            log_level,
            f"Secret {action}: type={secret_type}, name={secret_name}, actor={actor}, success={success}"
        )
        
        # Write to audit file
        self._write_to_audit_file(event)
        
        # Send to shared audit
        self._send_to_shared_audit(event)
        
        return event
    
    def log_secret_rotation(
        self,
        secret_type: SecretType | str,
        secret_name: str,
        rotated_by: str,
        rotation_reason: str = "scheduled",
        old_expiry: Optional[str] = None,
        new_expiry: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> SecretAuditEvent:
        """
        Log a secret rotation event.
        
        Args:
            secret_type: Type of secret rotated
            secret_name: Name of the secret
            rotated_by: Who/what triggered the rotation
            rotation_reason: Why rotation occurred (scheduled, emergency, etc.)
            old_expiry: Previous expiration timestamp
            new_expiry: New expiration timestamp
            correlation_id: Trace ID
            metadata: Additional context
        
        Returns:
            The created audit event
        """
        if isinstance(secret_type, SecretType):
            secret_type = secret_type.value
        
        metadata = metadata or {}
        metadata.update({
            "rotation_reason": rotation_reason,
            "old_expiry": old_expiry,
            "new_expiry": new_expiry
        })
        
        return self.log_secret_access(
            secret_type=secret_type,
            secret_name=secret_name,
            action=SecretAction.ROTATE,
            actor=rotated_by,
            actor_type="system" if "github-actions" in rotated_by else "user",
            correlation_id=correlation_id,
            metadata=metadata
        )
    
    def log_rotation_failure(
        self,
        secret_type: SecretType | str,
        secret_name: str,
        error: Exception,
        attempted_by: str,
        correlation_id: Optional[str] = None
    ) -> SecretAuditEvent:
        """Log a failed rotation attempt."""
        return self.log_secret_access(
            secret_type=secret_type,
            secret_name=secret_name,
            action=SecretAction.ROTATE,
            actor=attempted_by,
            success=False,
            error_message=f"{type(error).__name__}: rotation_failed",
            correlation_id=correlation_id
        )
    
    def get_recent_accesses(
        self,
        secret_name: Optional[str] = None,
        secret_type: Optional[str] = None,
        hours: int = 24
    ) -> list[SecretAuditEvent]:
        """
        Query recent secret access events.
        
        Note: This is a simplified implementation. In production,
        integrate with your log aggregation system (ELK, Splunk, etc.)
        """
        events = []
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        
        try:
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        event_time = datetime.fromisoformat(data['timestamp'])
                        if event_time.timestamp() < cutoff:
                            continue
                        
                        if secret_name and data.get('secret_name') != secret_name:
                            continue
                        if secret_type and data.get('secret_type') != secret_type:
                            continue
                        
                        events.append(SecretAuditEvent(**data))
                    except (json.JSONDecodeError, KeyError):
                        continue
        except FileNotFoundError:
            pass
        
        return events


# Convenience functions for common use cases
def audit_database_access(
    database_name: str,
    user: str,
    operation: str,
    source_ip: Optional[str] = None
) -> None:
    """Convenience function to log database credential access."""
    logger = SecretAuditLogger()
    logger.log_secret_access(
        secret_type=SecretType.DATABASE,
        secret_name=f"db-{database_name}",
        action=SecretAction.READ,
        actor=user,
        source_ip=source_ip,
        metadata={"operation": operation}
    )


def audit_api_key_usage(
    api_key_name: str,
    endpoint: str,
    client_id: str
) -> None:
    """Convenience function to log API key usage."""
    logger = SecretAuditLogger()
    logger.log_secret_access(
        secret_type=SecretType.API_KEY,
        secret_name=api_key_name,
        action=SecretAction.READ,
        actor=client_id,
        metadata={"endpoint": endpoint}
    )


def audit_rotation(
    secret_type: str,
    secret_name: str,
    rotated_by: str,
    reason: str = "scheduled"
) -> None:
    """Convenience function to log secret rotation."""
    logger = SecretAuditLogger()
    logger.log_secret_rotation(
        secret_type=secret_type,
        secret_name=secret_name,
        rotated_by=rotated_by,
        rotation_reason=reason
    )


if __name__ == "__main__":
    # Example usage
    logger = SecretAuditLogger(environment="test")
    
    # Log database access
    event = logger.log_secret_access(
        secret_type=SecretType.DATABASE,
        secret_name="postgres-app-credentials",
        action=SecretAction.READ,
        actor="layer1-ingestion",
        actor_type="service",
        source_ip="10.0.1.100",
        metadata={"operation": "connect", "pool_size": 10}
    )
    
    print(f"Logged event: {event.to_json()}")
    
    # Log rotation
    rotation_event = logger.log_secret_rotation(
        secret_type=SecretType.JWT_SIGNING,
        secret_name="jwt-secret",
        rotated_by="github-actions",
        rotation_reason="scheduled-90d",
        new_expiry="2024-07-15T00:00:00Z"
    )
    
    print(f"Logged rotation: {rotation_event.to_json()}")
