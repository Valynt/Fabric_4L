"""Comprehensive configuration management and environment-specific settings."""

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from value_fabric.shared.models.typed_dict import TypedDictModel


class ConfigurationManager__load_from_vaultResult(TypedDictModel):
    pass

class ConfigurationManager__load_from_fileResult(TypedDictModel):
    pass

logger = logging.getLogger(__name__)


class VaultSourceNotSupportedError(RuntimeError):
    """Raised when a vault config source is requested but Vault support is not implemented.

    Direct Vault API access is intentionally unsupported in v1. Use External Secrets
    Operator (ESO) to sync Vault secrets into Kubernetes Secrets, then mount them as
    environment variables and configure the source as ``type: env``.

    See ``docs/secrets-management.md`` and ``docs/governance/compatibility-debt-registry.md``.
    """

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name
        super().__init__(
            f"Vault config source '{source_name}' is not supported in v1. "
            "Use External Secrets Operator (ESO) to sync Vault secrets into Kubernetes "
            "Secrets and configure the source as type: env. "
            "See docs/governance/compatibility-debt-registry.md for the migration path."
        )


class Environment(str, Enum):
    """Deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigFormat(str, Enum):
    """Configuration file formats."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    ENV = "env"


@dataclass
class ConfigSource:
    """Configuration source definition."""

    name: str
    type: str  # file, env, vault, etc.
    location: str
    format: ConfigFormat | None = None
    priority: int = 0
    required: bool = True
    encrypted: bool = False
    watch_changes: bool = False


class DatabaseConfig(BaseModel):
    """Database configuration."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=7687, description="Database port")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    database: str = Field(default="neo4j", description="Database name")
    max_pool_size: int = Field(default=50, description="Maximum connection pool size")
    connection_timeout: int = Field(
        default=30, description="Connection timeout in seconds"
    )
    retry_attempts: int = Field(default=3, description="Connection retry attempts")
    ssl_enabled: bool = Field(default=False, description="Enable SSL")
    ssl_cert_path: str | None = Field(None, description="SSL certificate path")
    read_only: bool = Field(default=False, description="Read-only mode")


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True, description="Enable caching")
    backend: str = Field(default="redis", description="Cache backend")
    host: str = Field(default="localhost", description="Cache host")
    port: int = Field(default=6379, description="Cache port")
    database: int = Field(default=0, description="Cache database number")
    password: str | None = Field(None, description="Cache password")
    default_ttl: int = Field(default=300, description="Default TTL in seconds")
    max_connections: int = Field(default=100, description="Maximum connections")
    connection_timeout: int = Field(default=5, description="Connection timeout")
    retry_attempts: int = Field(default=3, description="Retry attempts")
    key_prefix: str = Field(default="value_fabric:", description="Key prefix")
    compression: bool = Field(default=True, description="Enable compression")
    serialization: str = Field(default="json", description="Serialization format")


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""

    enabled: bool = Field(default=True, description="Enable vector store")
    provider: str = Field(default="pinecone", description="Vector store provider")
    api_key: str = Field(..., description="API key")
    environment: str = Field(default="us-west-2", description="Environment/region")
    index_name: str = Field(default="value-fabric", description="Index name")
    dimension: int = Field(default=768, description="Vector dimension")
    metric: str = Field(default="cosine", description="Similarity metric")
    batch_size: int = Field(default=100, description="Batch size for upserts")
    max_retries: int = Field(default=3, description="Maximum retries")
    timeout: int = Field(default=30, description="Request timeout")


class AuthConfig(BaseModel):
    """Authentication configuration."""

    enabled: bool = Field(default=True, description="Enable authentication")
    provider: str = Field(default="api_key", description="Auth provider")
    secret_key: str = Field(..., description="Secret key for tokens")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    token_expiry: int = Field(default=3600, description="Token expiry in seconds")
    refresh_token_expiry: int = Field(default=86400, description="Refresh token expiry")
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(
        default=100, description="Rate limit requests per minute"
    )
    rate_limit_burst: int = Field(default=200, description="Rate limit burst size")
    session_timeout: int = Field(default=1800, description="Session timeout in seconds")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format")
    include_timestamp: bool = Field(default=True, description="Include timestamp")
    include_level: bool = Field(default=True, description="Include log level")
    include_module: bool = Field(default=True, description="Include module name")
    include_function: bool = Field(default=True, description="Include function name")
    include_line_number: bool = Field(default=True, description="Include line number")
    request_id_header: str = Field(
        default="X-Request-ID", description="Request ID header"
    )
    structured_logging: bool = Field(
        default=True, description="Enable structured logging"
    )
    log_to_file: bool = Field(default=False, description="Log to file")
    log_file_path: str = Field(default="./logs/app.log", description="Log file path")
    max_file_size: int = Field(default=10485760, description="Max file size in bytes")
    backup_count: int = Field(default=5, description="Number of backup files")

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


class MetricsConfig(BaseModel):
    """Metrics configuration."""

    enabled: bool = Field(default=True, description="Enable metrics")
    backend: str = Field(default="prometheus", description="Metrics backend")
    port: int = Field(default=9090, description="Metrics port")
    path: str = Field(default="/metrics", description="Metrics endpoint path")
    namespace: str = Field(default="value_fabric", description="Metrics namespace")
    subsystem: str = Field(default="layer3", description="Metrics subsystem")
    collect_interval: int = Field(
        default=15, description="Collection interval in seconds"
    )
    retention_days: int = Field(default=30, description="Retention period in days")
    export_histograms: bool = Field(default=True, description="Export histograms")
    export_counters: bool = Field(default=True, description="Export counters")
    export_gauges: bool = Field(default=True, description="Export gauges")


class TracingConfig(BaseModel):
    """Tracing configuration."""

    enabled: bool = Field(default=True, description="Enable tracing")
    backend: str = Field(default="jaeger", description="Tracing backend")
    service_name: str = Field(default="value-fabric-layer3", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    endpoint: str | None = Field(None, description="Tracing endpoint")
    auth_token: str | None = Field(None, description="Authentication token")
    sample_rate: float = Field(default=1.0, description="Sample rate (0.0-1.0)")
    max_spans_per_second: int = Field(default=1000, description="Max spans per second")
    timeout: int = Field(default=5, description="Request timeout")
    batch_size: int = Field(default=100, description="Batch size")
    flush_interval: int = Field(default=5, description="Flush interval in seconds")

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v):
        """Validate sample rate."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Sample rate must be between 0.0 and 1.0")
        return v


