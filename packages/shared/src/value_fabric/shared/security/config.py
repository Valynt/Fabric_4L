"""Security configuration and startup validation."""

from __future__ import annotations

import logging
import os
import re
from typing import Any
from urllib.parse import parse_qsl, urlparse

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Minimum JWT secret length for production (NIST SP 800-117 recommends >= 256 bits)
_MIN_JWT_SECRET_LENGTH = 32

# Known weak/placeholder secrets that must never be used in production
_WEAK_SECRET_DENYLIST = frozenset({
    "", "changeme", "change_me", "change-me", "change me",
    "password", "secret", "secretkey", "secret_key", "secret-key",
    "your-secret", "your_secret", "yoursecret",
    "test-secret", "test_secret", "testsecret",
    "default", "defaultsecret", "default_secret",
    "admin", "root", "123456", "12345678", "qwerty",
})

# JWT algorithms approved for use (NIST/RFC 7518 safe subset)
_APPROVED_JWT_ALGORITHMS = frozenset({
    "HS256", "HS384", "HS512",
    "RS256", "RS384", "RS512",
    "ES256", "ES384", "ES512",
})

# Dev-only environment names — anything else is treated as production-like
_TEST_ENVIRONMENTS = frozenset({"test", "testing", "ci"})

# Known PostgreSQL superuser names that bypass RLS
_SUPERUSER_NAMES = frozenset({"postgres", "rdsadmin", "cloudsqladmin", "azure_superuser"})

# Default database credentials that must not be used in production
_DEFAULT_DATABASE_USERS = frozenset({"postgres", "admin", "root", "user", "dbuser"})
_DEFAULT_DATABASE_NAMES = frozenset({"postgres", "admin", "test", "db", "database"})

# Localhost hostnames that must not be used in production
_LOCALHOST_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})
_APPROVED_DATABASE_SSL_MODES = frozenset({"require", "verify-ca", "verify-full"})
_PREFERRED_DATABASE_SSL_MODE = "verify-full"


class SecurityConfig(BaseModel):
    """Security middleware configuration."""

    # CORS — fail-closed defaults. Wildcards are never permitted in production-like
    # environments and are only used as a dev convenience when explicitly enabled.
    _DEFAULT_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    _DEFAULT_CORS_HEADERS = ["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID"]

    cors_origins: list[str] = Field(default=[], description="Allowed CORS origins")
    cors_methods: list[str] = Field(default=_DEFAULT_CORS_METHODS, description="Allowed CORS methods")
    cors_headers: list[str] = Field(default=_DEFAULT_CORS_HEADERS, description="Allowed CORS headers")
    
    # Security headers
    enable_hsts: bool = Field(default=True, description="Enable HSTS header")
    enable_xframe: bool = Field(default=True, description="Enable X-Frame-Options")
    enable_xss_protection: bool = Field(default=True, description="Enable XSS protection")
    enable_content_type_options: bool = Field(default=True, description="Enable X-Content-Type-Options")
    enable_referrer_policy: bool = Field(default=True, description="Enable Referrer-Policy")
    
    # CSP
    content_security_policy: str | None = Field(
        default="default-src 'self'",
        description="Content-Security-Policy header"
    )
    
    # Request limits
    max_body_size: int = Field(default=10 * 1024 * 1024, description="Max request body size (bytes)")
    max_body_size_bytes: int = Field(default=1_048_576, description="Max body size for validation (bytes)")
    
    # Validation settings
    skip_validation_paths: frozenset[str] = Field(default=frozenset(), description="Paths to skip validation")
    strict_mode: bool = Field(default=True, description="Strict validation mode")
    validate_json_bodies: bool = Field(default=True, description="Validate JSON request bodies")
    
    class Config:
        extra = "allow"


# ═══════════════════════════════════════════════════════════════════════════
# Environment Detection
# ═══════════════════════════════════════════════════════════════════════════


def detect_environment() -> str:
    """Detect environment from ENVIRONMENT, ENV, or APP_ENV variables."""
    for key in ("ENVIRONMENT", "ENV", "APP_ENV"):
        val = os.getenv(key, "").strip().lower()
        if val:
            return val
    return "development"


