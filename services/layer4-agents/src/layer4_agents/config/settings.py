from __future__ import annotations

"""Layer 4 Agents Service Configuration.

P0-29: Pydantic-settings with validation for required secrets.
Fails fast on startup if required configuration is missing or invalid.
"""
import asyncio
import importlib
import importlib.util
import logging
import secrets
from functools import lru_cache
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Lazy initialization hooks — called explicitly during app lifespan startup
# to avoid import-time side effects that break tests and tooling.
_startup_dependencies_verified = False
_infisical_secrets_loaded = False


def _load_infisical_secrets_safe() -> None:
    """Load Infisical secrets if configured; never raise on missing config."""
    global _infisical_secrets_loaded
    if _infisical_secrets_loaded:
        return
    _secrets_module = (
        importlib.import_module("value_fabric.shared.secrets")
        if importlib.util.find_spec("value_fabric.shared.secrets")
        else None
    )
    load_fn = getattr(_secrets_module, "load_infisical_secrets", None)
    if load_fn is not None:
        try:
            load_fn()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Non-fatal: Infisical is optional; pydantic-settings validators
            # will catch genuinely missing production secrets at instantiation.
            logger.warning("Infisical secrets load skipped: %s", exc)
    _infisical_secrets_loaded = True


def configure_settings() -> None:
    """Run import-time side effects safely during app startup.

    Separated from module import so tests and tooling can import Settings
    without a full runtime environment.
    """
    global _startup_dependencies_verified
    if not _startup_dependencies_verified:
        from ..startup.dependency_verifier import verify_layer4_startup_dependencies

        verify_layer4_startup_dependencies()
        _startup_dependencies_verified = True
    _load_infisical_secrets_safe()


from pydantic import AliasChoices, Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from value_fabric.shared.security.neo4j import validate_neo4j_aura_config

from ._billing_mixin import BillingSettingsMixin
from ._runtime_mixin import RuntimeSettingsMixin


