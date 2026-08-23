"""Error response models for standardized error handling across all layers."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(str, Enum):
    """Standardized error codes across all Value Fabric services."""

    # Authentication/Authorization errors (4xx)
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHORIZATION_POLICY_MISSING = "AUTHORIZATION_POLICY_MISSING"
    INSUFFICIENT_SCOPE = "INSUFFICIENT_SCOPE"
    TENANT_ISOLATION_ERROR = "TENANT_ISOLATION_ERROR"
    TENANT_SCOPE_MISMATCH = "TENANT_SCOPE_MISMATCH"
    TENANT_CONTEXT_MISMATCH = "TENANT_CONTEXT_MISMATCH"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    AUTH_TOKEN_MISSING = "auth.token_missing"
    AUTH_TOKEN_INVALID = "auth.token_invalid"
    AUTH_CLERK_TOKEN_INVALID = "auth.clerk_token_invalid"
    AUTH_CLERK_TOKEN_EXPIRED = "auth.clerk_token_expired"
    AUTH_CLERK_UNAUTHORIZED_PARTY = "auth.clerk_unauthorized_party"
    AUTH_TENANT_UNRESOLVED = "auth.tenant_unresolved"
    AUTH_USER_UNPROVISIONED = "auth.user_unprovisioned"
    AUTH_MEMBERSHIP_INACTIVE = "auth.membership_inactive"
    AUTH_MISCONFIGURED = "auth.misconfigured"
    AUTH_ENVELOPE_MISCONFIGURED = "auth.envelope_misconfigured"

    # Validation errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    WEBHOOK_INVALID_BODY = "auth.webhook_invalid_body"

    # Resource errors (4xx)
    NOT_FOUND = "NOT_FOUND"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    RESOURCE_GONE = "RESOURCE_GONE"
    CONFLICT = "CONFLICT"
    ALREADY_EXISTS = "ALREADY_EXISTS"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    THROTTLED = "THROTTLED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

    # Knowledge graph specific (L3)
    NEO4J_ERROR = "NEO4J_ERROR"
    CYPHER_SYNTAX_ERROR = "CYPHER_SYNTAX_ERROR"
    GRAPH_CONSTRAINT_VIOLATION = "GRAPH_CONSTRAINT_VIOLATION"

    # Agent specific (L4)
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    AGENT_EXECUTION_ERROR = "AGENT_EXECUTION_ERROR"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    STATE_PERSISTENCE_ERROR = "STATE_PERSISTENCE_ERROR"

    # Ground truth specific (L5)
    CLAIM_VALIDATION_ERROR = "CLAIM_VALIDATION_ERROR"
    SOURCE_VERIFICATION_ERROR = "SOURCE_VERIFICATION_ERROR"


class ErrorDetail(BaseModel):
    """Detailed error information for the canonical error envelope.

    This model provides the nested error structure with request_id
    for correlation and optional sanitized details.
    """

    code: ErrorCode = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    request_id: str = Field(..., description="Request ID for support correlation")
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional additional error context (sanitized in production)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "ENTITY_NOT_FOUND",
                "message": "The requested entity was not found",
                "request_id": "req_abc123def456",
                "details": {"entity_type": "Company", "entity_id": "12345"},
            }
        }
    )


class ErrorEnvelope(BaseModel):
    """Canonical error response envelope for all API errors.

    This model ensures consistent error responses across all layers,
    with security-conscious design (no stack traces in production).
    The nested structure provides a clear separation between the envelope
    and the error details.
    """

    error: ErrorDetail = Field(..., description="Error details")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "ENTITY_NOT_FOUND",
                    "message": "The requested entity was not found",
                    "request_id": "req_abc123def456",
                    "details": {"entity_type": "Company", "entity_id": "12345"},
                }
            }
        }
    )


class ErrorResponse(BaseModel):
    """Legacy flat error response model for backward compatibility.

    This model is deprecated in favor of ErrorEnvelope but kept
    for migration purposes. New code should use ErrorEnvelope.
    """

    code: ErrorCode = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    trace_id: str = Field(..., description="Request trace ID for support correlation")
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional additional error context (sanitized in production)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "ENTITY_NOT_FOUND",
                "message": "The requested entity was not found",
                "trace_id": "req_abc123def456",
                "details": {"entity_type": "Company", "entity_id": "12345"},
            }
        }
    )
