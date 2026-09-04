"""Stable denial reason codes and error types for the authorization facade.

External callers depend on the stable ``reason_code`` string and HTTP status.
Never expose stack traces, internal tokens, or raw policy-engine internals.
"""

from __future__ import annotations

import enum


class ReasonCode(str, enum.Enum):
    """Canonical denial reason codes (mirror policy bundle data).

    Kept stable so dashboards, audit analysis, and clients can rely on them.
    """

    UNCATALOGUED_ACTION = "UNCATALOGUED_ACTION"
    TENANT_MISMATCH = "TENANT_MISMATCH"
    PRINCIPAL_INACTIVE = "PRINCIPAL_INACTIVE"
    ROLE_MISSING = "ROLE_MISSING"
    RELATIONSHIP_MISSING = "RELATIONSHIP_MISSING"
    SELF_APPROVAL_FORBIDDEN = "SELF_APPROVAL_FORBIDDEN"
    APPROVAL_CEILING_EXCEEDED = "APPROVAL_CEILING_EXCEEDED"
    MODEL_VERSION_STALE = "MODEL_VERSION_STALE"
    RESOURCE_REVISION_CHANGED = "RESOURCE_REVISION_CHANGED"
    DISPUTE_OPEN = "DISPUTE_OPEN"
    VALIDATION_INCOMPLETE = "VALIDATION_INCOMPLETE"
    EXCEPTION_NOT_ACTIVATED = "EXCEPTION_NOT_ACTIVATED"
    EXCEPTION_EXPIRED = "EXCEPTION_EXPIRED"
    EXCEPTION_INVALID_TRANSITION = "EXCEPTION_INVALID_TRANSITION"
    EXCEPTION_OUT_OF_SCOPE = "EXCEPTION_OUT_OF_SCOPE"
    AGENT_ACTION_FORBIDDEN = "AGENT_ACTION_FORBIDDEN"
    PUBLISHER_SOD_VIOLATION = "PUBLISHER_SOD_VIOLATION"
    DEPLOYMENT_LOCK_VIOLATION = "DEPLOYMENT_LOCK_VIOLATION"
    CEILING_APPROVER_SOD_VIOLATION = "CEILING_APPROVER_SOD_VIOLATION"
    STATIC_SOD_VIOLATION = "STATIC_SOD_VIOLATION"
    DUAL_CONTROL_REQUIRED = "DUAL_CONTROL_REQUIRED"
    DELEGATION_INVALID = "DELEGATION_INVALID"
    DELEGATION_REVOKED = "DELEGATION_REVOKED"
    EXTERNAL_GRANT_REVOKED = "EXTERNAL_GRANT_REVOKED"
    GRANT_EXPIRED = "GRANT_EXPIRED"
    BREAK_GLASS_APPROVER_NOT_ELIGIBLE = "BREAK_GLASS_APPROVER_NOT_ELIGIBLE"
    REQUIREMENT_NOT_MET = "REQUIREMENT_NOT_MET"
    POLICY_INPUT_INVALID = "POLICY_INPUT_INVALID"
    PDP_UNAVAILABLE = "PDP_UNAVAILABLE"
    POLICY_BUNDLE_UNAVAILABLE = "POLICY_BUNDLE_UNAVAILABLE"
    DENIED_BY_DEFAULT = "DENIED_BY_DEFAULT"


# All valid reason codes (mirror bundle). CI gate keeps this aligned with the
# policy bundle's reason-code data so uncatalogued codes cannot be emitted.
REASON_CODES: frozenset[str] = frozenset(r.value for r in ReasonCode)


class AuthorizationError(Exception):
    """Base class for authorization control-plane errors."""

    reason_code: ReasonCode = ReasonCode.DENIED_BY_DEFAULT
    http_status: int = 403

    def __init__(
        self,
        message: str,
        *,
        action: str | None = None,
        details: dict | None = None,
    ) -> None:
        self.message = message
        self.action = action
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        payload: dict = {
            "error": self.reason_code.value,
            "reason_code": self.reason_code.value,
            "message": self.message,
        }
        if self.action:
            payload["action"] = self.action
        if self.details:
            payload["details"] = self.details
        return payload


class AuthorizationDeniedError(AuthorizationError):
    """Explicit policy denial. Maps to HTTP 403 by default."""

    reason_code: ReasonCode = ReasonCode.DENIED_BY_DEFAULT


class PDUnavailableError(AuthorizationError):
    """Policy decision point unreachable or policy bundle unavailable.

    Principle 10: authorization outages on protected writes must fail closed.
    Maps to HTTP 503 for distinguishing "denied for an operational reason"
    from "denied by policy", but the write is still refused.
    """

    reason_code: ReasonCode = ReasonCode.PDP_UNAVAILABLE
    http_status: int = 503


class PolicyBundleUnavailableError(PDUnavailableError):
    """The policy bundle could not be loaded or validated."""

    reason_code: ReasonCode = ReasonCode.POLICY_BUNDLE_UNAVAILABLE


class PermissionDeniedHTTP(Exception):
    """Adapter for layers whose error contract is a plain HTTPException.

    ``http_status`` defaults to 403 for policy denials and 503 for availability
    failures. Keeps external API surfaces consistent without leaking internals.
    """

    def __init__(self, status_code: int, detail: dict) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail.get("message", "denied"))


# Simple dict-based mapping helpers for layers without class ergonomics.
def reason_code_for_failure(reason_code: str) -> bool:
    """Return True if a raw reason code is one of the canonical codes."""
    return reason_code in REASON_CODES
