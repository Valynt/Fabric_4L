"""Security middleware for input validation and sanitization.

Provides centralized security validation with per-layer configuration support.
Uses stream caching with receive() override to avoid body consumption issues.

NOTE: This is the authoritative security middleware for Layer 2+ runtime.
Do not confuse with shared/security/middleware.py at the repo root, which is
a separate package for repo-wide utilities.
See: docs/security/shared-package-collision.md
"""

import html
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, FrozenSet

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message, Receive, Scope, Send
from value_fabric.shared.models.typed_dict import TypedDictModel


class SecurityMiddleware__sanitize_json_dataResult(TypedDictModel):
    pass


class SecurityMiddleware_receiveResult(TypedDictModel):
    body: Any
    more_body: bool
    type: str

# Security patterns for injection detection
# WARNING: This is a defense-in-depth layer only. These patterns can be bypassed via:
# - Unicode homoglyphs (e.g., Cyrillic characters that look like Latin)
# - Comment-based obfuscation (e.g., S/**/ELECT)
# - Hex/encoded payloads (e.g., 0x53454c454354)
# Primary SQL injection protection MUST be via parameterized queries at the data layer.
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
    r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
    r"(\b(OR|AND)\s+['\"]\w+['\"]\s*=\s*['\"]\w+['\"])",
    r"(--(?:\s|$)|\/\*|\*\/)",
    r"(\b(LOAD_FILE|INTO\s+OUTFILE|DUMPFILE)\b)",
    r"(\bWAITFOR\s+DELAY\b|\bBENCHMARK\s*\(|\bSLEEP\s*\()",
]

XSS_PATTERNS = [
    r"<\s*script[^>]*>.*?<\s*/\s*script\s*>",
    r"javascript\s*:",
    r"on\w+\s*=",
    r"<\s*iframe[^>]*>",
    r"<\s*object[^>]*>",
    r"<\s*embed[^>]*>",
    r"<\s*link[^>]*>",
    r"<\s*meta[^>]*>",
]

NOSQL_INJECTION_PATTERNS = [
    r"(\$where|\$ne|\$gt|\$lt|\$in|\$nin)",
    r"(\{.*\$.*\})",
    r"(true\s*\|\s*false)",
    r"(\.\s*\.)",
]

COMMAND_INJECTION_PATTERNS = [
    # Command separators and redirections (require surrounding context)
    r"(;\s*\||\|\s*|\|\||&&|\$\(|\`\s*\w+|\|\s*\w+)",
    # Common command-line tools used in attacks
    r"\b(curl|wget|nc|netcat|ssh|ftp|telnet)\b",
    # Dangerous file operations
    r"\b(rm\s+-rf|mv\s+.*\s+/dev/null|dd\s+if=)\b",
    # Scripting language invocations
    r"\b(python|perl|ruby|php)\s+(-c|-e|--eval)",
]


