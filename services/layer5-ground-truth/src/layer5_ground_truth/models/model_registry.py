"""
SQLAlchemy models for the Model Registry.

Core entities:
  - ModelVersion      : LLM model definitions with capabilities and cost tracking
  - ModelDeployment   : Deployment state per environment (canary, production, etc.)
  - ModelEvaluation   : Benchmark scores for model versions

Design notes:
  - Follows Layer 5 patterns: UUID primary keys, tenant_id for tenancy
  - Cost tracking enables accurate billing attribution per model usage
  - Deployment model supports canary releases and traffic splitting
  - Evaluation model tracks benchmark performance over time
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.types import JSON

# Import from truth_object to share the same Base and UUID type
from .truth_object import UUID, Base

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ModelProvider(str, PyEnum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    GOOGLE = "google"
    AZURE = "azure"
    OTHER = "other"


class ModelCapability(str, PyEnum):
    """Model capabilities for feature detection."""

    JSON_MODE = "json_mode"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    STREAMING = "streaming"
    SYSTEM_PROMPT = "system_prompt"
    TOOLS = "tools"


class DeploymentEnvironment(str, PyEnum):
    """Deployment environments for traffic routing."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStatus(str, PyEnum):
    """Status of a model deployment."""

    PENDING = "pending"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ROLLED_BACK = "rolled_back"


# ---------------------------------------------------------------------------
# ModelVersion — the central model definition
# ---------------------------------------------------------------------------


class ModelVersion(Base):
    """
    A versioned LLM model definition with capabilities and cost tracking.

    This is the atomic unit of model governance. Every LLM call in the system
    must reference a ModelVersion for cost attribution and audit trails.
    """

    __tablename__ = "model_versions"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique model version identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation — all queries must filter by this",
    )

    # -------------------------------------------------------------------------
    # Model identification
    # -------------------------------------------------------------------------
    name = Column(
        String(128),
        nullable=False,
        comment="Model name, e.g., 'gpt-4-turbo', 'claude-3-opus-20240229'",
    )
    provider = Column(
        String(32),
        nullable=False,
        default=ModelProvider.OTHER.value,
        comment="LLM provider — see ModelProvider enum",
    )
    version = Column(
        String(64),
        nullable=False,
        comment="Semver or provider version string, e.g., '1.0', '2024-02'",
    )
    model_identifier = Column(
        String(128),
        nullable=False,
        comment="Provider's API identifier, e.g., 'gpt-4-turbo-preview'",
    )

    # -------------------------------------------------------------------------
    # Capabilities
    # -------------------------------------------------------------------------
    capabilities = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of ModelCapability values this model supports",
    )
    context_window = Column(
        Integer,
        nullable=False,
        default=4096,
        comment="Maximum context window in tokens",
    )
    max_output_tokens = Column(
        Integer,
        nullable=True,
        comment="Maximum output tokens (null = same as context window)",
    )

    # -------------------------------------------------------------------------
    # Cost tracking (per 1K tokens for billing)
    # -------------------------------------------------------------------------
    cost_per_1k_input = Column(
        Numeric(10, 6),
        nullable=False,
        default=Decimal("0.0"),
        comment="Cost per 1,000 input tokens in USD",
    )
    cost_per_1k_output = Column(
        Numeric(10, 6),
        nullable=False,
        default=Decimal("0.0"),
        comment="Cost per 1,000 output tokens in USD",
    )
    cost_per_1k_cached = Column(
        Numeric(10, 6),
        nullable=True,
        comment="Cost per 1,000 cached tokens if provider supports caching",
    )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this model version is available for use",
    )
    is_default = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is the default model for its provider",
    )
    deprecated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when model was deprecated (soft delete)",
    )
    deprecation_reason = Column(
        Text,
        nullable=True,
        comment="Reason for deprecation",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    description = Column(
        Text,
        nullable=True,
        comment="Human-readable description of the model",
    )
    extra_metadata = Column(
        "metadata",  # Keep column name as 'metadata' in DB for compatibility
        JSON,
        nullable=True,
        comment="Additional provider-specific metadata",
    )
    created_by = Column(
        String(255),
        nullable=True,
        comment="User ID or email of who registered this model",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="Registration timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="Last update timestamp",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    deployments: Mapped[list["ModelDeployment"]] = relationship(
        "ModelDeployment",
        back_populates="model_version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    evaluations: Mapped[list["ModelEvaluation"]] = relationship(
        "ModelEvaluation",
        back_populates="model_version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_model_versions_tenant_provider_name",
            "tenant_id",
            "provider",
            "name",
        ),
        Index(
            "ix_model_versions_tenant_default",
            "tenant_id",
            "is_default",
        ),
    )


# ---------------------------------------------------------------------------
# ModelDeployment — environment-specific deployment state
# ---------------------------------------------------------------------------