def is_production() -> bool:
    """Check if running in production environment."""
    return detect_environment() == "production"


def is_staging() -> bool:
    """Check if running in staging environment."""
    return detect_environment() == "staging"


def is_development() -> bool:
    """Check if running in development environment."""
    return detect_environment() == "development"


def is_test_runtime(environment: str | None = None) -> bool:
    """Check if running in test-only runtime profile."""
    env = (environment or detect_environment()).strip().lower()
    return env in _TEST_ENVIRONMENTS


def is_production_like_environment(environment: str | None = None) -> bool:
    """Return True for production, staging, or any unknown environment.

    This is the canonical fail-safe policy: unknown/custom environments are
    treated as production-like so that security controls are never accidentally
    relaxed.
    """
    env = (environment or detect_environment()).strip().lower()
    return not is_test_runtime(env)


# ═══════════════════════════════════════════════════════════════════════════
# Production Safety Validator
# ═══════════════════════════════════════════════════════════════════════════


class ProductionSafetyValidator:
    """Fail-closed validator for required production dependencies.

    Authentication, persistence, encryption, API keys, CORS origins, and tenant
    isolation must never downgrade to mock, fallback, or development behavior in
    ``production`` or ``staging`` modes (or any unknown environment).

    Usage::

        from value_fabric.shared.security.config import validate_production_safety
        validate_production_safety()  # raises RuntimeError on misconfiguration
    """

    def __init__(self, environment: str | None = None) -> None:
        self.environment = (environment or detect_environment()).strip().lower()
        self.is_production_like = is_production_like_environment(self.environment)
        self.errors: list[str] = []

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def validate_authentication(self) -> None:
        """JWT secret and auth bypass flags."""
        jwt_secret = os.getenv("JWT_SECRET", "")
        if not jwt_secret:
            self.errors.append(
                "JWT_SECRET is required in production-like environments. "
                "Authentication cannot operate without a signing secret."
            )
            return

        normalized = jwt_secret.strip().lower()
        if len(jwt_secret) < _MIN_JWT_SECRET_LENGTH:
            self.errors.append(
                f"JWT_SECRET is too short ({len(jwt_secret)} chars). "
                f"Production-like environments require at least {_MIN_JWT_SECRET_LENGTH} characters "
                f"(256 bits) to resist brute-force attacks."
            )
        if normalized in _WEAK_SECRET_DENYLIST:
            self.errors.append(
                "JWT_SECRET appears to be a known placeholder or weak value. "
                "Generate a strong secret: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )

        # Auth bypass flags must never be enabled in production-like envs
        if os.getenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "").lower() in ("true", "1", "yes"):
            self.errors.append(
                "ALLOW_INSECURE_DEV_AUTH_BYPASS must be false or unset in production-like environments. "
                "Development authentication bypass is a critical security risk."
            )
        if os.getenv("JWT_FALLBACK_TO_QUERY_PARAM", "").lower() in ("true", "1", "yes"):
            self.errors.append(
                "JWT_FALLBACK_TO_QUERY_PARAM must be false or unset in production-like environments. "
                "Passing tokens in query strings leaks credentials to logs and proxies."
            )
        if os.getenv("DEV_AUTH_BYPASS", "").lower() in ("true", "1", "yes"):
            self.errors.append(
                "DEV_AUTH_BYPASS must be false or unset in production-like environments. "
                "Development authentication bypass is a critical security risk."
            )
        if os.getenv("ALLOW_DEV_AUTH_BYPASS", "").lower() in ("true", "1", "yes"):
            self.errors.append(
                "ALLOW_DEV_AUTH_BYPASS must be false or unset in production-like environments. "
                "Development authentication bypass is a critical security risk."
            )
        if os.getenv("AUTH_BYPASS_ENABLED", "").lower() in ("true", "1", "yes"):
            self.errors.append(
                "AUTH_BYPASS_ENABLED must be false or unset in production-like environments. "
                "Development authentication bypass is a critical security risk."
            )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def validate_persistence(self) -> None:
        """Database URL must be durable PostgreSQL with non-default credentials."""
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            self.errors.append(
                "DATABASE_URL is required in production-like environments. "
                "Services must not start without a configured persistence backend."
            )
            return

        if database_url.startswith("sqlite"):
            self.errors.append(
                "SQLite is not permitted in production-like environments. "
                "Use PostgreSQL with Row-Level Security for multi-tenant isolation."
            )
            return

        try:
            parsed = urlparse(database_url)
            host = (parsed.hostname or "").lower()
            username = (parsed.username or "").lower()
            db_name = (parsed.path or "").lstrip("/").lower()
        except Exception:
            self.errors.append("DATABASE_URL is malformed and cannot be parsed.")
            return

        if host in _LOCALHOST_HOSTS:
            self.errors.append(
                f"DATABASE_URL host '{host}' is localhost. "
                f"Production-like environments require a network-resident database."
            )
        if username in _DEFAULT_DATABASE_USERS:
            self.errors.append(
                f"DATABASE_URL user '{username}' is a default/weak account. "
                f"Create a dedicated application role with least privilege."
            )
        if username in _SUPERUSER_NAMES:
            self.errors.append(
                f"DATABASE_URL user '{username}' is a PostgreSQL superuser. "
                f"Superusers bypass ALL Row-Level Security policies, making tenant isolation ineffective."
            )
        if db_name.split("?")[0] in _DEFAULT_DATABASE_NAMES:
            self.errors.append(
                f"DATABASE_URL database '{db_name}' is a default name. "
                f"Use a service-specific database name."
            )

        # Mock persistence must not be enabled
        if os.getenv("MOCK_PERSISTENCE", "").lower() in ("true", "1", "yes"):
            self.errors.append(
                "MOCK_PERSISTENCE must be false or unset in production-like environments. "
                "Mock persistence destroys data durability and tenant isolation guarantees."
            )

    # ------------------------------------------------------------------
    # Encryption
    # ------------------------------------------------------------------
    def validate_encryption(self) -> None:
        """Master encryption key must be explicitly configured."""
        master_key = os.getenv("CREDENTIALS_MASTER_KEY", "")
        if not master_key:
            self.errors.append(
                "CREDENTIALS_MASTER_KEY is required in production-like environments. "
                "Ephemeral encryption keys would cause irreversible data loss on restart."
            )
            return

        normalized = master_key.strip().lower()
        if normalized in _WEAK_SECRET_DENYLIST or normalized.startswith("change"):
            self.errors.append(
                "CREDENTIALS_MASTER_KEY appears to be a placeholder. "
                "Set a strong 256-bit base64-encoded Fernet key."
            )

        allow_ephemeral = os.getenv("ALLOW_EPHEMERAL_ENCRYPTION", "").lower() in ("true", "1", "yes")
        if allow_ephemeral:
            self.errors.append(
                "ALLOW_EPHEMERAL_ENCRYPTION must be false or unset in production-like environments."
            )

    # ------------------------------------------------------------------
    # API Keys
    # ------------------------------------------------------------------
    def validate_api_keys(self) -> None:
        """API key HMAC secret must be configured and strong."""
        api_key_secret = os.getenv("API_KEY_HMAC_SECRET", "")
        if not api_key_secret:
            self.errors.append(
                "API_KEY_HMAC_SECRET is required in production-like environments. "
                "API key integrity verification cannot operate without an HMAC secret."
            )
            return

        normalized = api_key_secret.strip().lower()
        if len(api_key_secret) < _MIN_JWT_SECRET_LENGTH:
            self.errors.append(
                f"API_KEY_HMAC_SECRET is too short ({len(api_key_secret)} chars). "
                f"Use at least {_MIN_JWT_SECRET_LENGTH} characters."
            )
        if normalized in _WEAK_SECRET_DENYLIST or normalized.startswith("change"):
            self.errors.append(
                "API_KEY_HMAC_SECRET appears to be a placeholder or weak value."
            )

    # ------------------------------------------------------------------
    # CORS Origins
    # ------------------------------------------------------------------
    def validate_cors_origins(self) -> None:
        """CORS origins must be explicit, HTTPS-only, and contain no wildcards."""
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if not cors_origins or cors_origins.strip() == "":
            self.errors.append(
                "CORS_ORIGINS is required in production-like environments. "
                "Wildcard or missing CORS allows arbitrary cross-origin requests."
            )
            return

        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
        if not origins:
            self.errors.append(
                "CORS_ORIGINS is empty after parsing. Provide at least one trusted origin."
            )
            return

        if "*" in origins:
            self.errors.append(
                "CORS_ORIGINS contains wildcard '*'. Explicit HTTPS origins are required in production-like environments."
            )

        for origin in origins:
            if "*" in origin:
                self.errors.append(
                    f"CORS origin '{origin}' contains a wildcard. Each origin must be an exact URL."
                )
                continue
            parsed = urlparse(origin)
            if parsed.scheme not in {"https"} and not is_development():
                # Allow http:// only in development
                self.errors.append(
                    f"CORS origin '{origin}' must use HTTPS in production-like environments."
                )
            if not parsed.netloc:
                self.errors.append(
                    f"CORS origin '{origin}' is missing a host. Provide a complete URL like https://app.example.com."
                )

    # ------------------------------------------------------------------
    # Tenant Isolation
    # ------------------------------------------------------------------
    def validate_tenant_isolation(self) -> None:
        """Tenant isolation prerequisites: valid default tenant ID, no shared schemas."""
        default_tenant = os.getenv("DEFAULT_TENANT_ID", "").strip()
        if not default_tenant:
            self.errors.append(
                "DEFAULT_TENANT_ID is required in production-like environments. "
                "A missing default tenant prevents deterministic fallback isolation."
            )
        elif default_tenant.lower() == "default":
            self.errors.append(
                "DEFAULT_TENANT_ID must not use the literal value 'default'. "
                "This is an implicit fallback that breaks deterministic isolation."
            )
        else:
            # Validate UUID format (basic check)
            uuid_pattern = re.compile(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
            )
            if not uuid_pattern.match(default_tenant):
                self.errors.append(
                    f"DEFAULT_TENANT_ID '{default_tenant}' is not a valid UUID. "
                    f"Tenant IDs must be deterministic UUIDs for isolation guarantees."
                )

        # Service auth secret (used for inter-service auth) must also be strong
        service_auth = os.getenv("SERVICE_AUTH_SECRET", "").strip()
        if not service_auth:
            self.errors.append(
                "SERVICE_AUTH_SECRET is required in production-like environments. "
                "Inter-service authentication cannot operate without a shared secret."
            )
        elif len(service_auth) < _MIN_JWT_SECRET_LENGTH:
            self.errors.append(
                f"SERVICE_AUTH_SECRET is too short ({len(service_auth)} chars). "
                f"Use at least {_MIN_JWT_SECRET_LENGTH} characters."
            )
        elif service_auth.lower() in _WEAK_SECRET_DENYLIST:
            self.errors.append(
                "SERVICE_AUTH_SECRET appears to be a known placeholder or weak value."
            )

        # Multi-tenant mode must be explicitly enabled
        if os.getenv("MULTI_TENANT_MODE", "").lower() == "false":
            self.errors.append(
                "MULTI_TENANT_MODE must not be explicitly disabled in production-like environments."
            )

    # ------------------------------------------------------------------
    # LLM / External Providers
    # ------------------------------------------------------------------
    def validate_external_providers(self) -> None:
        """Mock LLM providers must not be used in production-like environments."""
        llm_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        if llm_provider == "mock":
            self.errors.append(
                "LLM_PROVIDER='mock' is not permitted in production-like environments. "
                "Configure a real inference endpoint (e.g., openai, anthropic, azure)."
            )
        if os.getenv("ALLOW_MOCK_LLM", "").lower() in ("true", "1", "yes"):
            self.errors.append(
                "ALLOW_MOCK_LLM must be false or unset in production-like environments."
            )

    # ------------------------------------------------------------------
    # Debug / Development Flags
    # ------------------------------------------------------------------
    def validate_debug_flags(self) -> None:
        """DEBUG mode and development flags must be disabled."""
        if os.getenv("DEBUG", "").lower() == "true":
            self.errors.append(
                "DEBUG must be false or unset in production-like environments."
            )
        if os.getenv("SEED_DEMO_DATA", "").lower() in ("true", "1", "yes"):
            self.errors.append(
                "SEED_DEMO_DATA must be false or unset in production-like environments. "
                "Demo data seeding pollutes production databases with synthetic records."
            )

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    def validate(self) -> None:
        """Run all production-safety checks."""
        if not self.is_production_like:
            # In dev/test environments, run validations as warnings only
            self._run_all()
            if self.errors:
                for msg in self.errors:
                    logger.warning("Development environment config warning: %s", msg)
                self.errors.clear()
            return
        self._run_all()
        if self.errors:
            raise RuntimeError(
                f"Production safety validation failed for environment='{self.environment}':\n"
                + "\n".join(f"  • {err}" for err in self.errors)
            )

    def _run_all(self) -> None:
        """Execute every validation gate."""
        self.validate_authentication()
        self.validate_persistence()
        self.validate_encryption()
        self.validate_api_keys()
        self.validate_cors_origins()
        self.validate_tenant_isolation()
        self.validate_external_providers()
        self.validate_debug_flags()


