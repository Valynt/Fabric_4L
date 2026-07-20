# Audit Events Catalog — Fabric 4L

## Status: PRODUCTION-READY
## Version: 1.2.0
## Owner: Security Engineering
## Last Updated: 2024-01

---

## 1. Overview

This document defines the complete catalog of auditable events in Fabric 4L. Every event is:

- **Structured**: JSON format with mandatory fields (see §4)
- **Immutable**: Write-once, append-only storage
- **Searchable**: Indexed by tenant_id, user_id, event_type, timestamp
- **Compliant**: Covers GDPR Art. 30 (Records of processing), SOC 2 CC7.2, and ISO 27001 A.12.4

---

## 2. Event Taxonomy

Events are organized into categories following the pattern `<category>.<action>`.

### 2.1 Authentication Events (`auth.*`)

| Event | Severity | GDPR Relevance | Description |
|-------|----------|----------------|-------------|
| `auth.login_success` | INFO | Yes | Successful user login |
| `auth.login_failure` | WARN | Yes | Failed login attempt (includes reason) |
| `auth.logout` | INFO | Yes | User-initiated logout |
| `auth.session_created` | INFO | Yes | New session token issued |
| `auth.session_revoked` | INFO | Yes | Session explicitly invalidated |
| `auth.session_expired` | INFO | Yes | Session timed out |
| `auth.mfa_enabled` | INFO | Yes | MFA activated for account |
| `auth.mfa_disabled` | WARN | Yes | MFA deactivated (requires justification) |
| `auth.mfa_challenge_issued` | INFO | Yes | MFA prompt sent to user |
| `auth.mfa_challenge_failed` | WARN | Yes | Incorrect MFA code submitted |
| `auth.password_changed` | INFO | Yes | User changed password |
| `auth.password_reset_requested` | INFO | Yes | Password reset flow initiated |
| `auth.password_reset_completed` | INFO | Yes | Password reset successfully completed |
| `auth.api_key_created` | INFO | Yes | New API key generated |
| `auth.api_key_revoked` | INFO | Yes | API key invalidated |
| `auth.impersonation_started` | WARN | Yes | Admin began user impersonation |
| `auth.impersonation_ended` | INFO | Yes | Admin ended impersonation |

### 2.2 Tenant Data Access Events (`tenant.*`)

| Event | Severity | GDPR Relevance | Description |
|-------|----------|----------------|-------------|
| `tenant.data_access` | INFO | Yes | User accessed tenant data |
| `tenant.data_export` | INFO | Yes | Data export initiated (GDPR Art. 20) |
| `tenant.data_export_completed` | INFO | Yes | Data export finished |
| `tenant.data_delete` | WARN | Yes | Deletion request (GDPR Art. 17) |
| `tenant.data_delete_completed` | WARN | Yes | Deletion finished |
| `tenant.data_modified` | INFO | Yes | Data modification operation |
| `tenant.data_query` | INFO | Yes | Search/query executed |
| `tenant.user_invited` | INFO | Yes | New user invited to tenant |
| `tenant.user_removed` | INFO | Yes | User removed from tenant |
| `tenant.user_role_changed` | WARN | Yes | User role/permissions modified |
| `tenant.settings_changed` | INFO | Yes | Tenant configuration updated |
| `tenant.billing_updated` | INFO | No | Billing information changed |

### 2.3 Administrative Events (`admin.*`)

| Event | Severity | GDPR Relevance | Description |
|-------|----------|----------------|-------------|
| `admin.user_created` | INFO | Yes | New user account created |
| `admin.user_deleted` | WARN | Yes | User account permanently deleted |
| `admin.user_suspended` | WARN | Yes | User account suspended |
| `admin.user_reactivated` | INFO | Yes | Suspended user reactivated |
| `admin.role_changed` | WARN | Yes | Role definition modified |
| `admin.permission_granted` | WARN | Yes | Additional permissions assigned |
| `admin.permission_revoked` | INFO | Yes | Permissions removed |
| `admin.tenant_created` | INFO | Yes | New tenant provisioned |
| `admin.tenant_suspended` | WARN | Yes | Tenant access suspended |
| `admin.tenant_reactivated` | INFO | Yes | Suspended tenant reactivated |
| `admin.tenant_deleted` | CRITICAL | Yes | Complete tenant erasure (GDPR) |
| `admin.audit_log_accessed` | INFO | Yes | Admin viewed audit logs |
| `admin.config_changed` | WARN | Yes | System configuration modified |
| `admin.feature_flag_toggled` | INFO | No | Feature flag state changed |

