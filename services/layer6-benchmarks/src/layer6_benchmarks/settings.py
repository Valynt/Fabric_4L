from __future__ import annotations

import warnings
from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlparse

from pydantic import (
    AliasChoices,
    Field,
    SecretStr,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from value_fabric.shared.security.neo4j import (
    INSECURE_NEO4J_PASSWORDS,
    is_production_like_environment,
    validate_neo4j_aura_config,
)

_ALLOWED_PG_SSL_MODES = {"require", "verify-ca", "verify-full"}
_WEAK_SECRET_VALUES = frozenset(
    {
        "",
        "changeme",
        "change_me",
        "change-me",
        "password",
        "secret",
        "default",
        "test",
        "placeholder",
    }
)


class Layer6Settings(BaseSettings):
    """Canonical Layer 6 runtime settings with fail-closed validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    environment: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "ENV", "APP_ENV"),
    )
    testing: bool = Field(default=False, alias="TESTING")
    auth_required: bool = Field(default=True, alias="AUTH_REQUIRED")

    database_url: str = Field(alias="DATABASE_URL")
    database_url_sync: str = Field(alias="DATABASE_URL_SYNC")
    db_host: str | None = Field(default=None, alias="DB_HOST")
    db_port: int | None = Field(default=None, alias="DB_PORT", ge=1, le=65535)
    db_name: str | None = Field(default=None, alias="DB_NAME")
    db_user: str | None = Field(default=None, alias="DB_USER")
    db_password: SecretStr | None = Field(default=None, alias="DB_PASSWORD")

    neo4j_uri: str = Field(alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER", min_length=1)
    neo4j_password: SecretStr = Field(alias="NEO4J_PASSWORD", min_length=12)
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE", min_length=1)
    neo4j_max_pool_size: int = Field(default=50, alias="NEO4J_MAX_POOL_SIZE", ge=1, le=200)

    jwt_secret: SecretStr = Field(alias="JWT_SECRET", min_length=32)
    api_key_hmac_secret: SecretStr = Field(alias="API_KEY_HMAC_SECRET", min_length=32)
    service_auth_secret: SecretStr = Field(alias="SERVICE_AUTH_SECRET", min_length=32)
    layer3_api_key: SecretStr = Field(alias="LAYER3_API_KEY", min_length=16)
    layer5_api_key: SecretStr = Field(alias="LAYER5_API_KEY", min_length=16)

    # Canonical auth bypass flag — use this in all new code.
    allow_insecure_dev_auth_bypass: bool = Field(default=False, alias="ALLOW_INSECURE_DEV_AUTH_BYPASS")

    # Deprecated aliases — kept for backward compatibility with existing deployments.
    # These emit DeprecationWarning at startup if set. Migrate to ALLOW_INSECURE_DEV_AUTH_BYPASS.
    dev_auth_bypass: bool = Field(default=False, alias="DEV_AUTH_BYPASS")
    auth_bypass_enabled: bool = Field(default=False, alias="AUTH_BYPASS_ENABLED")
    allow_dev_auth_bypass: str | None = Field(default=None, alias="ALLOW_DEV_AUTH_BYPASS")

    jwt_fallback_to_query_param: bool = Field(default=False, alias="JWT_FALLBACK_TO_QUERY_PARAM")
    allow_ephemeral_encryption: bool = Field(default=False, alias="ALLOW_EPHEMERAL_ENCRYPTION")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8006, alias="API_PORT", ge=1, le=65535)
    port: int = Field(default=8006, alias="PORT", ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )
    layer6_service_name: str = Field(default="layer6-benchmarks", alias="LAYER6_SERVICE_NAME", min_length=1)
    layer6_version: str = Field(default="dev", alias="LAYER6_VERSION", min_length=1)
    layer6_build_sha: str = Field(default="unknown", alias="LAYER6_BUILD_SHA", min_length=1)

    @property
    def neo4j_auth(self) -> tuple[str, str]:
        return (self.neo4j_user, self.neo4j_password.get_secret_value())

    @field_validator("database_url", "database_url_sync")
    @classmethod
    def _validate_database_url(cls, value: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "DATABASE_URL"
        env_var = "DATABASE_URL_SYNC" if field_name == "database_url_sync" else "DATABASE_URL"
        if not value.startswith(("postgresql://", "postgresql+")):
            raise ValueError(f"{env_var} must target PostgreSQL")

        env = info.data.get("environment", "development")
        if env in {"staging", "production"}:
            sslmodes = [
                sslmode.strip().lower()
                for key, sslmode in parse_qsl(urlparse(value).query, keep_blank_values=True)
                if key.lower() == "sslmode"
            ]
            if not sslmodes:
                raise ValueError(f"{env_var} must include sslmode in staging/production")
            if sslmodes[-1] not in _ALLOWED_PG_SSL_MODES:
                raise ValueError(f"{env_var} sslmode must be require, verify-ca, or verify-full")
        return value

    @field_validator("jwt_secret", "api_key_hmac_secret", "service_auth_secret", "layer3_api_key", "layer5_api_key")
    @classmethod
    def _reject_weak_secrets(cls, value: SecretStr, info: ValidationInfo) -> SecretStr:
        raw_value = value.get_secret_value().strip()
        normalized = raw_value.lower()
        if normalized in _WEAK_SECRET_VALUES or normalized.startswith("change"):
            field_name = (info.field_name or "secret").upper()
            raise ValueError(f"{field_name} must not use a placeholder or weak default value")
        return value

    @field_validator("neo4j_password")
    @classmethod
    def _validate_neo4j_password(cls, value: SecretStr) -> SecretStr:
        raw_value = value.get_secret_value().strip()
        if raw_value.lower() in INSECURE_NEO4J_PASSWORDS:
            raise ValueError("NEO4J_PASSWORD must be a strong non-default secret")
        return value

    @field_validator("neo4j_uri")
    @classmethod
    def _validate_neo4j_uri(cls, value: str, info: ValidationInfo) -> str:
        env = info.data.get("environment", "development")
        if env in {"staging", "production"}:
            validate_neo4j_aura_config(
                uri=value,
                password="placeholder-validation-secret",
                environment=env,
            )
        return value

    @model_validator(mode="after")
    def _warn_deprecated_bypass_flags(self) -> "Layer6Settings":
        """Emit DeprecationWarning for legacy auth bypass env vars and fold them
        into the canonical ``allow_insecure_dev_auth_bypass`` flag.

        Canonical flag: ``ALLOW_INSECURE_DEV_AUTH_BYPASS``
        Deprecated:     ``DEV_AUTH_BYPASS``, ``AUTH_BYPASS_ENABLED``, ``ALLOW_DEV_AUTH_BYPASS``
        """
        legacy_active: list[str] = []
        if self.dev_auth_bypass:
            legacy_active.append("DEV_AUTH_BYPASS")
        if self.auth_bypass_enabled:
            legacy_active.append("AUTH_BYPASS_ENABLED")
        if (self.allow_dev_auth_bypass or "").strip().lower() == "i_understand_risk":
            legacy_active.append("ALLOW_DEV_AUTH_BYPASS")

        if legacy_active:
            warnings.warn(
                f"Layer 6: deprecated auth bypass flag(s) set: {', '.join(legacy_active)}. "
                "Migrate to ALLOW_INSECURE_DEV_AUTH_BYPASS. "
                "These flags will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            # Fold into canonical flag so downstream code only checks one field.
            object.__setattr__(self, "allow_insecure_dev_auth_bypass", True)

        return self

    @model_validator(mode="after")
    def _validate_cross_field_constraints(self) -> "Layer6Settings":
        if self.api_port != self.port:
            raise ValueError("API_PORT and PORT must match when both are configured")

        if self.environment in {"staging", "production"}:
            if not self.auth_required:
                raise ValueError("AUTH_REQUIRED must remain true in staging/production")

            validate_neo4j_aura_config(
                uri=self.neo4j_uri,
                password=self.neo4j_password.get_secret_value(),
                environment=self.environment,
            )

            # Legacy flags are folded into allow_insecure_dev_auth_bypass by
            # _warn_deprecated_bypass_flags, so only the canonical flag needs checking here.
            active_flags: list[str] = []
            if self.allow_insecure_dev_auth_bypass:
                active_flags.append("ALLOW_INSECURE_DEV_AUTH_BYPASS")
            if self.jwt_fallback_to_query_param:
                active_flags.append("JWT_FALLBACK_TO_QUERY_PARAM")
            if self.allow_ephemeral_encryption:
                active_flags.append("ALLOW_EPHEMERAL_ENCRYPTION")

            if active_flags:
                raise ValueError(
                    "Production-like Layer 6 configuration cannot enable bypass flags: "
                    + ", ".join(active_flags)
                )

        return self

    def is_production_like(self) -> bool:
        return is_production_like_environment(self.environment)


Settings = Layer6Settings


@lru_cache(maxsize=1)
def get_layer6_settings() -> Layer6Settings:
    return Layer6Settings()


def get_settings() -> Layer6Settings:
    return get_layer6_settings()


def validate_layer6_startup_settings() -> Layer6Settings:
    """Fail-fast startup hook for Layer 6 critical configuration."""

    return get_layer6_settings()