def validate_production_safety(environment: str | None = None) -> None:
    """Fail-closed gate: raise RuntimeError if required production dependencies are missing.

    This is the canonical entry-point that every service should call during startup.
    It never allows mock, fallback, or development behavior in ``production``,
    ``staging``, or any unknown environment.

    Raises:
        RuntimeError: If any required control is missing or misconfigured.
    """
    validator = ProductionSafetyValidator(environment=environment)
    validator.validate()


# ═══════════════════════════════════════════════════════════════════════════
# Legacy Startup Validation Functions (preserved for backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════


def validate_cors_config() -> None:
    """Validate CORS configuration for production safety.
    
    Raises:
        ValueError: If CORS is misconfigured in production
    """
    cors_origins = os.getenv("CORS_ORIGINS", "*")
    
    if is_production():
        # Wildcard CORS is not allowed in production
        if cors_origins == "*":
            raise ValueError(
                "CORS wildcard (*) is not allowed in production. "
                "Specify explicit HTTPS origins."
            )
        
        # HTTP origins are not allowed in production
        if "http://" in cors_origins.lower():
            raise ValueError(
                "HTTP CORS origins are not allowed in production. "
                "Use HTTPS only."
            )
    elif is_development() and cors_origins == "*":
        logger.warning(
            "CORS is set to wildcard (*) in development mode. "
            "This is insecure and should not be used in production."
        )