class BackupConfig(BaseModel):
    """Backup configuration."""

    enabled: bool = Field(default=True, description="Enable backups")
    schedule: str = Field(default="0 2 * * *", description="Backup schedule (cron)")
    retention_days: int = Field(default=30, description="Retention period in days")
    max_backups: int = Field(default=100, description="Maximum backups to keep")
    compression: bool = Field(default=True, description="Enable compression")
    encryption: bool = Field(default=False, description="Enable encryption")
    storage_type: str = Field(default="local", description="Storage type")
    storage_path: str = Field(default="./backups", description="Storage path")
    s3_bucket: str | None = Field(None, description="S3 bucket name")
    s3_region: str | None = Field(None, description="S3 region")
    s3_access_key: str | None = Field(None, description="S3 access key")
    s3_secret_key: str | None = Field(None, description="S3 secret key")


class SecurityConfig(BaseModel):
    """Security configuration."""

    cors_origins: list[str] = Field(default=[], description="CORS allowed origins (empty = same-origin only)")
    cors_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods"
    )
    cors_headers: list[str] = Field(default=["Content-Type", "Authorization"], description="CORS allowed headers")
    cors_credentials: bool = Field(default=False, description="CORS allow credentials")
    ssl_verify: bool = Field(default=True, description="Verify SSL certificates")
    max_request_size: int = Field(
        default=10485760, description="Max request size in bytes"
    )
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    allowed_hosts: list[str] = Field(default=[], description="Allowed hosts (empty = no host header validation)")
    trusted_proxies: list[str] = Field(default=[], description="Trusted proxy IPs")
    rate_limiting_enabled: bool = Field(
        default=True, description="Enable rate limiting"
    )


