"""Configuration management for Layer 1 Ingestion Service."""

import logging
import os
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from value_fabric.shared.secrets import load_infisical_secrets
except ImportError:
    def load_infisical_secrets() -> None:
        """No-op fallback if shared package not available."""
        pass

logger = logging.getLogger(__name__)

_DEV_ENVIRONMENTS = {"local", "dev", "development", "test", "testing", "ci"}
_DEV_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
_EXPLICIT_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_EXPLICIT_CORS_HEADERS = ["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID"]
_PRIVATE_CLUSTER_DNS_SUFFIXES = (".svc", ".svc.cluster.local", ".cluster.local", ".internal")


def detect_environment() -> str:
    for key in ("ENVIRONMENT", "ENV", "APP_ENV"):
        value = os.getenv(key, "").strip().lower()
        if value:
            return value
    return "development"


def is_production_like_environment(environment: str | None = None) -> bool:
    """Return True only for the exact 'production' environment.

    This changes the previous fail-safe policy to an explicit allowlist.
    Staging and unknown/custom environments are NOT treated as production-like.
    Callers that need staging-specific gating should use is_strict_environment()
    from value_fabric.shared.security.config instead.
    """
    env = (environment or detect_environment()).strip().lower()
    return env == "production"


def _default_jwt_secret() -> str:
    if is_production_like_environment():
        raise RuntimeError("JWT_SECRET must be set in production-like environments")
    return "local-development-only-jwt-secret-not-for-production"


def parse_cors_origins(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(origin).strip() for origin in value if str(origin).strip()]
    raise TypeError(f"Unsupported type for CORS origins: {type(value).__name__}. Expected str, list, tuple, set, or None.")


def parse_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    raise TypeError(f"Unsupported type for string list: {type(value).__name__}. Expected str, list, tuple, set, or None.")


def _is_private_cluster_hostname(hostname: str) -> bool:
    lower = hostname.lower()
    return any(lower.endswith(suffix) for suffix in _PRIVATE_CLUSTER_DNS_SUFFIXES)


def validate_exact_cors_origins(origins: list[str], *, production_like: bool) -> list[str]:
    if production_like and not origins:
        raise ValueError("CORS_ORIGINS must be set to at least one specific origin in production-like environments")

    errors: list[str] = []
    for origin in origins:
        if origin == "*" or "*" in origin:
            if production_like:
                errors.append("Wildcard CORS origin not allowed in production-like environments")
            continue
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"CORS origin '{origin}' must be an explicit http(s) origin")
        if origin.lower() in {"change_me", "changeme", "null"}:
            errors.append(f"CORS origin '{origin}' is not a deployable origin")

    if errors:
        raise ValueError("; ".join(errors))
    return origins


def build_cors_policy(origins: list[str], *, production_like: bool) -> dict[str, Any]:
    safe_origins = validate_exact_cors_origins(origins, production_like=production_like)
    return {
        "allow_origins": safe_origins,
        "allow_credentials": bool(safe_origins) and "*" not in safe_origins,
        "allow_methods": _EXPLICIT_CORS_METHODS,
        "allow_headers": _EXPLICIT_CORS_HEADERS,
    }


# Load secrets from Infisical if available (optional in dev, required in prod-like envs)
try:
    load_infisical_secrets()
except Exception:
    if is_production_like_environment():
        raise RuntimeError("Failed to load Infisical secrets in production-like environment")