def validate_database_config() -> None:
    """Validate database configuration for production safety.
    
    Raises:
        ValueError: If database is misconfigured in production
    """
    database_url = os.getenv("DATABASE_URL", "")
    
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    
    if is_production():
        # SQLite is not allowed in production
        if database_url.startswith("sqlite"):
            raise ValueError(
                "SQLite is not supported in production. "
                "Use PostgreSQL with RLS for multi-tenant isolation."
            )
        _validate_database_tls_mode(database_url, source_variable="DATABASE_URL")

        sync_database_url = os.getenv("DATABASE_URL_SYNC", "")
        if sync_database_url:
            _validate_database_tls_mode(sync_database_url, source_variable="DATABASE_URL_SYNC")


def _validate_database_tls_mode(database_url: str, *, source_variable: str) -> None:
    parsed = urlparse(database_url)
    query_params = {key.lower(): value for key, value in parse_qsl(parsed.query, keep_blank_values=True)}
    sslmode = (query_params.get("sslmode", "") or "").strip().lower()

    if sslmode not in _APPROVED_DATABASE_SSL_MODES:
        raise ValueError(
            f"Production {source_variable} must include sslmode=require or stronger "
            "(verify-ca/verify-full); verify-full is preferred."
        )
    if sslmode != _PREFERRED_DATABASE_SSL_MODE:
        logger.info(
            "%s uses sslmode=%s; sslmode=%s is preferred.",
            source_variable,
            sslmode,
            _PREFERRED_DATABASE_SSL_MODE,
        )


