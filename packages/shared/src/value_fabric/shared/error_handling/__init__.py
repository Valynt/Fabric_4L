"""Shared error handling module for all Value Fabric layers."""

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    TenantIsolationError,
    ValidationError,
    ValueFabricException,
)
from .handlers import (
    canonical_error_response_schema,
    install_error_response_openapi,
    register_exception_handlers,
)
from .helpers import build_error_detail, sanitize_log_error
from .sanitizer import PublicError, sanitize_error_for_log, sanitize_public_error
from .middleware import get_request_id, RequestIDMiddleware
from .models import ErrorCode, ErrorEnvelope, ErrorDetail, ErrorResponse

# Versioned surface marker (R2 versioned shared boundaries).
# The public API of this boundary is ``__all__``; changing it requires a coordinated
# ``SURFACE_VERSION`` bump and a regeneration of ``config/ci/shared_surface_contract.json``
# (via scripts/ci/check_shared_boundary_surfaces.py --update). This marker is intentionally
# NOT part of ``__all__``: it is boundary metadata, not exported API.
SURFACE_VERSION = "1.0.0"

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
    "PublicError",
    "sanitize_error_for_log",
    "sanitize_public_error",
    "ServiceUnavailableError",
    "TenantIsolationError",
    "ValidationError",
    "ValueFabricException",
]
