"""Configuration for Layer 5 Ground Truth service."""

import logging
import warnings
from functools import lru_cache
from typing import ClassVar
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PRODUCTION_LIKE_ENVIRONMENTS = {"production", "prod", "staging", "stage"}
LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1"}
WEAK_JWT_SECRETS = {
    "changeme-in-production",
    "changeme",
    "password",
    "password123",
    "admin",
    "secret",
    "jwt-secret",
    "default",
    "test",
    "",
    "null",
    "none",
    "123456",
    "12345678",
    "qwerty",
    "abc123",
}


def _normalize_environment(value: str | None) -> str:
    """Normalize an environment name for production-policy decisions."""
    return (value or "development").strip().lower()


def is_production_like_environment(value: str | None) -> bool:
    """Return True for production or staging environments.

    Per the launch-readiness gate, staging and stage are treated as
    production-like and must enforce the same fail-closed controls.
    """
    return _normalize_environment(value) in PRODUCTION_LIKE_ENVIRONMENTS


def _parse_cors_origins(raw: str) -> list[str]:
    """Parse the comma-separated CORS origin contract used by deployment env vars."""
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _is_local_database_url(raw_url: str) -> bool:
    """Return whether a database URL points at localhost or SQLite."""
    parsed = urlparse(raw_url)
    if parsed.scheme.startswith("sqlite"):
        return True
    return (parsed.hostname or "").strip().lower() in LOCALHOST_HOSTS