### 2.4 System Events (`system.*`)

| Event | Severity | GDPR Relevance | Description |
|-------|----------|----------------|-------------|
| `system.deployment_started` | INFO | No | Deployment pipeline initiated |
| `system.deployment_completed` | INFO | No | Deployment successful |
| `system.deployment_failed` | ERROR | No | Deployment error |
| `system.deployment_rolled_back` | WARN | No | Rollback executed |
| `system.backup_created` | INFO | Yes | Data backup completed |
| `system.backup_restored` | WARN | Yes | Backup restoration executed |
| `system.migration_applied` | INFO | No | Database migration run |
| `system.migration_rolled_back` | WARN | No | Migration reverted |
| `system.scale_up` | INFO | No | Auto-scaling added instances |
| `system.scale_down` | INFO | No | Auto-scaling removed instances |
| `system.config_reloaded` | INFO | No | Runtime config refresh |
| `system.certificate_rotated` | INFO | No | TLS certificate renewed |

### 2.5 Security Events (`security.*`)

| Event | Severity | GDPR Relevance | Description |
|-------|----------|----------------|-------------|
| `security.policy_violation` | WARN | Yes | Security policy breach detected |
| `security.rate_limit_triggered` | WARN | Yes | Rate limit exceeded |
| `security.unauthorized_access_attempt` | ERROR | Yes | Forbidden resource access attempt |
| `security.suspicious_activity` | WARN | Yes | Anomaly detection alert |
| `security.ip_blocked` | WARN | No | IP address blacklisted |
| `security.ip_unblocked` | INFO | No | IP address removed from blacklist |
| `security.dlp_triggered` | CRITICAL | Yes | Data loss prevention rule matched |
| `security.data_exfiltration_detected` | CRITICAL | Yes | Potential data exfiltration |
| `security.vulnerability_detected` | ERROR | No | New CVE found in dependency |
| `security.pentest_initiated` | INFO | No | Penetration test started |
| `security.pentest_completed` | INFO | No | Penetration test finished |
| `security.incident_declared` | CRITICAL | Yes | Security incident opened |
| `security.incident_resolved` | INFO | Yes | Security incident closed |
| `security.gdpr_deletion_initiated` | CRITICAL | Yes | GDPR deletion started |
| `security.gdpr_deletion_completed` | CRITICAL | Yes | GDPR deletion finished |
| `security.gdpr_export_initiated` | INFO | Yes | GDPR data export started |

### 2.6 API Events (`api.*`)

| Event | Severity | GDPR Relevance | Description |
|-------|----------|----------------|-------------|
| `api.request` | DEBUG | No | API request received |
| `api.response` | DEBUG | No | API response sent |
| `api.error` | ERROR | No | Unhandled API exception |
| `api.timeout` | WARN | No | Request timeout |
| `api.validation_failed` | INFO | No | Input validation error |

---

## 3. Event Catalog (Python Constants)

