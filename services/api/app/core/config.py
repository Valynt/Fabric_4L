import os
import warnings
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_DEV_SECRET = "fabric-4l-dev-secret-key-change-in-production"
_DEV_ENVIRONMENTS = {"local", "dev", "development", "test", "testing", "ci"}
_DEV_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
_EXPLICIT_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_EXPLICIT_CORS_HEADERS = ["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID"]


def _detect_environment() -> str:
    for key in ("ENVIRONMENT", "ENV", "APP_ENV"):
        val = os.getenv(key, "").strip().lower()
        if val:
            return val
    return "development"


def _is_production_like(environment: str) -> bool:
    """Return True only for the exact 'production' environment.

    This changes the previous fail-safe policy to an explicit allowlist.
    Staging and unknown/custom environments are NOT treated as production-like.
    """
    env = environment.strip().lower()
    return env == "production"


def _parse_cors_origins(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(origin).strip() for origin in value if str(origin).strip()]
    raise TypeError(
        f"Unsupported type for CORS origins: {type(value).__name__}. Expected str, list, tuple, set, or None."
    )


def _validate_exact_cors_origins(origins: list[str], *, production_like: bool) -> list[str]:
    if production_like and not origins:
        raise ValueError("cors_origins must be configured in production-like environments")

    errors: list[str] = []
    for origin in origins:
        if origin == "*" or "*" in origin:
            if production_like:
                errors.append(
                    "cors_origins cannot include wildcard origins in production-like environments"
                )
            continue
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"cors origin '{origin}' must be an explicit http(s) origin")
        if origin.lower() in {"change_me", "changeme", "null"}:
            errors.append(f"cors origin '{origin}' is not a deployable origin")

    if errors:
        raise ValueError("; ".join(errors))
    return origins


def build_cors_policy(origins: list[str], *, production_like: bool) -> dict[str, object]:
    """Return a credentials-safe, explicit CORS policy for FastAPI middleware."""
    safe_origins = _validate_exact_cors_origins(origins, production_like=production_like)
    return {
        "allow_origins": safe_origins,
        "allow_credentials": bool(safe_origins) and "*" not in safe_origins,
        "allow_methods": _EXPLICIT_CORS_METHODS,
        "allow_headers": _EXPLICIT_CORS_HEADERS,
    }