class APIConfig(BaseModel):
    """API configuration."""

    host: str = Field(default="0.0.0.0", description="API host")  # nosec B104
    port: int = Field(default=8003, description="API port")
    workers: int = Field(default=1, description="Number of workers")
    reload: bool = Field(default=False, description="Enable auto-reload")
    debug: bool = Field(default=False, description="Enable debug mode")
    prefix: str = Field(default="/v1", description="API prefix")
    title: str = Field(default="Value Fabric Layer 3 API", description="API title")
    description: str = Field(
        default="Value Fabric Layer 3 Knowledge Graph API",
        description="API description",
    )
    version: str = Field(default="1.0.0", description="API version")
    docs_enabled: bool = Field(default=True, description="Enable API docs")
    redoc_enabled: bool = Field(default=True, description="Enable ReDoc")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI URL")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class AppConfig(BaseModel):
    """Main application configuration."""

    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Global log level")

    # Component configurations
    database: DatabaseConfig = Field(..., description="Database configuration")
    cache: CacheConfig = Field(
        default_factory=CacheConfig, description="Cache configuration"
    )
    vector_store: VectorStoreConfig = Field(
        ..., description="Vector store configuration"
    )
    auth: AuthConfig = Field(
        default_factory=AuthConfig, description="Authentication configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    metrics: MetricsConfig = Field(
        default_factory=MetricsConfig, description="Metrics configuration"
    )
    tracing: TracingConfig = Field(
        default_factory=TracingConfig, description="Tracing configuration"
    )
    backup: BackupConfig = Field(
        default_factory=BackupConfig, description="Backup configuration"
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig, description="Security configuration"
    )
    api: APIConfig = Field(default_factory=APIConfig, description="API configuration")

    # Custom configuration
    custom: dict[str, Any] = Field(
        default_factory=dict, description="Custom configuration"
    )

    @model_validator(mode="after")
    def validate_production_jwt_algorithm(self) -> "AppConfig":
        """Fail-closed: reject HS256 JWT algorithm in production."""
        if self.environment == Environment.PRODUCTION:
            if self.auth.algorithm.upper() == "HS256":
                raise ValueError(
                    "algorithm must not be HS256 in production; use RS256 or stronger"
                )
        return self

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )


class ConfigurationManager:
    """Manages configuration loading and validation."""

    def __init__(self, environment: Environment | None = None):
        """Initialize configuration manager.

        Args:
            environment: Target environment
        """
        self.environment = environment or self._detect_environment()
        self.config_sources: list[ConfigSource] = []
        self._config: AppConfig | None = None
        self._setup_default_sources()

    def _detect_environment(self) -> Environment:
        """Detect current environment.

        Returns:
            Detected environment
        """
        env_var = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()

        try:
            return Environment(env_var)
        except ValueError:
            logger.warning(
                f"Invalid environment '{env_var}', defaulting to development"
            )
            return Environment.DEVELOPMENT

    def _setup_default_sources(self) -> None:
        """Setup default configuration sources."""
        # Base configuration file
        self.config_sources.append(
            ConfigSource(
                name="base",
                type="file",
                location="config/base.yaml",
                format=ConfigFormat.YAML,
                priority=100,
                required=False,
            )
        )

        # Environment-specific configuration
        self.config_sources.append(
            ConfigSource(
                name="environment",
                type="file",
                location=f"config/{self.environment.value}.yaml",
                format=ConfigFormat.YAML,
                priority=200,
                required=False,
            )
        )

        # Local configuration (for development overrides)
        self.config_sources.append(
            ConfigSource(
                name="local",
                type="file",
                location="config/local.yaml",
                format=ConfigFormat.YAML,
                priority=300,
                required=False,
            )
        )

        # Environment variables
        self.config_sources.append(
            ConfigSource(
                name="env",
                type="env",
                location="environment",
                priority=400,
                required=True,
            )
        )

    def add_config_source(self, source: ConfigSource) -> None:
        """Add a configuration source.

        Args:
            source: Configuration source to add
        """
        self.config_sources.append(source)
        self.config_sources.sort(key=lambda s: s.priority)

    def load_config(self) -> AppConfig:
        """Load and merge configuration from all sources.

        Returns:
            Loaded configuration
        """
        if self._config:
            return self._config

        merged_config = {}

        # Load from sources in priority order
        for source in self.config_sources:
            try:
                config_data = self._load_from_source(source)
                if config_data:
                    merged_config = self._merge_configs(merged_config, config_data)
                    logger.debug(f"Loaded configuration from {source.name}")
            except VaultSourceNotSupportedError:
                # Vault is intentionally unsupported in v1 — always re-raise regardless of
                # source.required so misconfigured vault sources fail loudly rather than
                # silently producing an empty config.
                raise
            except Exception as e:
                if source.required:
                    raise ValueError(
                        f"Failed to load required configuration source '{source.name}': {e}"
                    )
                else:
                    logger.warning(
                        f"Failed to load optional configuration source '{source.name}': {e}"
                    )

        # Validate and create configuration object
        self._config = AppConfig(**merged_config)

        # Log configuration summary
        self._log_config_summary()

        return self._config

    def _load_from_source(self, source: ConfigSource) -> dict[str, Any]:
        """Load configuration from a specific source.

        Args:
            source: Configuration source

        Returns:
            Configuration data
        """
        if source.type == "file":
            return self._load_from_file(source)
        elif source.type == "env":
            return self._load_from_env()
        elif source.type == "vault":
            return self._load_from_vault(source)
        else:
            raise ValueError(f"Unsupported source type: {source.type}")

    def _load_from_file(self, source: ConfigSource) -> dict[str, Any]:
        """Load configuration from file.

        Args:
            source: File configuration source

        Returns:
            Configuration data
        """
        file_path = Path(source.location)

        if not file_path.exists():
            if source.required:
                raise FileNotFoundError(
                    f"Required configuration file not found: {file_path}"
                )
            return ConfigurationManager__load_from_fileResult.model_validate({})

        with open(file_path, encoding="utf-8") as f:
            if source.format == ConfigFormat.YAML:
                return yaml.safe_load(f) or {}
            elif source.format == ConfigFormat.JSON:
                return json.load(f) or {}
            elif source.format == ConfigFormat.TOML:
                import toml

                return toml.load(f) or {}
            else:
                raise ValueError(f"Unsupported file format: {source.format}")

    def _load_from_env(self) -> dict[str, Any]:
        """Load configuration from environment variables.

        Returns:
            Configuration data
        """
        env_config = {}

        # Map environment variables to configuration keys
        env_mappings = {
            # Database
            "DB_HOST": ("database", "host"),
            "DB_PORT": ("database", "port"),
            "DB_USERNAME": ("database", "username"),
            "DB_PASSWORD": ("database", "password"),
            "DB_DATABASE": ("database", "database"),
            "DB_MAX_POOL_SIZE": ("database", "max_pool_size"),
            # Cache
            "CACHE_HOST": ("cache", "host"),
            "CACHE_PORT": ("cache", "port"),
            "CACHE_PASSWORD": ("cache", "password"),
            "CACHE_DEFAULT_TTL": ("cache", "default_ttl"),
            # Vector Store
            "VECTOR_API_KEY": ("vector_store", "api_key"),
            "VECTOR_INDEX_NAME": ("vector_store", "index_name"),
            "VECTOR_DIMENSION": ("vector_store", "dimension"),
            # Auth
            "AUTH_SECRET_KEY": ("auth", "secret_key"),
            "AUTH_TOKEN_EXPIRY": ("auth", "token_expiry"),
            # API
            "API_HOST": ("api", "host"),
            "API_PORT": ("api", "port"),
            "API_WORKERS": ("api", "workers"),
            # Logging
            "LOG_LEVEL": ("logging", "level"),
            "LOG_FORMAT": ("logging", "format"),
            # Metrics
            "METRICS_ENABLED": ("metrics", "enabled"),
            "METRICS_PORT": ("metrics", "port"),
            # Tracing
            "TRACING_ENABLED": ("tracing", "enabled"),
            "TRACING_ENDPOINT": ("tracing", "endpoint"),
        }

        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                converted_value = self._convert_env_value(value)

                if section not in env_config:
                    env_config[section] = {}
                env_config[section][key] = converted_value

        return env_config

    def _load_from_vault(self, source: ConfigSource) -> dict[str, Any]:
        """Raise VaultSourceNotSupportedError — direct Vault access is not implemented in v1.

        Use External Secrets Operator (ESO) to sync Vault secrets into Kubernetes Secrets,
        mount them as environment variables, and configure the source as ``type: env``.
        See ``docs/governance/compatibility-debt-registry.md`` for the migration path.

        Args:
            source: Vault configuration source (unsupported)

        Raises:
            VaultSourceNotSupportedError: Always. Vault source type is not supported in v1.
        """
        raise VaultSourceNotSupportedError(source.name)

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable value to appropriate type.

        Args:
            value: String value from environment

        Returns:
            Converted value
        """
        # Boolean conversion
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Integer conversion
        if value.isdigit():
            return int(value)

        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass

        # JSON conversion
        if value.startswith(("{", "[")):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        # Return as string
        return value

    def _merge_configs(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge two configuration dictionaries.

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _log_config_summary(self) -> None:
        """Log configuration summary (without sensitive data)."""
        if not self._config:
            return

        logger.info(f"Configuration loaded for environment: {self.environment.value}")
        logger.info(f"Debug mode: {self._config.debug}")
        logger.info(f"API server: {self._config.api.host}:{self._config.api.port}")
        logger.info(
            f"Database: {self._config.database.host}:{self._config.database.port}/{self._config.database.database}"
        )
        logger.info(f"Cache: {self._config.cache.host}:{self._config.cache.port}")
        logger.info(f"Vector store: {self._config.vector_store.provider}")
        logger.info(f"Metrics enabled: {self._config.metrics.enabled}")
        logger.info(f"Tracing enabled: {self._config.tracing.enabled}")
        logger.info(f"Backup enabled: {self._config.backup.enabled}")

    def get_config(self) -> AppConfig:
        """Get loaded configuration.

        Returns:
            Configuration object
        """
        if not self._config:
            self.load_config()
        return self._config

    def reload_config(self) -> AppConfig:
        """Reload configuration from sources.

        Returns:
            Reloaded configuration
        """
        self._config = None
        return self.load_config()

    def validate_config(self, config: AppConfig) -> list[str]:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Validate database configuration
        if not config.database.password:
            errors.append("Database password is required")

        # Validate vector store configuration
        if not config.vector_store.api_key:
            errors.append("Vector store API key is required")

        # Validate auth configuration
        if config.auth.enabled and not config.auth.secret_key:
            errors.append("Auth secret key is required when authentication is enabled")

        # Validate API configuration
        if not 1 <= config.api.port <= 65535:
            errors.append("API port must be between 1 and 65535")

        # Validate backup configuration
        if config.backup.enabled and config.backup.storage_type == "s3":
            if not config.backup.s3_bucket:
                errors.append("S3 bucket name is required for S3 backup storage")
            if not config.backup.s3_access_key or not config.backup.s3_secret_key:
                errors.append("S3 credentials are required for S3 backup storage")

        return errors

    def export_config(
        self, format: str = "yaml", include_sensitive: bool = False
    ) -> str:
        """Export configuration to string.

        Args:
            format: Export format (yaml, json)
            include_sensitive: Include sensitive data

        Returns:
            Exported configuration string
        """
        config = self.get_config()

        # Create export dictionary
        export_data = config.dict()

        # Remove sensitive data if requested
        if not include_sensitive:
            self._remove_sensitive_data(export_data)

        # Export in requested format
        if format.lower() == "yaml":
            return yaml.dump(export_data, default_flow_style=False)
        elif format.lower() == "json":
            return json.dumps(export_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _remove_sensitive_data(self, data: dict[str, Any]) -> None:
        """Remove sensitive data from configuration dictionary.

        Args:
            data: Configuration dictionary
        """
        sensitive_keys = {
            "password",
            "secret_key",
            "api_key",
            "access_key",
            "auth_token",
        }

        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively remove sensitive data
                self._remove_sensitive_data(value)
            elif isinstance(key, str) and any(
                sensitive in key.lower() for sensitive in sensitive_keys
            ):
                data[key] = "***REDACTED***"


# Global configuration manager instance
_config_manager: ConfigurationManager | None = None


def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance.

    Returns:
        Configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def get_config() -> AppConfig:
    """Get application configuration.

    Returns:
        Application configuration
    """
    return get_config_manager().get_config()


def load_config(environment: Environment | None = None) -> AppConfig:
    """Load configuration for specific environment.

    Args:
        environment: Target environment

    Returns:
        Loaded configuration
    """
    global _config_manager
    _config_manager = ConfigurationManager(environment)
    return _config_manager.load_config()


def validate_configuration(config: AppConfig) -> list[str]:
    """Validate application configuration.

    Args:
        config: Configuration to validate

    Returns:
        List of validation errors
    """
    return get_config_manager().validate_config(config)
