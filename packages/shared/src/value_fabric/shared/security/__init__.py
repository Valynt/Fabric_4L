"""Shared security middleware for input validation and sanitization.

This package provides a centralized SecurityMiddleware implementation
with per-layer configuration support.
"""

from .middleware import (
    SecurityConfig,
    SecurityMiddleware,
    SecurityValidator,
    add_security_middleware,
    SQL_INJECTION_PATTERNS,
    XSS_PATTERNS,
    NOSQL_INJECTION_PATTERNS,
)
from .config import (
    SecurityConfig as RootSecurityConfig,
    ProductionSafetyValidator,
    validate_production_safety,
    is_production_like_environment,
    is_strict_environment,
    detect_environment,
    get_startup_summary,
)
from .redaction import (
    REDACTED_VALUE,
    RedactionFilter,
    install_redaction_filter,
    is_sensitive_key,
    redact_credentials,
    redact_value,
    redaction_processor,
)

__all__ = [
    "SecurityConfig",
    "SecurityMiddleware",
    "SecurityValidator",
    "add_security_middleware",
    "SQL_INJECTION_PATTERNS",
    "XSS_PATTERNS",
    "NOSQL_INJECTION_PATTERNS",
    "REDACTED_VALUE",
    "RedactionFilter",
    "install_redaction_filter",
    "is_sensitive_key",
    "redact_credentials",
    "redact_value",
    "redaction_processor",
    "ProductionSafetyValidator",
    "validate_production_safety",
    "is_production_like_environment",
    "is_strict_environment",
    "detect_environment",
    "get_startup_summary",
]