class Settings(BaseSettings):
    app_name: str = "Fabric_4L API"
    app_env: str = Field(
        default_factory=_detect_environment,
        validation_alias=AliasChoices("ENVIRONMENT", "ENV", "APP_ENV"),
    )
    debug: bool = False
    secret_key: str = _DEFAULT_DEV_SECRET
    algorithm: str = "HS256"
    jwt_issuer: str = Field(
        default="value-fabric-internal",
        validation_alias=AliasChoices("JWT_ISSUER"),
    )
    jwt_audience: str = Field(
        default="value-fabric-services",
        validation_alias=AliasChoices("JWT_AUDIENCE"),
    )
    access_token_expire_minutes: int = 60
    # Lifetime of single-use invite tokens issued by POST /v1/auth/invite.
    # Only the SHA-256 hash of a token is stored; after this many hours the
    # token is rejected even if never consumed. Default: 7 days.
    invite_token_expire_hours: int = 24 * 7
    mock_persistence: bool = False
    database_url: str | None = None
    redis_url: str | None = None
    llm_provider: str = "layer4"
    llm_model: str | None = None
    allow_mock_llm: bool = False
    layer1_api_base_url: str = Field(
        default="http://localhost:8001",
        validation_alias=AliasChoices("LAYER1_API_BASE_URL", "LAYER1_API_URL"),
    )
    layer1_timeout_seconds: float = 30.0
    layer2_api_base_url: str = Field(
        default="http://localhost:8002",
        validation_alias=AliasChoices("LAYER2_API_BASE_URL", "LAYER2_API_URL"),
    )
    layer2_timeout_seconds: float = 30.0
    layer3_api_base_url: str = Field(
        default="http://localhost:8003",
        validation_alias=AliasChoices("LAYER3_API_BASE_URL", "LAYER3_API_URL"),
    )
    layer3_timeout_seconds: float = 10.0
    layer4_api_base_url: str = Field(
        default="http://localhost:8004",
        validation_alias=AliasChoices("LAYER4_API_BASE_URL", "LAYER4_API_URL"),
    )
    layer4_timeout_seconds: float = 10.0
    layer5_api_base_url: str = Field(
        default="http://localhost:8005",
        validation_alias=AliasChoices("LAYER5_API_BASE_URL", "LAYER5_API_URL"),
    )
    layer5_timeout_seconds: float = 10.0
    layer6_api_base_url: str = Field(
        default="http://localhost:8006",
        validation_alias=AliasChoices("LAYER6_API_BASE_URL", "LAYER6_API_URL"),
    )
    layer6_timeout_seconds: float = 10.0
    delegation_timeout_seconds: float = 30.0
    # Gateway delegation resilience (P2): retry + circuit breaker for the
    # async reverse proxy. Defaults are conservative so a sustained upstream
    # outage fails closed fast instead of queuing traffic.
    delegation_retry_max_attempts: int = 3
    delegation_retry_base_delay: float = 0.2
    delegation_retry_max_delay: float = 5.0
    delegation_cb_failure_threshold: int = 5
    delegation_cb_recovery_timeout: float = 60.0
    seed_demo_data: bool = False
    # Empty list = no cross-origin requests allowed by default (fail-closed).
    # Development get_settings() supplies localhost defaults only after warning.
    cors_origins: list[str] | str = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    @property
    def is_production_like(self) -> bool:
        return _is_production_like(self.app_env)

    @field_validator("database_url", mode="before")
    @classmethod
    def reject_sqlite(cls, value: object) -> object:
        """SQLite is not supported in any environment; require PostgreSQL."""
        if isinstance(value, str) and value.startswith("sqlite"):
            raise ValueError(
                "SQLite is not supported. Configure a PostgreSQL database_url."
            )
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        """Accept a comma-separated string or a list of exact allowed origins."""
        return _parse_cors_origins(value)

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        errors: list[str] = []
        if self.is_production_like:
            if self.debug:
                errors.append("debug must be false in production-like environments")
            if self.mock_persistence:
                errors.append("mock_persistence must be false in production-like environments")
            if not self.database_url:
                errors.append("database_url must be configured in production-like environments")
            if self.llm_provider.lower() != "layer4":
                errors.append("llm_provider must be set to layer4 in production-like environments")
            if self.seed_demo_data:
                errors.append("seed_demo_data must be false in production-like environments")
            if self.secret_key == _DEFAULT_DEV_SECRET or len(self.secret_key) < 32:
                errors.append("SECRET_KEY must be replaced with a strong production secret")
            if not self.jwt_issuer.strip():
                errors.append("JWT_ISSUER must be configured in production-like environments")
            if not self.jwt_audience.strip():
                errors.append("JWT_AUDIENCE must be configured in production-like environments")
            if self.algorithm.upper() == "HS256":
                errors.append("algorithm must not be HS256 in production-like environments; use RS256 or stronger")

        try:
            _validate_exact_cors_origins(self.cors_origins, production_like=self.is_production_like)
        except ValueError as exc:
            errors.append(str(exc))

        if errors:
            raise ValueError("Unsafe production configuration: " + "; ".join(errors))
        return self

    @property
    def cors_policy(self) -> dict[str, object]:
        return build_cors_policy(self.cors_origins, production_like=self.is_production_like)


@lru_cache
def get_settings() -> Settings:
    try:
        settings = Settings()
    except Exception as exc:
        if "Unsafe production configuration" in str(exc):
            raise RuntimeError("unsafe_production_configuration") from exc
        raise

    if settings.is_production_like:
        return settings

    if not settings.cors_origins:
        warnings.warn(
            "CORS_ORIGINS not set — defaulting to localhost dev origins. "
            "Set CORS_ORIGINS explicitly before deploying.",
            RuntimeWarning,
            stacklevel=2,
        )
        settings.cors_origins = list(_DEV_CORS_ORIGINS)

    return settings