class ModelDeployment(Base):
    """
    Deployment state for a ModelVersion in a specific environment.

    Supports canary releases, traffic splitting, and rollback operations.
    Each environment (dev, staging, prod) has its own deployment record.
    """

    __tablename__ = "model_deployments"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique deployment identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    model_version_id = Column(
        UUID,
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the deployed model version",
    )
    model_version: Mapped[ModelVersion] = relationship(
        "ModelVersion",
        back_populates="deployments",
    )

    # -------------------------------------------------------------------------
    # Deployment configuration
    # -------------------------------------------------------------------------
    environment = Column(
        String(32),
        nullable=False,
        default=DeploymentEnvironment.DEVELOPMENT.value,
        comment="Target environment — see DeploymentEnvironment enum",
    )
    status = Column(
        String(32),
        nullable=False,
        default=DeploymentStatus.PENDING.value,
        comment="Current deployment status",
    )
    traffic_percentage = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Traffic percentage for canary (0-100)",
    )
    is_default_for_env = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is the default model for this environment",
    )

    # -------------------------------------------------------------------------
    # Deployment tracking
    # -------------------------------------------------------------------------
    deployed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When deployment was activated",
    )
    deployed_by = Column(
        String(255),
        nullable=True,
        comment="User who initiated the deployment",
    )
    rolled_back_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When deployment was rolled back",
    )
    rolled_back_by = Column(
        String(255),
        nullable=True,
        comment="User who initiated the rollback",
    )
    rollback_reason = Column(
        Text,
        nullable=True,
        comment="Reason for rollback",
    )

    # -------------------------------------------------------------------------
    # Health & monitoring
    # -------------------------------------------------------------------------
    error_rate_5m = Column(
        Numeric(5, 4),
        nullable=True,
        comment="5-minute rolling error rate (0.0-1.0)",
    )
    latency_p50_ms = Column(
        Integer,
        nullable=True,
        comment="50th percentile latency in milliseconds",
    )
    latency_p99_ms = Column(
        Integer,
        nullable=True,
        comment="99th percentile latency in milliseconds",
    )
    last_health_check = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last health check",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    deployment_notes = Column(
        Text,
        nullable=True,
        comment="Notes about this deployment",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_model_deployments_tenant_env_default",
            "tenant_id",
            "environment",
            "is_default_for_env",
        ),
        Index(
            "ix_model_deployments_tenant_env_status",
            "tenant_id",
            "environment",
            "status",
        ),
    )


# ---------------------------------------------------------------------------
# ModelEvaluation — benchmark performance tracking
# ---------------------------------------------------------------------------


class ModelEvaluation(Base):
    """
    Benchmark evaluation results for a ModelVersion.

    Tracks model performance on standardized benchmarks over time,
    enabling comparison between versions and providers.
    """

    __tablename__ = "model_evaluations"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique evaluation identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    model_version_id = Column(
        UUID,
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to evaluated model version",
    )
    model_version: Mapped[ModelVersion] = relationship(
        "ModelVersion",
        back_populates="evaluations",
    )

    # -------------------------------------------------------------------------
    # Evaluation details
    # -------------------------------------------------------------------------
    benchmark_name = Column(
        String(128),
        nullable=False,
        comment="Name of the benchmark, e.g., 'mmlu', 'human-eval'",
    )
    benchmark_version = Column(
        String(64),
        nullable=True,
        comment="Version of the benchmark dataset",
    )
    score = Column(
        Numeric(6, 4),
        nullable=False,
        comment="Primary score (0.0-1.0 or normalized scale)",
    )
    score_details = Column(
        JSON,
        nullable=True,
        comment="Detailed scores by category/subtask",
    )

    # -------------------------------------------------------------------------
    # Evaluation metadata
    # -------------------------------------------------------------------------
    evaluated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="When evaluation was performed",
    )
    evaluated_by = Column(
        String(255),
        nullable=True,
        comment="User or system that ran the evaluation",
    )
    evaluation_config = Column(
        JSON,
        nullable=True,
        comment="Configuration used for evaluation (temperature, etc.)",
    )
    sample_size = Column(
        Integer,
        nullable=True,
        comment="Number of samples evaluated",
    )
    cost_usd = Column(
        Numeric(10, 6),
        nullable=True,
        comment="Total cost of evaluation in USD",
    )
    duration_seconds = Column(
        Integer,
        nullable=True,
        comment="Duration of evaluation in seconds",
    )

    # -------------------------------------------------------------------------
    # Notes & artifacts
    # -------------------------------------------------------------------------
    notes = Column(
        Text,
        nullable=True,
        comment="Human notes about the evaluation",
    )
    artifact_urls = Column(
        JSON,
        nullable=True,
        comment="Links to evaluation artifacts (logs, outputs, etc.)",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_model_evaluations_tenant_benchmark",
            "tenant_id",
            "benchmark_name",
        ),
        Index(
            "ix_model_evaluations_tenant_model",
            "tenant_id",
            "model_version_id",
        ),
    )
