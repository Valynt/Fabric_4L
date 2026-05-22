"""Error response models for standardized error handling across all layers."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(str, Enum):
    """Standardized error codes across all Value Fabric services."""

    # Authentication/Authorization errors (4xx)
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"

    # Validation errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Resource errors (4xx)
    NOT_FOUND = "NOT_FOUND"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    RESOURCE_GONE = "RESOURCE_GONE"
    CONFLICT = "CONFLICT"
    ALREADY_EXISTS = "ALREADY_EXISTS"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
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


class ErrorResponse(BaseModel):
    """Standardized error response model for all API errors.

    This model ensures consistent error responses across all layers,
    with security-conscious design (no stack traces in production).
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


def build_error_detail(
    *,
    message: str,
    error_code: str,
    request_id: str | None,
    correlation_id: str | None = None,
) -> dict[str, str]:
    """Build canonical API error detail payload for HTTPException responses."""
    payload = {
        "message": message,
        "error_code": error_code,
    }
    if request_id:
        payload["request_id"] = request_id
    if correlation_id:
        payload["correlation_id"] = correlation_id
    return payload
