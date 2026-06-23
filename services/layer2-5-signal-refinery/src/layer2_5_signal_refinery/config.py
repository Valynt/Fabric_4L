from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

"""Configuration for the L2.5 Signal Refinery service."""

PRODUCTION_LIKE_ENVIRONMENTS = {"production", "prod", "staging", "stage"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Service identity
    service_name: str = "layer2-5-signal-refinery"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    port: int = 8007

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./signal_refinery.db",
        alias="DATABASE_URL",
    )

    # Auth / JWT
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"

    # Layer 2 integration
    layer2_base_url: str = Field(default="http://localhost:8002", alias="LAYER2_BASE_URL")

    # Layer 3 integration
    layer3_base_url: str = Field(default="http://localhost:8003", alias="LAYER3_BASE_URL")

    # Layer 4 integration
    layer4_base_url: str = Field(default="http://localhost:8004", alias="LAYER4_BASE_URL")

    # Observability
    otel_exporter_endpoint: str | None = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")

    @field_validator("jwt_secret", mode="after")
    @classmethod
    def _reject_weak_jwt_secret(cls, v: str) -> str:
        weak = {"", "changeme", "changeme-in-production", "password", "secret", "valuefabric"}
        if v.lower() in weak:
            raise ValueError("JWT_SECRET cannot be empty or a known weak default")
        return v

    @field_validator("jwt_algorithm", mode="after")
    @classmethod
    def _reject_weak_jwt_algorithm(cls, v: str, info) -> str:
        data = info.data
        env = str(data.get("environment", "development")).lower()
        if env in PRODUCTION_LIKE_ENVIRONMENTS and v.upper() == "HS256":
            raise ValueError("jwt_algorithm must not be HS256 in production-like environments; use RS256 or stronger")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in PRODUCTION_LIKE_ENVIRONMENTS


@lru_cache
def get_settings() -> Settings:
    return Settings()