class Settings(BaseSettings):
    """Application settings loaded from environment variables with security validation."""

    # Application
    environment: str = Field(default_factory=detect_environment, description="Runtime environment")
    app_name: str = "layer1-ingestion"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Enable debug mode")

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/layer1_ingestion",
        description="PostgreSQL connection URL",
        alias="DATABASE_URL",
    )

    # JWT and Security
    jwt_secret: str = Field(default_factory=_default_jwt_secret, description="JWT signing secret")
    cors_origins: list[str] = Field(default=[], description="CORS allowed origins")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins_field(cls, v: object) -> object:
        return parse_cors_origins(v)

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_mode(cls, v: object) -> object:
        if isinstance(v, str) and v.strip().lower() == "release":
            return False
        return v

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        production_like = is_production_like_environment(self.environment)
        errors: list[str] = []

        if production_like:
            redis_url = self.redis_url.strip()
            s3_endpoint = self.s3_endpoint.strip()
            s3_access_key = (self.s3_access_key or "").strip()
            s3_secret_key = (self.s3_secret_key or "").strip()

            if self.debug:
                errors.append("Debug mode must be disabled in production-like environments")
            insecure_defaults = ["changeme", "changeme-in-production", "valuefabric", "postgres", "secret", "password"]
            if self.jwt_secret.lower() in insecure_defaults:
                errors.append("Insecure default JWT secret detected in production-like environment")
            if len(self.jwt_secret) < 32:
                errors.append("JWT secret must be >= 32 characters in production-like environments")
            if "postgres:postgres@" in self.database_url or "password" in self.database_url.lower():
                errors.append("Database URL contains default/insecure credentials")
            parsed_redis = urlparse(redis_url)
            redis_host = (parsed_redis.hostname or "").lower()
            if not redis_url:
                errors.append(
                    "REDIS_URL must be set in production-like environments. "
                    "Configure REDIS_URL to a managed Redis endpoint with authentication/TLS from your secret manager."
                )
            elif self.redis_url.strip() == "redis://localhost:6379/0":
                errors.append(
                    "REDIS_URL is using default localhost value 'redis://localhost:6379/0'. "
                    "Set REDIS_URL to a managed Redis endpoint with authentication/TLS for production deployment."
                )
            elif parsed_redis.scheme not in {"redis", "rediss"} or not parsed_redis.hostname:
                errors.append(
                    "REDIS_URL is invalid for a production-like environment. "
                    "Use a full redis:// or rediss:// endpoint with a hostname, credentials, and TLS where supported."
                )
            elif redis_host in {"localhost", "127.0.0.1", "::1"}:
                errors.append(
                    "REDIS_URL cannot target localhost in production-like environments. "
                    "Point REDIS_URL at the managed Redis service reachable from the deployment environment."
                )
            if not s3_access_key or not s3_secret_key:
                errors.append(
                    "S3_ACCESS_KEY and S3_SECRET_KEY must be set in production-like environments. "
                    "Load non-placeholder object storage credentials from your secret manager."
                )
            elif s3_access_key.lower() == "minioadmin" or s3_secret_key.lower() == "minioadmin":
                errors.append(
                    "S3 credentials use default placeholder value 'minioadmin'. "
                    "Set S3_ACCESS_KEY and S3_SECRET_KEY to production credentials from your secret manager."
                )
            parsed_endpoint = urlparse(s3_endpoint)
            if not parsed_endpoint.scheme or not parsed_endpoint.hostname:
                errors.append(
                    "S3_ENDPOINT is missing or invalid. "
                    "Set S3_ENDPOINT to a valid https:// endpoint (or allowlisted private cluster DNS endpoint)."
                )
            else:
                endpoint_host = parsed_endpoint.hostname.lower()
                endpoint_is_localhost = endpoint_host in {"localhost", "127.0.0.1", "::1"}
                endpoint_is_tls = parsed_endpoint.scheme.lower() == "https"
                allowlisted_hosts = {host.lower() for host in self.private_storage_endpoint_allowlist}
                allowlisted_private = endpoint_host in allowlisted_hosts and _is_private_cluster_hostname(endpoint_host)
                if endpoint_is_localhost:
                    errors.append(
                        "S3_ENDPOINT cannot target localhost in production-like environments. "
                        "Use an internal object storage endpoint reachable by the cluster."
                    )
                elif not endpoint_is_tls and not allowlisted_private:
                    errors.append(
                        "S3_ENDPOINT must use TLS (https) in production-like environments. "
                        "For private-cluster exceptions, add the exact private DNS hostname to "
                        "PRIVATE_STORAGE_ENDPOINT_ALLOWLIST."
                    )

        try:
            validate_exact_cors_origins(self.cors_origins, production_like=production_like)
        except ValueError:
            errors.append("config_validation_failed")

        if errors:
            raise ValueError("Unsafe production configuration: " + "; ".join(errors))
        return self

    @property
    def is_production_like(self) -> bool:
        return is_production_like_environment(self.environment)

    @property
    def cors_policy(self) -> dict[str, Any]:
        origins = self.cors_origins
        if not origins and not self.is_production_like:
            logger.warning(
                "CORS_ORIGINS not configured in non-production environment, "
                f"falling back to dev defaults: {_DEV_CORS_ORIGINS}. "
                "Set CORS_ORIGINS environment variable to avoid this warning."
            )
            origins = list(_DEV_CORS_ORIGINS)
        return build_cors_policy(origins, production_like=self.is_production_like)

    # Redis (Celery broker and cache)
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # Storage (MinIO/S3)
    s3_endpoint: str = Field(default="http://localhost:9000", description="S3/MinIO endpoint")
    s3_access_key: str | None = Field(default=None, description="S3 access key (required in production-like environments)", alias="LAYER1_S3_ACCESS_KEY")
    s3_secret_key: str | None = Field(default=None, description="S3 secret key (required in production-like environments)", alias="LAYER1_S3_SECRET_KEY")
    s3_bucket: str = Field(default="layer1-raw-html", description="S3 bucket for raw HTML")
    s3_region: str = Field(default="us-east-1", description="S3 region")
    private_storage_endpoint_allowlist: list[str] = Field(
        default=[],
        description="Allowlisted private-cluster storage hostnames allowed to use non-TLS endpoints in production-like environments.",
    )

    @field_validator("private_storage_endpoint_allowlist", mode="before")
    @classmethod
    def parse_storage_allowlist(cls, v: object) -> object:
        return parse_string_list(v)

    # Crawler settings
    max_concurrent_pages: int = Field(default=5, description="Max concurrent pages per worker")
    page_timeout_ms: int = Field(default=30000, description="Page load timeout in milliseconds")
    navigation_timeout_ms: int = Field(default=10000, description="Navigation timeout in milliseconds")
    default_crawl_depth: int = Field(default=2, description="Default crawl depth")
    max_crawl_depth: int = Field(default=5, description="Maximum crawl depth")

    # Rate limiting
    global_requests_per_minute: int = Field(default=1000, description="Global rate limit")
    per_domain_delay_seconds: float = Field(default=1.0, description="Delay between requests to same domain")
    jitter_percent: float = Field(default=20.0, description="Random jitter percentage for delays")

    # Queue settings
    queue_batch_size: int = Field(default=100, description="Number of URLs to process in batch")
    max_retries: int = Field(default=3, description="Max retries for failed URLs")
    retry_delay_seconds: int = Field(default=60, description="Base retry delay")

    # SEC EDGAR
    sec_edgar_rate_limit: int = Field(default=10, description="Requests per second (SEC limit)")
    sec_edgar_user_agent: str = Field(default="ValueFabric/1.0 (contact@valuefabric.io)")
    sec_edgar_cache_ttl_hours: int = Field(default=24)

    # USPTO Patents
    uspto_api_key: str | None = Field(default=None)
    uspto_rate_limit: int = Field(default=5, description="Requests per second")

    # News sources
    news_source: str = Field(default="gdelt", description="News source: 'gdelt' or 'newsapi'")
    newsapi_key: str | None = Field(default=None)

    # Compliance
    retention_days: int = Field(default=30, description="Raw HTML retention period")
    audit_log_retention_years: int = Field(default=7, description="Audit log retention")
    pii_threshold_flag: float = Field(default=0.3, description="PII detection threshold for flagging")
    pii_threshold_quarantine: float = Field(default=0.7, description="PII detection threshold for quarantine")
    robots_txt_cache_hours: int = Field(default=24, description="robots.txt cache TTL")
    robots_txt_strict_mode: bool = Field(default=False, description="Deprecated: use strict_robots_enforcement")
    strict_robots_enforcement: bool = Field(
        default=False,
        description="If True, robots.txt fetch/parse failures block crawling instead of allowing",
    )

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API server host")  # nosec B104
    api_port: int = Field(default=8000, description="API server port")

    # Layer 2 integration
    layer2_api_url: str = Field(default="http://layer2:8000", description="Layer 2 extraction API URL")
    layer2_celery_broker_url: str = Field(default="redis://redis:6379/0", description="Layer 2 Celery broker URL for task dispatch")
    use_celery_for_l2: bool = Field(default=True, description="Use Celery for L2 dispatch instead of HTTP")

    # LLM Providers (for AI_LLM extraction method)
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model for extraction")
    openai_timeout_seconds: int = Field(default=60, description="OpenAI API timeout")

    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model")
    anthropic_timeout_seconds: int = Field(default=60, description="Anthropic API timeout")

    azure_openai_api_key: str | None = Field(default=None, description="Azure OpenAI API key")
    azure_openai_endpoint: str | None = Field(default=None, description="Azure OpenAI endpoint")
    azure_openai_deployment: str | None = Field(default=None, description="Azure OpenAI deployment name")

    # Pipeline settings
    pipeline_stage_timeout_seconds: int = Field(default=300, description="Timeout per pipeline stage")
    max_pipeline_retries: int = Field(default=3, description="Max retries per pipeline stage")

    model_config = SettingsConfigDict(populate_by_name=True)


# Global settings instance
settings = Settings()