```python
# services/shared/src/value_fabric/shared/audit_events.py
"""
Canonical audit event types for Fabric 4L.

Usage:
    from value_fabric.shared.audit_events import AUDIT_EVENTS, is_valid_event
    log_audit_event(event_type=AUDIT_EVENTS["auth.login_success"], ...)
"""

from enum import Enum
from typing import Dict, Set


class AuditEventCategory(str, Enum):
    AUTH = "auth"
    TENANT = "tenant"
    ADMIN = "admin"
    SYSTEM = "system"
    SECURITY = "security"
    API = "api"


# Full event catalog as typed constants
class AuditEvents:
    """Namespace for all auditable event type strings."""

    # --- Authentication ---
    AUTH_LOGIN_SUCCESS = "auth.login_success"
    AUTH_LOGIN_FAILURE = "auth.login_failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_SESSION_CREATED = "auth.session_created"
    AUTH_SESSION_REVOKED = "auth.session_revoked"
    AUTH_SESSION_EXPIRED = "auth.session_expired"
    AUTH_MFA_ENABLED = "auth.mfa_enabled"
    AUTH_MFA_DISABLED = "auth.mfa_disabled"
    AUTH_MFA_CHALLENGE_ISSUED = "auth.mfa_challenge_issued"
    AUTH_MFA_CHALLENGE_FAILED = "auth.mfa_challenge_failed"
    AUTH_PASSWORD_CHANGED = "auth.password_changed"
    AUTH_PASSWORD_RESET_REQUESTED = "auth.password_reset_requested"
    AUTH_PASSWORD_RESET_COMPLETED = "auth.password_reset_completed"
    AUTH_API_KEY_CREATED = "auth.api_key_created"
    AUTH_API_KEY_REVOKED = "auth.api_key_revoked"
    AUTH_IMPERSONATION_STARTED = "auth.impersonation_started"
    AUTH_IMPERSONATION_ENDED = "auth.impersonation_ended"

    # --- Tenant Data ---
    TENANT_DATA_ACCESS = "tenant.data_access"
    TENANT_DATA_EXPORT = "tenant.data_export"
    TENANT_DATA_EXPORT_COMPLETED = "tenant.data_export_completed"
    TENANT_DATA_DELETE = "tenant.data_delete"
    TENANT_DATA_DELETE_COMPLETED = "tenant.data_delete_completed"
    TENANT_DATA_MODIFIED = "tenant.data_modified"
    TENANT_DATA_QUERY = "tenant.data_query"
    TENANT_USER_INVITED = "tenant.user_invited"
    TENANT_USER_REMOVED = "tenant.user_removed"
    TENANT_USER_ROLE_CHANGED = "tenant.user_role_changed"
    TENANT_SETTINGS_CHANGED = "tenant.settings_changed"
    TENANT_BILLING_UPDATED = "tenant.billing_updated"

    # --- Admin ---
    ADMIN_USER_CREATED = "admin.user_created"
    ADMIN_USER_DELETED = "admin.user_deleted"
    ADMIN_USER_SUSPENDED = "admin.user_suspended"
    ADMIN_USER_REACTIVATED = "admin.user_reactivated"
    ADMIN_ROLE_CHANGED = "admin.role_changed"
    ADMIN_PERMISSION_GRANTED = "admin.permission_granted"
    ADMIN_PERMISSION_REVOKED = "admin.permission_revoked"
    ADMIN_TENANT_CREATED = "admin.tenant_created"
    ADMIN_TENANT_SUSPENDED = "admin.tenant_suspended"
    ADMIN_TENANT_REACTIVATED = "admin.tenant_reactivated"
    ADMIN_TENANT_DELETED = "admin.tenant_deleted"
    ADMIN_AUDIT_LOG_ACCESSED = "admin.audit_log_accessed"
    ADMIN_CONFIG_CHANGED = "admin.config_changed"
    ADMIN_FEATURE_FLAG_TOGGLED = "admin.feature_flag_toggled"

    # --- System ---
    SYSTEM_DEPLOYMENT_STARTED = "system.deployment_started"
    SYSTEM_DEPLOYMENT_COMPLETED = "system.deployment_completed"
    SYSTEM_DEPLOYMENT_FAILED = "system.deployment_failed"
    SYSTEM_DEPLOYMENT_ROLLED_BACK = "system.deployment_rolled_back"
    SYSTEM_BACKUP_CREATED = "system.backup_created"
    SYSTEM_BACKUP_RESTORED = "system.backup_restored"
    SYSTEM_MIGRATION_APPLIED = "system.migration_applied"
    SYSTEM_MIGRATION_ROLLED_BACK = "system.migration_rolled_back"
    SYSTEM_SCALE_UP = "system.scale_up"
    SYSTEM_SCALE_DOWN = "system.scale_down"
    SYSTEM_CONFIG_RELOADED = "system.config_reloaded"
    SYSTEM_CERTIFICATE_ROTATED = "system.certificate_rotated"

    # --- Security ---
    SECURITY_POLICY_VIOLATION = "security.policy_violation"
    SECURITY_RATE_LIMIT_TRIGGERED = "security.rate_limit_triggered"
    SECURITY_UNAUTHORIZED_ACCESS_ATTEMPT = "security.unauthorized_access_attempt"
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    SECURITY_IP_BLOCKED = "security.ip_blocked"
    SECURITY_IP_UNBLOCKED = "security.ip_unblocked"
    SECURITY_DLP_TRIGGERED = "security.dlp_triggered"
    SECURITY_DATA_EXFILTRATION_DETECTED = "security.data_exfiltration_detected"
    SECURITY_VULNERABILITY_DETECTED = "security.vulnerability_detected"
    SECURITY_PENTEST_INITIATED = "security.pentest_initiated"
    SECURITY_PENTEST_COMPLETED = "security.pentest_completed"
    SECURITY_INCIDENT_DECLARED = "security.incident_declared"
    SECURITY_INCIDENT_RESOLVED = "security.incident_resolved"
    SECURITY_GDPR_DELETION_INITIATED = "security.gdpr_deletion_initiated"
    SECURITY_GDPR_DELETION_COMPLETED = "security.gdpr_deletion_completed"
    SECURITY_GDPR_EXPORT_INITIATED = "security.gdpr_export_initiated"

    # --- API ---
    API_REQUEST = "api.request"
    API_RESPONSE = "api.response"
    API_ERROR = "api.error"
    API_TIMEOUT = "api.timeout"
    API_VALIDATION_FAILED = "api.validation_failed"

    @classmethod
    def all_events(cls) -> Set[str]:
        """Return the set of all valid event type strings."""
        return {
            value for name, value in cls.__dict__.items()
            if not name.startswith("_") and isinstance(value, str)
        }

    @classmethod
    def is_valid(cls, event_type: str) -> bool:
        """Validate an event type string against the catalog."""
        return event_type in cls.all_events()

    @classmethod
    def events_for_category(cls, category: AuditEventCategory) -> Set[str]:
        """Return all event types for a given category."""
        prefix = f"{category.value}."
        return {e for e in cls.all_events() if e.startswith(prefix)}


# Convenience flat list for quick reference
AUDIT_EVENTS = sorted(AuditEvents.all_events())

GDPR_RELEVANT_EVENTS = sorted([
    e for e in AUDIT_EVENTS
    if e.startswith(("auth.", "tenant.", "admin.", "security.gdpr"))
])

SEVERITY_MAP: Dict[str, str] = {
    # Authentication
    AuditEvents.AUTH_LOGIN_SUCCESS: "INFO",
    AuditEvents.AUTH_LOGIN_FAILURE: "WARN",
    AuditEvents.AUTH_LOGOUT: "INFO",
    AuditEvents.AUTH_SESSION_CREATED: "INFO",
    AuditEvents.AUTH_SESSION_REVOKED: "INFO",
    AuditEvents.AUTH_SESSION_EXPIRED: "INFO",
    AuditEvents.AUTH_MFA_ENABLED: "INFO",
    AuditEvents.AUTH_MFA_DISABLED: "WARN",
    AuditEvents.AUTH_MFA_CHALLENGE_ISSUED: "INFO",
    AuditEvents.AUTH_MFA_CHALLENGE_FAILED: "WARN",
    AuditEvents.AUTH_PASSWORD_CHANGED: "INFO",
    AuditEvents.AUTH_PASSWORD_RESET_REQUESTED: "INFO",
    AuditEvents.AUTH_PASSWORD_RESET_COMPLETED: "INFO",
    AuditEvents.AUTH_API_KEY_CREATED: "INFO",
    AuditEvents.AUTH_API_KEY_REVOKED: "INFO",
    AuditEvents.AUTH_IMPERSONATION_STARTED: "WARN",
    AuditEvents.AUTH_IMPERSONATION_ENDED: "INFO",
    # Tenant
    AuditEvents.TENANT_DATA_ACCESS: "INFO",
    AuditEvents.TENANT_DATA_EXPORT: "INFO",
    AuditEvents.TENANT_DATA_EXPORT_COMPLETED: "INFO",
    AuditEvents.TENANT_DATA_DELETE: "WARN",
    AuditEvents.TENANT_DATA_DELETE_COMPLETED: "WARN",
    AuditEvents.TENANT_DATA_MODIFIED: "INFO",
    AuditEvents.TENANT_DATA_QUERY: "INFO",
    AuditEvents.TENANT_USER_INVITED: "INFO",
    AuditEvents.TENANT_USER_REMOVED: "INFO",
    AuditEvents.TENANT_USER_ROLE_CHANGED: "WARN",
    AuditEvents.TENANT_SETTINGS_CHANGED: "INFO",
    AuditEvents.TENANT_BILLING_UPDATED: "INFO",
    # Admin
    AuditEvents.ADMIN_USER_CREATED: "INFO",
    AuditEvents.ADMIN_USER_DELETED: "WARN",
    AuditEvents.ADMIN_USER_SUSPENDED: "WARN",
    AuditEvents.ADMIN_USER_REACTIVATED: "INFO",
    AuditEvents.ADMIN_ROLE_CHANGED: "WARN",
    AuditEvents.ADMIN_PERMISSION_GRANTED: "WARN",
    AuditEvents.ADMIN_PERMISSION_REVOKED: "INFO",
    AuditEvents.ADMIN_TENANT_CREATED: "INFO",
    AuditEvents.ADMIN_TENANT_SUSPENDED: "WARN",
    AuditEvents.ADMIN_TENANT_REACTIVATED: "INFO",
    AuditEvents.ADMIN_TENANT_DELETED: "CRITICAL",
    AuditEvents.ADMIN_AUDIT_LOG_ACCESSED: "INFO",
    AuditEvents.ADMIN_CONFIG_CHANGED: "WARN",
    AuditEvents.ADMIN_FEATURE_FLAG_TOGGLED: "INFO",
    # System
    AuditEvents.SYSTEM_DEPLOYMENT_STARTED: "INFO",
    AuditEvents.SYSTEM_DEPLOYMENT_COMPLETED: "INFO",
    AuditEvents.SYSTEM_DEPLOYMENT_FAILED: "ERROR",
    AuditEvents.SYSTEM_DEPLOYMENT_ROLLED_BACK: "WARN",
    AuditEvents.SYSTEM_BACKUP_CREATED: "INFO",
    AuditEvents.SYSTEM_BACKUP_RESTORED: "WARN",
    AuditEvents.SYSTEM_MIGRATION_APPLIED: "INFO",
    AuditEvents.SYSTEM_MIGRATION_ROLLED_BACK: "WARN",
    AuditEvents.SYSTEM_SCALE_UP: "INFO",
    AuditEvents.SYSTEM_SCALE_DOWN: "INFO",
    AuditEvents.SYSTEM_CONFIG_RELOADED: "INFO",
    AuditEvents.SYSTEM_CERTIFICATE_ROTATED: "INFO",
    # Security
    AuditEvents.SECURITY_POLICY_VIOLATION: "WARN",
    AuditEvents.SECURITY_RATE_LIMIT_TRIGGERED: "WARN",
    AuditEvents.SECURITY_UNAUTHORIZED_ACCESS_ATTEMPT: "ERROR",
    AuditEvents.SECURITY_SUSPICIOUS_ACTIVITY: "WARN",
    AuditEvents.SECURITY_IP_BLOCKED: "WARN",
    AuditEvents.SECURITY_IP_UNBLOCKED: "INFO",
    AuditEvents.SECURITY_DLP_TRIGGERED: "CRITICAL",
    AuditEvents.SECURITY_DATA_EXFILTRATION_DETECTED: "CRITICAL",
    AuditEvents.SECURITY_VULNERABILITY_DETECTED: "ERROR",
    AuditEvents.SECURITY_PENTEST_INITIATED: "INFO",
    AuditEvents.SECURITY_PENTEST_COMPLETED: "INFO",
    AuditEvents.SECURITY_INCIDENT_DECLARED: "CRITICAL",
    AuditEvents.SECURITY_INCIDENT_RESOLVED: "INFO",
    AuditEvents.SECURITY_GDPR_DELETION_INITIATED: "CRITICAL",
    AuditEvents.SECURITY_GDPR_DELETION_COMPLETED: "CRITICAL",
    AuditEvents.SECURITY_GDPR_EXPORT_INITIATED: "INFO",
    # API
    AuditEvents.API_REQUEST: "DEBUG",
    AuditEvents.API_RESPONSE: "DEBUG",
    AuditEvents.API_ERROR: "ERROR",
    AuditEvents.API_TIMEOUT: "WARN",
    AuditEvents.API_VALIDATION_FAILED: "INFO",
}
```