@dataclass(frozen=True)
class SecurityConfig:
    """Configuration for SecurityMiddleware.
    
    Attributes:
        skip_validation_paths: Paths that bypass security validation
        strict_mode: If True, blocks requests on security violations
        max_body_size_bytes: Maximum body size to buffer (default 1MB)
        validate_json_bodies: Whether to scan JSON request bodies
        enable_hsts: If True, adds Strict-Transport-Security header
    """
    skip_validation_paths: FrozenSet[str] = field(default_factory=frozenset)
    strict_mode: bool = True
    max_body_size_bytes: int = 1_048_576  # 1MB
    validate_json_bodies: bool = True
    max_json_depth: int = 10
    sanitize_json_strings: bool = True
    enable_hsts: bool = True

    @staticmethod
    def from_env(
        *,
        skip_validation_paths: FrozenSet[str] = frozenset(),
        strict_mode: bool = True,
    ) -> "SecurityConfig":
        """Build security configuration from env vars with safe defaults."""
        import os

        def _bool_from_env(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return raw.strip().lower() in {"1", "true", "yes", "on"}

        def _int_from_env(name: str, default: int, minimum: int) -> int:
            raw = os.getenv(name)
            if raw is None:
                return default
            try:
                return max(int(raw), minimum)
            except (TypeError, ValueError):
                return default

        return SecurityConfig(
            skip_validation_paths=skip_validation_paths,
            strict_mode=strict_mode,
            max_body_size_bytes=_int_from_env(
                "SECURITY_MAX_BODY_SIZE_BYTES", 1_048_576, 1024
            ),
            validate_json_bodies=_bool_from_env("SECURITY_VALIDATE_JSON_BODIES", True),
            max_json_depth=_int_from_env("SECURITY_MAX_JSON_DEPTH", 10, 1),
            sanitize_json_strings=_bool_from_env("SECURITY_SANITIZE_JSON_STRINGS", True),
            enable_hsts=_bool_from_env("SECURITY_ENABLE_HSTS", True),
        )


class SecurityValidator:
    """Security validation utilities for input sanitization."""

    @staticmethod
    def detect_injection(value: str, patterns: list[str]) -> bool:
        """Detect if value matches any injection patterns."""
        if not isinstance(value, str):
            return False

        value_lower = value.lower()
        for pattern in patterns:
            if re.search(pattern, value_lower, re.IGNORECASE | re.MULTILINE):
                return True
        return False

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string input to prevent XSS.

        Args:
            value: The string to sanitize. If not a string, returns str(value).

        Returns:
            The sanitized string.
        """
        if not isinstance(value, str):
            return str(value)

        # HTML escape
        value = html.escape(value)

        # Remove null bytes
        value = value.replace("\x00", "")

        # Normalize whitespace
        value = " ".join(value.split())

        return value

    @staticmethod
    def validate_json_structure(data: Any, max_depth: int = 10) -> bool:
        """Validate JSON structure to prevent deep recursion attacks."""
        if max_depth <= 0:
            return False

        if isinstance(data, dict):
            if len(data) > 1000:  # Prevent large object attacks
                return False
            return all(
                SecurityValidator.validate_json_structure(v, max_depth - 1)
                for v in data.values()
            )
        elif isinstance(data, list):
            if len(data) > 1000:  # Prevent large array attacks
                return False
            return all(
                SecurityValidator.validate_json_structure(item, max_depth - 1)
                for item in data
            )
        else:
            return True

    @staticmethod
    def validate_field_name(name: str) -> bool:
        """Validate field names to prevent injection."""
        if not isinstance(name, str):
            return False

        # Only allow alphanumeric, underscore, and dash
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", name))

    @staticmethod
    def sanitize_query_params(params: dict[str, Any]) -> dict[str, Any]:
        """Sanitize query parameters."""
        sanitized = {}
        for key, value in params.items():
            if SecurityValidator.validate_field_name(key):
                if isinstance(value, str):
                    sanitized[key] = SecurityValidator.sanitize_string(value)
                elif isinstance(value, list):
                    sanitized[key] = [
                        SecurityValidator.sanitize_string(item)
                        if isinstance(item, str)
                        else item
                        for item in value
                    ]
                else:
                    sanitized[key] = value
        return sanitized


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for input validation and sanitization.
    
    Uses stream caching with receive() override to ensure downstream
    consumers can still read the request body after security validation.
    """

    def __init__(self, app, config: SecurityConfig):
        """Initialize security middleware.
        
        Args:
            app: FastAPI/Starlette application
            config: Security configuration including skip paths and strict mode
        """
        super().__init__(app)
        self.config = config
        # Pre-compute normalized paths for efficient lookup
        self._normalized_skip_paths = frozenset(
            p.rstrip("/").lower() for p in config.skip_validation_paths
        )

    def _should_skip_validation(self, path: str) -> bool:
        """Check if path should skip security validation."""
        normalized = path.rstrip("/").lower()
        return normalized in self._normalized_skip_paths

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through security validation with body stream caching."""
        # Skip validation for configured paths
        if self._should_skip_validation(request.url.path):
            response = await call_next(request)
            if self.config.enable_hsts:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response

        # Skip body validation for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            response = await call_next(request)
            if self.config.enable_hsts:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response

        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > self.config.max_body_size_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": "Request body too large",
                        "max_body_size_bytes": self.config.max_body_size_bytes,
                    },
                )

        violations = []

        # Validate query parameters
        query_params = dict(request.query_params)
        sanitized_query = SecurityValidator.sanitize_query_params(query_params)

        for key, value in query_params.items():
            if isinstance(value, str):
                if SecurityValidator.detect_injection(value, SQL_INJECTION_PATTERNS):
                    violations.append(
                        f"SQL injection detected in query parameter '{key}'"
                    )
                if SecurityValidator.detect_injection(value, XSS_PATTERNS):
                    violations.append(f"XSS detected in query parameter '{key}'")
                if SecurityValidator.detect_injection(
                    value, COMMAND_INJECTION_PATTERNS
                ):
                    violations.append(
                        f"Command injection detected in query parameter '{key}'"
                    )

        # Cache and validate request body if applicable
        body_content = None
        if (
            self.config.validate_json_bodies
            and request.headers.get("content-type", "").startswith("application/json")
            and request.method in ("POST", "PUT", "PATCH")
        ):
            body_content = await self._cache_and_validate_body(request, violations)
            if body_content == b"__SECURITY_BODY_TOO_LARGE__":
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": "Request body too large",
                        "max_body_size_bytes": self.config.max_body_size_bytes,
                    },
                )

        # Handle violations
        if violations:
            # Import logger locally to avoid circular imports
            try:
                from structlog import get_logger
                logger = get_logger(__name__)
            except ImportError:
                import logging
                logger = logging.getLogger(__name__)

            logger.warning(
                "Security violations detected",
                extra={
                    "violations": violations,
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": request.client.host if request.client else None,
                },
            )

            if self.config.strict_mode:
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": "Security validation failed",
                        "violations": violations,
                    },
                )

        # Update request with sanitized query params
        request._query_params = sanitized_query

        # If we cached body content, inject a new receive() that returns it
        if body_content is not None:
            original_receive = request.receive
            request._body = body_content
            request._receive = self._make_receive_override(original_receive, body_content)

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        if self.config.enable_hsts:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

    async def _cache_and_validate_body(
        self, request: Request, violations: list[str]
    ) -> bytes | None:
        """Cache body content and validate for injection patterns.
        
        Returns the cached body content, or a sentinel if too large.
        """
        try:
            body = await request.body()
            
            # Reject if body is too large
            if len(body) > self.config.max_body_size_bytes:
                return b"__SECURITY_BODY_TOO_LARGE__"

            if body:
                try:
                    json_data = json.loads(body.decode("utf-8"))

                    # Validate JSON structure
                    if not SecurityValidator.validate_json_structure(
                        json_data, max_depth=self.config.max_json_depth
                    ):
                        violations.append(
                            "Invalid JSON structure - possible recursion attack"
                        )

                    # Scan JSON values for injection patterns
                    self._validate_json_data(json_data, violations)

                    if self.config.sanitize_json_strings:
                        sanitized_json = self._sanitize_json_data(json_data)
                        body = json.dumps(
                            sanitized_json, ensure_ascii=False, separators=(",", ":")
                        ).encode("utf-8")

                except json.JSONDecodeError:
                    # Invalid JSON will be handled by FastAPI
                    pass
                except Exception:
                    # Log but don't block on validation errors
                    pass

            return body

        except Exception:
            # If we can't read the body, don't block but don't cache either
            return None

    def _make_receive_override(
        self, original_receive: Receive, cached_body: bytes
    ) -> Receive:
        """Create a receive() override that returns cached body then resumes original.
        
        This preserves compatibility with FastAPI/Starlette body consumption.
        """
        body_sent = False

        async def receive() -> Message:
            nonlocal body_sent
            if not body_sent and cached_body:
                body_sent = True
                return {
                    "type": "http.request",
                    "body": cached_body,
                    "more_body": False,
                }

            # After body is consumed, delegate to original receive
            return await original_receive()

        return receive

    def _validate_json_data(
        self, data: Any, violations: list[str], path: str = ""
    ) -> None:
        """Recursively validate JSON data for injection patterns."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if not SecurityValidator.validate_field_name(key):
                    violations.append(f"Invalid field name: {current_path}")

                if isinstance(value, str):
                    self._check_string_injections(value, current_path, violations)
                elif isinstance(value, (dict, list)):
                    self._validate_json_data(value, violations, current_path)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"

                if isinstance(item, str):
                    self._check_string_injections(item, current_path, violations)
                elif isinstance(item, (dict, list)):
                    self._validate_json_data(item, violations, current_path)

    def _sanitize_json_data(self, data: Any) -> Any:
        """Recursively sanitize all user-supplied string fields."""
        if isinstance(data, dict):
            return {key: self._sanitize_json_data(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        if isinstance(data, str):
            return SecurityValidator.sanitize_string(data)
        return data

    @staticmethod
    def _is_rdf_data(value: str) -> bool:
        """Check if string looks like RDF/Turtle data (not injection)."""
        rdf_indicators = [
            "@prefix",
            "@base",
            "rdf:type",
            "http://",
            "https://",
        ]
        indicator_count = sum(1 for ind in rdf_indicators if ind in value)
        has_uri_syntax = "<http" in value and ">" in value
        return indicator_count >= 2 or (indicator_count >= 1 and has_uri_syntax)

    def _check_string_injections(
        self, value: str, path: str, violations: list[str]
    ) -> None:
        """Check string value for various injection patterns."""
        # Skip injection checks for legitimate RDF/Turtle data
        if self._is_rdf_data(value):
            return

        if SecurityValidator.detect_injection(value, SQL_INJECTION_PATTERNS):
            violations.append(f"SQL injection detected in field '{path}'")

        if SecurityValidator.detect_injection(value, XSS_PATTERNS):
            violations.append(f"XSS detected in field '{path}'")

        if SecurityValidator.detect_injection(value, NOSQL_INJECTION_PATTERNS):
            violations.append(f"NoSQL injection detected in field '{path}'")

        if SecurityValidator.detect_injection(value, COMMAND_INJECTION_PATTERNS):
            violations.append(f"Command injection detected in field '{path}'")


def add_security_middleware(app, config: SecurityConfig | None = None) -> None:
    """Add security middleware to FastAPI application.
    
    Args:
        app: FastAPI application
        config: Security configuration. If None, uses defaults (strict mode, no skip paths).
    """
    if config is None:
        config = SecurityConfig()
    app.add_middleware(SecurityMiddleware, config=config)