def _has_default_database_credentials(raw_url: str) -> bool:
    """Return whether a database URL still uses common placeholder credentials."""
    parsed = urlparse(raw_url)
    username = (parsed.username or "").strip().lower()
    password = parsed.password or ""
    return username in {"postgres", "valuefabric", "value_fabric"} or password in {"", "postgres", "password"}


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    app_env: str | None = Field(default=None, alias="APP_ENV")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")  # nosec B104
    api_port: int = Field(default=8005, alias="API_PORT")
    api_workers: int = Field(default=1, alias="API_WORKERS")
    api_version: str = Field(default="v1", alias="API_VERSION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="DEBUG")
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    # PostgreSQL Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./ground_truth.db",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="sqlite:///./ground_truth.db",
        alias="DATABASE_URL_SYNC",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_pre_ping: bool = Field(default=True, alias="DB_POOL_PRE_PING")
    db_pool_recycle: int = Field(default=3600, alias="DB_POOL_RECYCLE")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    redis_rate_limiting_required: bool = Field(
        default=False,
        alias="REDIS_RATE_LIMITING_REQUIRED",
        description="Require Redis-backed rate limiting during startup.",
    )
    redis_cache_ttl_seconds: int = Field(
        default=3600,
        alias="REDIS_CACHE_TTL_SECONDS",
        description="Default TTL for cached reference data in seconds (1 hour)",
    )
    vault_addr: str | None = Field(
        default=None,
        alias="VAULT_ADDR",
        description="Optional Vault address used for production-like startup health checks.",
    )

    # Layer 3 Knowledge Graph Integration
    layer3_base_url: str = Field(
        default="http://localhost:8003",
        alias="LAYER3_BASE_URL",
    )
    layer3_api_key: str | None = Field(default=None, alias="LAYER3_API_KEY")
    layer3_timeout_seconds: int = Field(default=30, alias="LAYER3_TIMEOUT_SECONDS")
    layer3_sync_enabled: bool = Field(default=True, alias="LAYER3_SYNC_ENABLED")

    # Validation Configuration
    min_sources_for_validated: int = Field(
        default=2,
        alias="MIN_SOURCES_FOR_VALIDATED",
        description="Minimum distinct sources required to advance to VALIDATED status",
    )
    min_confidence_for_validated: float = Field(
        default=0.6,
        alias="MIN_CONFIDENCE_FOR_VALIDATED",
        description="Minimum confidence score to advance from PROPOSED to VALIDATED",
    )
    auto_advance_to_validated: bool = Field(
        default=True,
        alias="AUTO_ADVANCE_TO_VALIDATED",
        description="Automatically advance to VALIDATED when confidence threshold is met",
    )

    # Freshness Configuration
    default_freshness_days: int = Field(
        default=90,
        alias="DEFAULT_FRESHNESS_DAYS",
        description="Default number of days before a truth object is considered stale",
    )
    stale_warning_days: int = Field(
        default=75,
        alias="STALE_WARNING_DAYS",
        description="Days before expiry to start emitting staleness warnings",
    )

    # Tenant Configuration
    default_tenant_id: str = Field(
        default="default",
        alias="DEFAULT_TENANT_ID",
    )

    # JWT / Auth Configuration
    jwt_secret: str = Field(
        default="",
        alias="JWT_SECRET",
        description="HMAC secret for signing/verifying JWTs",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        alias="JWT_ALGORITHM",
    )
    jwt_issuer: str = Field(
        default="value-fabric-internal",
        alias="JWT_ISSUER",
        description="Expected JWT issuer for Layer 5 auth",
    )
    jwt_audience: str = Field(
        default="value-fabric-services",
        alias="JWT_AUDIENCE",
        description="Expected JWT audience for Layer 5 auth",
    )
    jwt_tenant_claim: str = Field(
        default="tenant_id",
        alias="JWT_TENANT_CLAIM",
        description="JWT claim key that holds the tenant/organization UUID",
    )
    jwt_user_claim: str = Field(
        default="sub",
        alias="JWT_USER_CLAIM",
        description="JWT claim key that holds the user identity",
    )
    jwt_roles_claim: str = Field(
        default="roles",
        alias="JWT_ROLES_CLAIM",
        description="JWT claim key that holds the user roles list",
    )
    # When true, a missing/invalid JWT falls back to the tenant_id query param
    # (useful for local dev and integration tests). Set false in production.
    jwt_fallback_to_query_param: bool = Field(
        default=False,
        alias="JWT_FALLBACK_TO_QUERY_PARAM",
    )
    allow_insecure_dev_auth_bypass: bool = Field(
        default=False,
        alias="ALLOW_INSECURE_DEV_AUTH_BYPASS",
    )

    # Service-to-service auth shared secret — matches GovernanceMiddleware
    # SERVICE_AUTH_HEADER validation (X-Service-Auth). Required in
    # production-like runtimes; empty in dev lets GovernanceMiddleware reject
    # any ``X-Tenant-ID`` header fallback by design (see middleware.py).
    service_auth_secret: str = Field(
        default="",
        alias="SERVICE_AUTH_SECRET",
        description=(
            "Shared secret for X-Service-Auth header used for service-to-service "
            "X-Tenant-ID handoffs. Minimum 32 characters in production-like envs."
        ),
    )

    # Minimum length must stay in sync with
    # ``value_fabric.shared.identity.middleware.MIN_SERVICE_SECRET_LENGTH`` (32).
    _MIN_SERVICE_AUTH_SECRET_LENGTH: ClassVar[int] = 32

    @property
    def effective_environment(self) -> str:
        """Return the environment value used for production-like policy checks."""
        return _normalize_environment(self.app_env or self.environment)

    @property
    def is_production_like(self) -> bool:
        """Whether this settings object represents a production-like runtime."""
        return is_production_like_environment(self.effective_environment)

    @property
    def cors_origin_list(self) -> list[str]:
        """Return parsed CORS origins after trimming empty entries."""
        return _parse_cors_origins(self.cors_origins)

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        """Treat only explicit boolean strings as DEBUG=true/false.

        Some deployment shells expose release channel labels through DEBUG.
        Those labels must not crash settings import, and they must not enable
        debug mode.
        """
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off", "", "release", "prod", "production", "staging"}:
                return False
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses asyncpg driver."""
        if "postgresql://" in v and "asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://")
        return v




    @field_validator("layer3_base_url")
    @classmethod
    def validate_layer3_base_url(cls, v: str) -> str:
        """Ensure Layer 3 base URL is an absolute HTTP(S) origin without path/query."""
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("LAYER3_BASE_URL must use http or https")
        if not parsed.netloc:
            raise ValueError("LAYER3_BASE_URL must include a hostname")
        if parsed.path not in {"", "/"}:
            raise ValueError("LAYER3_BASE_URL must not include a path")
        if parsed.params or parsed.query or parsed.fragment:
            raise ValueError("LAYER3_BASE_URL must not include params, query, or fragment")
        return v.rstrip("/")

    @model_validator(mode="after")
    def warn_on_non_production_auth_risk(self) -> "Settings":
        """Emit explicit warning when non-production starts without strong JWT auth."""
        if self.is_production_like:
            return self

        if len(self.jwt_secret) < 32 or self.jwt_secret.strip().lower() in WEAK_JWT_SECRETS:
            logger.warning(
                "Layer 5 running in %s with weak or missing JWT_SECRET; set JWT_SECRET to at least 32 random "
                "characters to enable JWT auth verification.",
                self.effective_environment,
            )

        return self

    @model_validator(mode="after")
    def validate_production_fail_closed(self) -> "Settings":
        """Reject unsafe production-like configuration before app startup."""
        if not self.is_production_like:
            if self.effective_environment == "development" and self.allow_insecure_dev_auth_bypass:
                warnings.warn(
                    "ALLOW_INSECURE_DEV_AUTH_BYPASS is enabled in development; authentication bypass may be active.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            return self

        errors: list[str] = []
        layer3_host = (urlparse(self.layer3_base_url).hostname or "").strip().lower()
        if self.debug:
            errors.append("DEBUG must be false")
        if len(self.jwt_secret) < 32 or self.jwt_secret.strip().lower() in WEAK_JWT_SECRETS:
            errors.append("JWT_SECRET must be a non-placeholder value of at least 32 characters")
        if self.jwt_algorithm.upper() == "HS256":
            errors.append("JWT_ALGORITHM must not be HS256 in production-like environments; use RS256 or stronger")
        if not self.jwt_issuer.strip():
            errors.append("JWT_ISSUER must be configured")
        if not self.jwt_audience.strip():
            errors.append("JWT_AUDIENCE must be configured")
        if self.jwt_fallback_to_query_param:
            errors.append("JWT_FALLBACK_TO_QUERY_PARAM must be false")
        if self.allow_insecure_dev_auth_bypass:
            errors.append("ALLOW_INSECURE_DEV_AUTH_BYPASS must be false")
        if self.default_tenant_id.strip().lower() == "default":
            errors.append("DEFAULT_TENANT_ID must not use the implicit 'default' fallback tenant")
        # SERVICE_AUTH_SECRET must be present and meet the GovernanceMiddleware
        # minimum length in any production-like runtime so cross-service
        # X-Tenant-ID handoffs cannot bypass HMAC verification.
        if len(self.service_auth_secret) < self._MIN_SERVICE_AUTH_SECRET_LENGTH:
            errors.append(
                "SERVICE_AUTH_SECRET must be set to a value of at least "
                f"{self._MIN_SERVICE_AUTH_SECRET_LENGTH} characters"
            )
        elif self.service_auth_secret.strip().lower() in WEAK_JWT_SECRETS:
            errors.append("SERVICE_AUTH_SECRET must not be a known placeholder value")
        if _is_local_database_url(self.database_url) or _has_default_database_credentials(self.database_url):
            errors.append("DATABASE_URL must point to non-local PostgreSQL with non-default credentials")
        if _is_local_database_url(self.database_url_sync) or _has_default_database_credentials(self.database_url_sync):
            errors.append("DATABASE_URL_SYNC must point to non-local PostgreSQL with non-default credentials")
        if layer3_host in LOCALHOST_HOSTS:
            errors.append("LAYER3_BASE_URL must not point to localhost in production-like environments")

        origins = _parse_cors_origins(self.cors_origins)
        if not origins:
            errors.append("CORS_ORIGINS must list exact trusted origins")
        elif "*" in origins:
            errors.append("CORS_ORIGINS must not contain wildcard '*' origins")

        if errors:
            raise ValueError(
                "Layer 5 production configuration is not fail-closed for "
                f"{self.effective_environment}: " + "; ".join(errors)
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