def validate_jwt_secret_strength() -> None:
    """Validate that JWT_SECRET meets minimum length requirements.

    A short JWT secret is trivially brute-forceable.  NIST recommends
    at least 256 bits (32 bytes) for HMAC keys.

    Raises:
        ValueError: If JWT_SECRET is too short in production-like environments
    """
    jwt_secret = os.getenv("JWT_SECRET", "")

    if not jwt_secret:
        if is_test_runtime():
            return
        raise ValueError(
            "JWT_SECRET is required in all non-test runtimes. "
            "Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )

    # Enforce minimum length in production-like environments for consistency
    # with other JWT config checks (JWT_ISSUER, JWT_AUDIENCE)
    if is_production_like_environment() and len(jwt_secret) < _MIN_JWT_SECRET_LENGTH:
        raise ValueError(
            f"JWT_SECRET is too short ({len(jwt_secret)} chars). "
            f"Production-like environments require at least {_MIN_JWT_SECRET_LENGTH} characters "
            f"(256 bits) to resist brute-force attacks. "
            f"Generate a strong secret: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    elif not is_development() and len(jwt_secret) < _MIN_JWT_SECRET_LENGTH:
        logger.warning(
            "JWT_SECRET is only %d characters. "
            "Production-like environments require at least %d characters.",
            len(jwt_secret),
            _MIN_JWT_SECRET_LENGTH,
        )


def validate_jwt_config() -> None:
    """Validate JWT configuration for the current environment.

    Checks that JWT_SECRET, JWT_ISSUER, and JWT_AUDIENCE are present in
    production-like environments, that JWT_SECRET meets minimum strength
    requirements, and that JWT_ALGORITHM (if set) is an approved value.
    This is the canonical entry point for JWT configuration validation.

    Raises:
        ValueError: If JWT configuration is unsafe for the current environment
    """
    # Check presence of required JWT config in production-like environments
    if is_production_like_environment():
        jwt_secret = os.getenv("JWT_SECRET", "")
        if not jwt_secret:
            raise ValueError(
                "JWT_SECRET is required in production-like environments. "
                "Authentication cannot operate without a signing secret."
            )

        jwt_issuer = os.getenv("JWT_ISSUER", "")
        if not jwt_issuer:
            raise ValueError(
                "JWT_ISSUER is required in production-like environments. "
                "The issuer claim is required for token validation."
            )

        jwt_audience = os.getenv("JWT_AUDIENCE", "")
        if not jwt_audience:
            raise ValueError(
                "JWT_AUDIENCE is required in production-like environments. "
                "The audience claim is required for token validation."
            )

    # Check secret strength
    validate_jwt_secret_strength()

    # Check algorithm safety
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    if algorithm not in _APPROVED_JWT_ALGORITHMS:
        raise ValueError(
            f"JWT_ALGORITHM '{algorithm}' is not an approved algorithm. "
            f"Approved algorithms: {sorted(_APPROVED_JWT_ALGORITHMS)}"
        )


def validate_database_superuser() -> None:
    """Detect if the database connection uses a PostgreSQL superuser.

    PostgreSQL superusers bypass ALL Row-Level Security policies.
    If the application connects as a superuser, RLS provides zero
    tenant isolation — every query sees every tenant's data.

    Raises:
        ValueError: If DATABASE_URL uses a known superuser role in production
    """
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return

    # Extract username from connection string
    try:
        parsed = urlparse(database_url)
        username = parsed.username or ""
    except Exception:
        username = ""

    # Known PostgreSQL superuser names
    superuser_names = {"postgres", "rdsadmin", "cloudsqladmin", "azure_superuser"}

    if username.lower() in superuser_names:
        msg = (
            f"DATABASE_URL connects as '{username}', which is a PostgreSQL superuser. "
            f"Superusers bypass ALL Row-Level Security policies, meaning tenant "
            f"isolation is completely ineffective. Create a dedicated application "
            f"role: CREATE ROLE app_user LOGIN; GRANT CONNECT ON DATABASE ... TO app_user;"
        )
        if is_production():
            raise ValueError(msg)
        else:
            logger.warning(msg)


def validate_environment_config() -> None:
    """Validate environment configuration for conflicts.
    
    Raises:
        ValueError: If environment variables conflict
    """
    if is_production() and os.getenv("DEBUG", "").lower() == "true":
        raise ValueError(
            "DEBUG mode cannot be enabled in production. "
            "Set DEBUG=false or remove the variable."
        )


def validate_all_controls() -> None:
    """Validate that not all security controls are disabled.
    
    Raises:
        ValueError: If all controls are disabled in production
    """
    if not is_production():
        return
    
    redis_url = os.getenv("REDIS_URL", "")
    audit_sink = os.getenv("AUDIT_SINK_URL", "")
    jwt_secret = os.getenv("JWT_SECRET", "")
    cors_origins = os.getenv("CORS_ORIGINS", "*")
    
    if not redis_url and not audit_sink and not jwt_secret and cors_origins == "*":
        raise ValueError(
            "All security controls are disabled in production. "
            "This indicates a catastrophic misconfiguration."
        )


def get_startup_summary() -> dict[str, Any]:
    """Get startup summary with active control modes.
    
    Returns:
        Dictionary with environment info and control status
    """
    environment = detect_environment()
    redis_url = os.getenv("REDIS_URL", "")
    audit_sink = os.getenv("AUDIT_SINK_URL", "")
    cors_origins = os.getenv("CORS_ORIGINS", "*")
    database_url = os.getenv("DATABASE_URL", "")
    
    summary = {
        "environment": environment,
        "redis_enabled": bool(redis_url),
        "audit_enabled": bool(audit_sink),
        "cors_mode": "restricted" if cors_origins != "*" else "permissive",
        "jwt_validation": "strict" if is_production() else "relaxed",
        "rls_status": _get_rls_status(database_url),
        "warnings": [],
        "degraded_controls": [],
    }
    
    # Check for degraded controls
    if not redis_url:
        summary["degraded_controls"].extend(["redis", "rate_limiting"])
        if not is_development():
            summary["warnings"].append("Redis is not configured - rate limiting disabled")
    
    if not audit_sink:
        summary["degraded_controls"].append("audit")
        if not is_development():
            summary["warnings"].append("Audit sink is not configured - audit events will be lost")
    
    if cors_origins == "*":
        summary["degraded_controls"].append("cors")
        if not is_development():
            summary["warnings"].append("CORS is set to wildcard - security risk")

    # RLS status warnings
    rls_status = summary["rls_status"]
    if rls_status == "disabled":
        summary["degraded_controls"].append("rls")
        summary["warnings"].append(
            "RLS is not active (non-PostgreSQL database). "
            "Tenant isolation relies solely on application-level filtering."
        )
    elif rls_status == "superuser_bypass":
        summary["degraded_controls"].append("rls")
        summary["warnings"].append(
            "Database connection uses a superuser role. "
            "RLS policies exist but are bypassed for superusers."
        )
    
    if summary["warnings"]:
        summary["warnings"].insert(0, "WARNING: Some security controls are degraded")
        summary["warnings"].insert(0, "WARNING")
    
    return summary


def _get_rls_status(database_url: str) -> str:
    """Determine RLS status based on database configuration.

    Returns one of: ``active``, ``disabled``, ``superuser_bypass``.
    """
    if not database_url or database_url.startswith("sqlite"):
        return "disabled"

    try:
        parsed = urlparse(database_url)
        username = (parsed.username or "").lower()
    except Exception:
        username = ""

    superuser_names = {"postgres", "rdsadmin", "cloudsqladmin", "azure_superuser"}
    if username in superuser_names:
        return "superuser_bypass"

    return "active"
