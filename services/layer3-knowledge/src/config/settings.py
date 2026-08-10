"""Settings surface for Layer 3 Knowledge Graph."""

import os
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from value_fabric.shared.security.neo4j import validate_neo4j_aura_config


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE_PATH", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")  # nosec B104
    api_port: int = Field(default=8003, alias="API_PORT")
    api_workers: int = Field(default=1, alias="API_WORKERS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Logging Configuration
    log_format: str = Field(default="json", alias="LOG_FORMAT")  # json or text
    log_timestamp_format: str = Field(
        default="%Y-%m-%dT%H:%M:%S.%fZ", alias="LOG_TIMESTAMP_FORMAT"
    )
    log_include_module: bool = Field(default=True, alias="LOG_INCLUDE_MODULE")
    log_include_function: bool = Field(default=True, alias="LOG_INCLUDE_FUNCTION")
    log_include_line_number: bool = Field(default=True, alias="LOG_INCLUDE_LINE_NUMBER")
    log_request_id_header: str = Field(
        default="X-Request-ID", alias="LOG_REQUEST_ID_HEADER"
    )

    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(
        default=100, alias="RATE_LIMIT_REQUESTS_PER_MINUTE"
    )
    rate_limit_burst_size: int = Field(default=200, alias="RATE_LIMIT_BURST_SIZE")
    rate_limit_cleanup_interval: int = Field(
        default=300, alias="RATE_LIMIT_CLEANUP_INTERVAL"
    )

    # Cache Configuration
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    cache_redis_url: str = Field(
        default="redis://localhost:6379/0", alias="CACHE_REDIS_URL"
    )
    cache_default_ttl: int = Field(default=300, alias="CACHE_DEFAULT_TTL")
    cache_max_ttl: int = Field(default=3600, alias="CACHE_MAX_TTL")
    cache_key_prefix: str = Field(default="value_fabric:", alias="CACHE_KEY_PREFIX")
    cache_serializer: str = Field(default="json", alias="CACHE_SERIALIZER")
    cache_compression: bool = Field(default=True, alias="CACHE_COMPRESSION")

    # Metrics Configuration
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    metrics_prefix: str = Field(default="value_fabric_", alias="METRICS_PREFIX")
    metrics_namespace: str = Field(default="layer3", alias="METRICS_NAMESPACE")
    metrics_path: str = Field(default="/metrics", alias="METRICS_PATH")
    metrics_include_timestamp: bool = Field(
        default=True, alias="METRICS_INCLUDE_TIMESTAMP"
    )

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(..., alias="NEO4J_PASSWORD")  # Required field
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")
    neo4j_max_pool_size: int = Field(default=50, alias="NEO4J_MAX_POOL_SIZE")

    # Security Configuration
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    # NoDecode disables pydantic-settings' implicit JSON decoding for this complex
    # field so the ``mode="before"`` validator receives the raw env value and can
    # parse the comma-separated CORS contract used across all layers.
    cors_origins: Annotated[list[str], NoDecode] = Field(default=[], alias="CORS_ORIGINS")

    # Pinecone Configuration
    pinecone_api_key: str | None = Field(default=None, alias="PINECONE_API_KEY")
    pinecone_index: str = Field(default="value-fabric", alias="PINECONE_INDEX")
    pinecone_namespace: str = Field(default="entities", alias="PINECONE_NAMESPACE")
    pinecone_dimension: int = Field(default=768, alias="PINECONE_DIMENSION")
    pinecone_metric: str = Field(default="cosine", alias="PINECONE_METRIC")
    pinecone_cloud: str = Field(default="aws", alias="PINECONE_CLOUD")
    pinecone_region: str = Field(default="us-west-2", alias="PINECONE_REGION")

    # Embeddings Configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")

    # GraphRAG Configuration
    graphrag_max_hops: int = Field(default=3, alias="GRAPHRAG_MAX_HOPS")
    graphrag_max_nodes: int = Field(default=100, alias="GRAPHRAG_MAX_NODES")
    graphrag_min_confidence: float = Field(default=0.7, alias="GRAPHRAG_MIN_CONFIDENCE")

    # Hybrid Search Configuration
    hybrid_bm25_weight: float = Field(default=0.3, alias="HYBRID_BM25_WEIGHT")
    hybrid_vector_weight: float = Field(default=0.5, alias="HYBRID_VECTOR_WEIGHT")
    hybrid_graph_weight: float = Field(default=0.2, alias="HYBRID_GRAPH_WEIGHT")
    hybrid_top_k: int = Field(default=10, alias="HYBRID_TOP_K")

    # Ingestion Configuration
    ingestion_batch_size: int = Field(default=1000, alias="INGESTION_BATCH_SIZE")
    ingestion_timeout_seconds: int = Field(
        default=300, alias="INGESTION_TIMEOUT_SECONDS"
    )

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret is secure."""
        insecure_defaults = ["changeme", "changeme-in-production", "valuefabric", "postgres", "secret", "password"]
        if os.getenv("ENVIRONMENT") == "production":
            if v.lower() in insecure_defaults:
                raise ValueError(f"Insecure default JWT secret detected in production: {v}")
            if len(v) < 32:
                raise ValueError("JWT secret must be >= 32 characters in production")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> object:
        """Accept the comma-separated CORS origin contract used by deployment env files.

        Deployment ``.env`` files set ``CORS_ORIGINS`` as a plain or comma-separated
        string (e.g. ``http://localhost:3001`` or ``https://a.io,https://b.io``),
        consistent with Layers 1/4/5. Without this, pydantic-settings attempts to
        JSON-decode the value for the ``list[str]`` field and raises on non-JSON
        input. A JSON array string is still accepted for backward compatibility.
        """
        if isinstance(v, str):
            text = v.strip()
            if not text:
                return []
            if text.startswith("["):
                import json

                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in text.split(",") if origin.strip()]
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """Validate CORS origins are secure."""
        if os.getenv("ENVIRONMENT") == "production":
            if "*" in v:
                raise ValueError("Wildcard CORS origin not allowed in production")
            if not v or all(not origin.strip() for origin in v):
                raise ValueError("CORS_ORIGINS must be set to at least one specific origin in production")
        return v

    @field_validator("neo4j_password")
    @classmethod
    def validate_neo4j_password(cls, v: str | None) -> str:
        """Validate that Neo4j password is configured."""
        if v is None or v.strip() == "":
            raise ValueError(
                "NEO4J_PASSWORD environment variable must be set. "
                "Cannot use empty or None password for security reasons."
            )
        if v == "password":
            raise ValueError(
                "NEO4J_PASSWORD cannot be 'password'. "
                "Please set a secure password via NEO4J_PASSWORD environment variable."
            )
        return v

    @field_validator("embedding_dimension")
    @classmethod
    def validate_embedding_dimension(cls, v: int) -> int:
        """Embedding vectors must use a positive dimension."""
        if v <= 0:
            raise ValueError("EMBEDDING_DIMENSION must be a positive integer")
        return v

    @model_validator(mode="after")
    def validate_prod_neo4j_aura(self) -> "Settings":
        """Production/staging must use managed Aura, not in-cluster Neo4j."""
        validate_neo4j_aura_config(
            uri=self.neo4j_uri,
            password=self.neo4j_password,
            environment=os.getenv("ENVIRONMENT") or os.getenv("ENV"),
        )
        return self

    @property
    def neo4j_auth(self) -> tuple[str, str]:
        """Return Neo4j authentication tuple."""
        return (self.neo4j_user, self.neo4j_password)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