class Settings(BillingSettingsMixin, RuntimeSettingsMixin, BaseSettings):
    """Layer 4 Agents service settings with strict validation.

    All secrets must be provided via environment variables.
    Fails fast on startup if required configuration is missing.
    """

    model_config = SettingsConfigDict(
        env_prefix="LAYER4_",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",  # Allow extra env vars without error
    )

    # ==========================================================================
    # Application
    # ==========================================================================
    app_name: str = Field(default="layer4-agents", description="Service name")
    app_version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # ==========================================================================
    # Security (P0-29: Required secrets with minimum length validation)
    # ==========================================================================
    jwt_secret: str = Field(
        default="",
        description="JWT signing secret (min 32 characters required)"
    )
    api_key_hmac_secret: str = Field(
        default="",
        description="API key HMAC secret (min 32 characters required)"
    )

    # ==========================================================================
    # Database
    # ==========================================================================
    database_url: str = Field(
        default="",
        description="PostgreSQL connection URL (required in production)"
    )
    database_pool_size: int = Field(default=10, description="Connection pool size")
    database_max_overflow: int = Field(default=20, description="Max pool overflow")

    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")

    # ==========================================================================
    # External Services
    # ==========================================================================
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key for LLM operations"
    )
    openai_model: str = Field(default="gpt-4", description="Default OpenAI model")
    openai_timeout_seconds: int = Field(default=60, description="OpenAI API timeout")

    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Default Anthropic model")
    anthropic_timeout_seconds: int = Field(default=60, description="Anthropic API timeout")

    # Together.ai
    together_api_key: str | None = Field(
        default=None,
        description="Together.ai API key for LLM operations",
    )
    together_base_url: str = Field(
        default="https://api.together.ai/v1",
        description="Together.ai API base URL (OpenAI-compatible)",
    )
    together_default_model: str = Field(
        default="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        description="Default Together.ai model when not specified by harness config",
    )
    together_timeout_seconds: int = Field(
        default=60,
        description="Together.ai API timeout in seconds",
    )

    # LLM provider selection
    llm_provider: str = Field(
        default="together",
        description=(
            "Active LLM provider: 'together' | 'openai' | 'anthropic'. "
            "Governs which provider GovernedLLMClient uses for agent workflows."
        ),
    )

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        """Reject provider typos during settings construction/startup."""
        normalized = value.strip().lower()
        supported = {"together", "openai", "anthropic"}
        if normalized not in supported:
            raise ValueError(
                "llm_provider must be one of: anthropic, openai, together; "
                "implicit provider fallback is prohibited"
            )
        return normalized

    # ==========================================================================
    # Layer Integration
    # ==========================================================================
    service_mesh_mtls_enabled: bool = Field(
        default=False,
        description="Allow in-mesh HTTP service URLs when mTLS enforcement is enabled."
    )
    allow_insecure_service_http_in_development: bool = Field(
        default=False,
        validation_alias=AliasChoices("LAYER4_ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT", "ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT"),
        description="Allow HTTP service URLs only for local development/testing."
    )
    layer1_api_url: str = Field(
        default="",
        validation_alias=AliasChoices("LAYER4_LAYER1_API_URL", "LAYER1_API_URL"),
        description="Layer 1 Ingestion API URL"
    )
    layer2_api_url: str = Field(
        default="",
        validation_alias=AliasChoices("LAYER4_LAYER2_API_URL", "LAYER2_API_URL"),
        description="Layer 2 Extraction API URL"
    )
    layer3_api_url: str = Field(
        default="",
        validation_alias=AliasChoices("LAYER4_LAYER3_API_URL", "LAYER3_API_URL"),
        description="Layer 3 Knowledge Graph API URL"
    )
    layer5_api_url: str = Field(
        default="",
        validation_alias=AliasChoices("LAYER4_LAYER5_API_URL", "LAYER5_API_URL", "LAYER5_GROUND_TRUTH_URL"),
        description="Layer 5 Ground Truth API URL"
    )
    layer6_api_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("LAYER4_LAYER6_API_BASE_URL", "LAYER6_API_BASE_URL", "LAYER6_BENCHMARKS_URL"),
        description="Layer 6 Benchmarks API URL"
    )
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        validation_alias=AliasChoices("LAYER4_NEO4J_URI", "NEO4J_URI"),
        description="Neo4j URI for graph-backed tools"
    )
    neo4j_user: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("LAYER4_NEO4J_USER", "NEO4J_USER"),
        description="Neo4j username",
    )
    neo4j_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LAYER4_NEO4J_PASSWORD", "NEO4J_PASSWORD"),
        description="Neo4j password",
    )

    # ==========================================================================
    # Workflow Engine
    # ==========================================================================
    max_concurrent_workflows: int = Field(
        default=10,
        description="Maximum concurrent workflows per replica (P1-42)"
    )
    workflow_timeout_seconds: int = Field(
        default=1800,  # 30 minutes (P1-25)
        description="Global workflow timeout (service default baseline)"
    )
    workflow_timeout_min_seconds: int = Field(
        default=60,
        description="Lower bound for resolved workflow timeout"
    )
    workflow_timeout_max_seconds: int = Field(
        default=7200,
        description="Upper bound for resolved workflow timeout"
    )
    workflow_timeout_fallback_seconds: int = Field(
        default=1800,
        description="Safe fallback when resolved timeout is invalid/out of range"
    )
    workflow_state_ttl_seconds: int = Field(
        default=86400,  # 24 hours
        description="Workflow state TTL in Redis"
    )
    agent_gate_timeout_seconds: int = Field(
        default=600,
        description=(
            "Human-in-the-loop gate timeout in seconds. "
            "Defaults to 600 seconds when unset for backward compatibility."
        ),
    )

    # ==========================================================================
    # Rate Limiting (P1-15)
    # ==========================================================================
    rate_limit_requests_per_minute: int = Field(
        default=100,
        description="Per-tenant rate limit (requests per minute)"
    )
    rate_limit_burst_size: int = Field(
        default=20,
        description="Rate limit burst size"
    )

    # ==========================================================================
    # Circuit Breaker (P1-18)
    # ==========================================================================
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Failures before opening circuit"
    )
    circuit_breaker_recovery_timeout_seconds: int = Field(
        default=60,
        description="Seconds before attempting recovery"
    )
    circuit_breaker_half_open_max_calls: int = Field(
        default=3,
        description="Max test calls in half-open state"
    )

    # ==========================================================================
    # CORS (P0-20)
    # ==========================================================================
    cors_origins: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins"
    )

    # ==========================================================================
    # Observability
    # ==========================================================================
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or text")
    otel_exporter_endpoint: str | None = Field(
        default=None,
        description="OpenTelemetry exporter endpoint (P1-29)"
    )
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Metrics server port")

    # ==========================================================================
    # Feature Flags (P2-05)
    # ==========================================================================
    feature_flag_provider: str = Field(
        default="redis",
        description="Feature flag backend: redis, config, or unleash"
    )

    oidc_state_store_backend: str = Field(
        default="redis",
        description="OIDC state store backend: redis (production default) or memory (non-production only)",
    )
    oidc_state_ttl_seconds: int = Field(
        default=300,
        description="Strict TTL for OIDC state and PKCE verifier records",
    )

    enable_oidc_cleanup: bool = Field(
        default=True,
        description="Enable OIDC session cleanup startup integration"
    )
    enable_crm_scheduler: bool = Field(
        default=True,
        description="Enable CRM sync scheduler startup integration"
    )

    # ==========================================================================
    # Billing (Stripe Integration)
    # ==========================================================================
    billing_enabled: bool = Field(
        default=False,
        description="Enable billing features and Stripe integration"
    )
    stripe_secret_key: str | None = Field(
        default=None,
        description="Stripe API secret key (sk_...)"
    )
    stripe_webhook_secret: str | None = Field(
        default=None,
        description="Stripe webhook endpoint secret (whsec_...)"
    )
    stripe_price_pro: str | None = Field(
        default=None,
        description="Stripe Price ID for Pro plan"
    )
    stripe_price_enterprise: str | None = Field(
        default=None,
        description="Stripe Price ID for Enterprise plan"
    )

    # ==========================================================================
    # Export Object Storage (S3/MinIO)
    # ==========================================================================
    export_storage_endpoint: str | None = Field(
        default=None,
        description="S3/MinIO endpoint URL for export package uploads"
    )
    export_storage_region: str = Field(
        default="us-east-1",
        description="S3 region for export object storage"
    )
    export_storage_bucket: str = Field(
        default="value-fabric-exports",
        description="Bucket for exported case artifacts"
    )
    export_storage_access_key: str = Field(
        default="",
        description="Access key for S3/MinIO export uploads"
    )
    export_storage_secret_key: str = Field(
        default="",
        description="Secret key for S3/MinIO export uploads"
    )
    export_storage_use_ssl: bool = Field(
        default=True,
        description="Whether to use TLS for object storage endpoint"
    )
    export_signed_url_ttl_seconds: int = Field(
        default=900,
        description="Signed URL TTL for export downloads in seconds"
    )

    # ==========================================================================
    # Validators (P0-29: Fail fast on invalid config)
    # ==========================================================================

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Normalize environment name."""
        v = v.lower()
        allowed = {"development", "staging", "production", "test"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{v}'")
        return v

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str, info: ValidationInfo) -> str:
        """Validate JWT secret meets minimum requirements."""
        environment = info.data.get("environment", "development")

        if environment == "production":
            if not v:
                raise ValueError(
                    "FATAL: JWT_SECRET is required in production. "
                    "Set a strong secret (min 32 characters)."
                )
            if len(v) < 32:
                raise ValueError(
                    f"FATAL: JWT_SECRET must be at least 32 characters in production, "
                    f"got {len(v)} characters."
                )

        # In non-production, generate a random secret if not provided
        if not v:
            if environment == "development":
                import warnings
                warnings.warn(
                    "JWT_SECRET not set in development. Using random secret (sessions will not persist across restarts).",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return secrets.token_urlsafe(32)
            else:
                raise ValueError(f"JWT_SECRET is required in {environment} environment")

        if len(v) < 32:
            raise ValueError(f"JWT_SECRET must be at least 32 characters, got {len(v)}")

        return v

    @field_validator("api_key_hmac_secret")
    @classmethod
    def validate_api_key_hmac_secret(cls, v: str, info: ValidationInfo) -> str:
        """Validate API key HMAC secret meets minimum requirements."""
        environment = info.data.get("environment", "development")

        if environment == "production":
            if not v:
                raise ValueError(
                    "FATAL: API_KEY_HMAC_SECRET is required in production. "
                    "Set a strong secret (min 32 characters)."
                )
            if len(v) < 32:
                raise ValueError(
                    f"FATAL: API_KEY_HMAC_SECRET must be at least 32 characters in production, "
                    f"got {len(v)} characters."
                )

        # In non-production, generate a random secret if not provided
        if not v:
            if environment == "development":
                import warnings
                warnings.warn(
                    "API_KEY_HMAC_SECRET not set in development. Using random secret (API keys will not persist across restarts).",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return secrets.token_urlsafe(32)
            else:
                raise ValueError(f"API_KEY_HMAC_SECRET is required in {environment} environment")

        if len(v) < 32:
            raise ValueError(f"API_KEY_HMAC_SECRET must be at least 32 characters, got {len(v)}")

        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str, info: ValidationInfo) -> str:
        """Validate database URL in production."""
        environment = info.data.get("environment", "development")

        if environment == "production":
            if not v or v.strip() == "":
                raise ValueError(
                    "FATAL: DATABASE_URL is required in production. "
                    "Set LAYER4_DATABASE_URL or CHECKPOINT_DATABASE_URL environment variable."
                )

            # Check for default/insecure credentials
            insecure_patterns = [
                ":postgres@",
                ":password@",
                ":admin@",
                ":secret@",
            ]
            for pattern in insecure_patterns:
                if pattern in v.lower():
                    raise ValueError(
                        f"FATAL: DATABASE_URL contains insecure default credentials '{pattern}'. "
                        "Use strong, unique passwords in production."
                    )

        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str, info: ValidationInfo) -> str:
        """Validate CORS origins in production (P0-20)."""
        environment = info.data.get("environment", "development")

        if environment == "production":
            if not v or v.strip() == "":
                raise ValueError(
                    "FATAL: CORS_ORIGINS is required in production. "
                    "Set to comma-separated list of allowed origins (e.g., 'https://app.valuefabric.io')."
                )

            origins = [o.strip() for o in v.split(",") if o.strip()]

            if "*" in origins:
                raise ValueError(
                    "FATAL: CORS_ORIGINS cannot contain '*' in production. "
                    "Specify exact allowed origins."
                )

            for origin in origins:
                if not origin.startswith(("https://", "http://")):
                    raise ValueError(
                        f"FATAL: CORS origin '{origin}' must start with http:// or https://"
                    )

        return v

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Validate OpenAI API key format if provided."""
        if v and not v.startswith(("sk-", "sk-proj-")):
            raise ValueError(
                "OPENAI_API_KEY appears invalid. Should start with 'sk-' or 'sk-proj-'."
            )
        return v

    @field_validator("layer1_api_url", "layer2_api_url", "layer3_api_url", "layer5_api_url", "layer6_api_base_url")
    @classmethod
    def validate_layer_endpoint_url(cls, v: str, info: ValidationInfo) -> str:
        """Validate Layer 1/2/3/5/6 endpoint URLs with environment-aware transport rules."""
        if not info.field_name:
            raise ValueError("field_name is required for URL validation")
        field_name = info.field_name.upper()

        # The field defaults are intentionally empty strings. When a value is
        # not configured (empty / whitespace-only), skip format validation —
        # the production-readiness gates already verify that every required
        # endpoint URL is populated before deploy. This lets Settings be
        # constructed for unit tests and non-production tooling without
        # forcing every layer endpoint to be wired.
        if not v or not v.strip():
            return v

        endpoint = v.strip()
        parsed = urlparse(endpoint)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            raise ValueError(
                f"FATAL: {field_name} must use http:// or https://, got '{endpoint}'."
            )

        environment = info.data.get("environment", "development")
        mesh_mtls_enabled = info.data.get("service_mesh_mtls_enabled", False)
        allow_dev_http = info.data.get("allow_insecure_service_http_in_development", False)

        if scheme == "https":
            return endpoint

        if mesh_mtls_enabled:
            return endpoint

        if environment in {"development", "test"} and allow_dev_http:
            return endpoint

        if environment in {"development", "test"}:
            raise ValueError(
                f"FATAL: {field_name} uses insecure HTTP. "
                "Set ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT=true for local-only usage, "
                "or configure HTTPS/service-mesh mTLS."
            )

        raise ValueError(
            f"FATAL: {field_name} must use HTTPS in {environment}, "
            "or enable validated service-mesh mTLS mode."
        )

    @field_validator("oidc_state_store_backend")
    @classmethod
    def validate_oidc_state_store_backend(cls, v: str) -> str:
        backend = v.strip().lower()
        if backend not in {"redis", "memory"}:
            raise ValueError("oidc_state_store_backend must be one of: redis, memory")
        return backend

    @field_validator("oidc_state_ttl_seconds")
    @classmethod
    def validate_oidc_state_ttl_seconds(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("oidc_state_ttl_seconds must be positive")
        return v

    @model_validator(mode="after")
    def validate_prod_neo4j_aura(self) -> Settings:
        """Production/staging must use managed Aura, not in-cluster Neo4j.

        Kept on Settings because it depends on both runtime (environment,
        oidc_state_store_backend) and Neo4j (neo4j_uri, neo4j_password) fields.
        """
        validate_neo4j_aura_config(
            uri=self.neo4j_uri,
            password=self.neo4j_password,
            environment=self.environment,
        )
        if self.environment in {"production", "staging"} and self.oidc_state_store_backend != "redis":
            raise ValueError(
                "FATAL: OIDC state store backend must be 'redis' in production/staging."
            )
        return self

# ==========================================================================
# Lazy Settings Accessor (P2-002)
# ==========================================================================

# Use lazy accessor to avoid import-time side effects.
# Call configure_settings() during app lifespan startup before first use.
@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (created on first call)."""
    return Settings()


class _SettingsProxy:
    """Lazy compatibility proxy for legacy direct ``settings`` imports."""

    def __getattr__(self, name: str) -> object:
        return getattr(get_settings(), name)


settings = _SettingsProxy()
