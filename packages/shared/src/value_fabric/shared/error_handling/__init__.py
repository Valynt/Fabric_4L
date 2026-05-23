"""Shared error handling module for all Value Fabric layers."""

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
    ValueFabricException,
)
from .handlers import (
    canonical_error_response_schema,
    install_error_response_openapi,
    register_exception_handlers,
)
from .helpers import build_error_detail, sanitize_log_error
from .middleware import get_request_id, RequestIDMiddleware
from .models import ErrorCode, ErrorEnvelope, ErrorDetail, ErrorResponse

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "canonical_error_response_schema",
    "ErrorCode",
    "ErrorEnvelope",
    "ErrorDetail",
    "ErrorResponse",
    "build_error_detail",
    "get_request_id",
    "install_error_response_openapi",
    "NotFoundError",
    "RateLimitError",
    "register_exception_handlers",
    "RequestIDMiddleware",
    "sanitize_log_error",
    "ServiceUnavailableError",
    "ValidationError",
    "ValueFabricException",
]