---

## 4. Event Schema (Mandatory Fields)

Every audit event record MUST include the following fields:

```json
{
  "event_id": "evt_01HN3J8KQVM7R28D1E1VZCXQY5",
  "event_type": "auth.login_success",
  "timestamp": "2024-01-15T09:23:47.123Z",
  "severity": "INFO",
  "tenant_id": "tenant_abc123",
  "user_id": "user_xyz789",
  "session_id": "sess_pqr456",
  "request_id": "req_mno012",
  "actor_ip": "198.51.100.42",
  "actor_user_agent": "Mozilla/5.0 ...",
  "resource_type": "document",
  "resource_id": "doc_456",
  "action": "read",
  "outcome": "success",
  "details": {
    "custom_field": "additional context"
  },
  "gdpr_relevant": true,
  "retention_class": "hot",
  "hash_chain": "sha256:abc123..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | ULID | Yes | Lexicographically sortable unique identifier |
| `event_type` | string | Yes | Must match a value from AuditEvents catalog |
| `timestamp` | ISO 8601 | Yes | Event occurrence time (UTC) |
| `severity` | enum | Yes | DEBUG, INFO, WARN, ERROR, CRITICAL |
| `tenant_id` | string | Yes* | Tenant scope (*system events use "system") |
| `user_id` | string | Yes* | Acting user (*system events use "system") |
| `session_id` | string | No | Web session identifier |
| `request_id` | string | No | HTTP request correlation ID |
| `actor_ip` | IP address | Yes | Originating IP (hashed for GDPR if PII) |
| `actor_user_agent` | string | No | Browser/client identifier |
| `resource_type` | string | No | Category of affected resource |
| `resource_id` | string | No | Specific resource identifier |
| `action` | string | No | CRUD action verb |
| `outcome` | string | Yes | success, failure, denied, error |
| `details` | JSON object | No | Event-specific payload |
| `gdpr_relevant` | boolean | Yes | Whether event is subject to GDPR retention |
| `retention_class` | enum | Yes | hot (90d), warm (1y), cold (7y) |
| `hash_chain` | string | Yes | SHA-256 chain linking to previous event |

---

## 5. Retention Policy

| Class | Duration | Storage | Query Latency | Compliance Driver |
|-------|----------|---------|---------------|-------------------|
| **Hot** | 90 days | PostgreSQL + Redis | < 100ms | SOC 2 CC7.2, Daily ops |
| **Warm** | 1 year | S3 (Parquet) + Athena | < 5s | GDPR Art. 30, Annual audit |
| **Cold** | 7 years | Glacier Deep Archive | Hours | Legal hold, Regulatory |

### Retention Class Assignment

```python
RETENTION_ASSIGNMENT = {
    # Hot: operational security
    "security.policy_violation": "hot",
    "security.unauthorized_access_attempt": "hot",
    "auth.login_failure": "hot",
    "auth.mfa_disabled": "hot",
    "admin.user_deleted": "hot",
    "admin.tenant_deleted": "hot",

    # Warm: compliance reporting
    "tenant.data_export": "warm",
    "tenant.data_delete": "warm",
    "security.gdpr_deletion_initiated": "warm",

    # Cold: long-term legal
    "admin.audit_log_accessed": "cold",
    "security.incident_declared": "cold",
}
# Default: hot
```

---

## 6. Compliance Mapping

| Regulation | Article/Control | Covered Events |
|------------|----------------|----------------|
| GDPR Art. 17 | Right to erasure | `tenant.data_delete`, `security.gdpr_deletion_*` |
| GDPR Art. 20 | Data portability | `tenant.data_export*` |
| GDPR Art. 30 | Records of processing | All `tenant.*`, `auth.*` |
| GDPR Art. 32 | Security | All `security.*`, `auth.mfa_*` |
| SOC 2 CC7.2 | System monitoring | All `system.*`, `security.*` |
| ISO 27001 A.12.4 | Logging | Entire catalog |
| CCPA 1798.105 | Deletion rights | `tenant.data_delete*` |

---

## 7. Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2024-01-15 | 1.2.0 | Added `security.gdpr_export_initiated`, `api.validation_failed` |
| 2024-01-01 | 1.1.0 | Added `auth.impersonation_*`, `admin.audit_log_accessed` |
| 2023-12-01 | 1.0.0 | Initial catalog (72 event types) |
