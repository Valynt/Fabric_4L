"""SQLAlchemy models for Layer 1 Ingestion Service.

Spec-compliant database schema with multi-tenancy support.
Defines: ScrapingTarget, ScrapingJob, RawContent, ExtractedData,
ComplianceLog, ProxyPool, JobStageDetail, JobError entities.
"""

import uuid
from datetime import UTC, datetime
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
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all Layer 1 ORM models."""

    pass


# =============================================================================
# ENUMS
# =============================================================================


class JobStatus(str, PyEnum):
    """Job lifecycle states - 11 states as per spec."""

    PENDING = "PENDING"
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    BROWSER_ACQUIRING = "BROWSER_ACQUIRING"
    NAVIGATING = "NAVIGATING"
    EXTRACTING = "EXTRACTING"
    TRANSFORMING = "TRANSFORMING"
    STORING = "STORING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"


class PipelineStage(str, PyEnum):
    """Pipeline execution stages - 11 stages as per spec."""

    INIT = "INIT"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    BROWSER_LAUNCH = "BROWSER_LAUNCH"
    NAVIGATION = "NAVIGATION"
    CONTENT_CAPTURE = "CONTENT_CAPTURE"
    AI_EXTRACTION = "AI_EXTRACTION"
    POST_PROCESSING = "POST_PROCESSING"
    VALIDATION = "VALIDATION"
    STORAGE = "STORAGE"
    NOTIFICATION = "NOTIFICATION"


class ExtractionMethod(str, PyEnum):
    """Content extraction methods."""

    AI_LLM = "AI_LLM"
    DETERMINISTIC = "DETERMINISTIC"
    HYBRID = "HYBRID"


class SourceType(str, PyEnum):
    """Canonical source intake types for the Source Ingestion Layer UI."""

    NOTES = "notes"
    URL = "url"
    AUDIO = "audio"
    CRM = "crm"
    PDF = "pdf"
    MEETING = "meeting"


class IngestionRunStatus(str, PyEnum):
    """Lifecycle states for a canonical source ingestion run (v3.0).

    Happy path:
    ACCEPTED -> VALIDATING_ACCESS -> RESOLVING_CONNECTOR -> FETCHING_SOURCE
    -> APPLYING_POLICY -> NORMALIZING -> CHUNKING -> EXTRACTING
    -> BUILDING_CLAIMS -> VALIDATING_CLAIMS -> PROJECTING_SUMMARY -> READY
    """

    ACCEPTED = "ACCEPTED"
    VALIDATING_ACCESS = "VALIDATING_ACCESS"
    RESOLVING_CONNECTOR = "RESOLVING_CONNECTOR"
    FETCHING_SOURCE = "FETCHING_SOURCE"
    APPLYING_POLICY = "APPLYING_POLICY"
    NORMALIZING = "NORMALIZING"
    CHUNKING = "CHUNKING"
    EXTRACTING = "EXTRACTING"
    BUILDING_CLAIMS = "BUILDING_CLAIMS"
    VALIDATING_CLAIMS = "VALIDATING_CLAIMS"
    PROJECTING_SUMMARY = "PROJECTING_SUMMARY"
    READY = "READY"
    NEEDS_USER_ACTION = "NEEDS_USER_ACTION"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_PERMANENT = "FAILED_PERMANENT"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class CustodyMode(str, PyEnum):
    """Data custody model for an ingested source (v3.0).

    A: Fabric full custody — raw content stored in Fabric.
    B: Reference + extract — metadata and extracted values stored; raw fetched on demand.
    C: Customer hosted — no raw content persisted; only hashes, pointers, and attestations.
    """

    FULL_CUSTODY = "A"
    REFERENCE_EXTRACT = "B"
    CUSTOMER_HOSTED = "C"


class EvidenceChunkStatus(str, PyEnum):
    """Lifecycle status of an evidence chunk."""

    ACTIVE = "active"
    VERIFICATION_FAILED = "verification_failed"
    SUPERSEDED = "superseded"
    REDACTED = "redacted"


class SourceConsentStatus(str, PyEnum):
    """Lifecycle status of a source consent record."""

    PENDING = "pending"
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class TargetType(str, PyEnum):
    """Scraping target types."""

    SINGLE_PAGE = "SINGLE_PAGE"
    PAGINATED = "PAGINATED"
    SPIDER = "SPIDER"
    API_ENDPOINT = "API_ENDPOINT"


class SourceCategory(str, PyEnum):
    """Source category for scraping targets."""

    API = "API"
    CRM = "CRM"
    ERP = "ERP"
    HRIS = "HRIS"
    MARKETING = "MARKETING"
    FINANCE = "FINANCE"
    PRODUCT = "PRODUCT"
    SUPPORT = "SUPPORT"
    GENERAL = "GENERAL"


class TargetStatus(str, PyEnum):
    """Scraping target lifecycle status."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"
    ERROR = "ERROR"


class ComplianceEventType(str, PyEnum):
    """Compliance event types."""

    ROBOTS_TXT_CHECK = "ROBOTS_TXT_CHECK"
    RATE_LIMIT_APPLIED = "RATE_LIMIT_APPLIED"
    PII_DETECTED = "PII_DETECTED"
    PII_REDACTED = "PII_REDACTED"
    DOMAIN_BLOCKED = "DOMAIN_BLOCKED"
    DOMAIN_ALLOWED = "DOMAIN_ALLOWED"
    CAPTCHA_ENCOUNTERED = "CAPTCHA_ENCOUNTERED"
    BLOCKED_BY_TARGET = "BLOCKED_BY_TARGET"
    TERMS_VIOLATION = "TERMS_VIOLATION"
    DATA_RETENTION_DELETION = "DATA_RETENTION_DELETION"


class ProxyRotationStrategy(str, PyEnum):
    """Proxy rotation strategies."""

    ROUND_ROBIN = "ROUND_ROBIN"
    RANDOM = "RANDOM"
    GEO_BASED = "GEO_BASED"
    SESSION_BASED = "SESSION_BASED"
    LEAST_USED = "LEAST_USED"


class ProxyType(str, PyEnum):
    """Proxy types."""

    RESIDENTIAL = "RESIDENTIAL"
    DATACENTER = "DATACENTER"
    MOBILE = "MOBILE"


class ProxyStatus(str, PyEnum):
    """Proxy health status."""

    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


class TriggeredBy(str, PyEnum):
    """Job trigger sources."""

    SCHEDULE = "SCHEDULE"
    MANUAL = "MANUAL"
    API = "API"
    WEBHOOK = "WEBHOOK"
    WORKFLOW = "WORKFLOW"


class RetryBackoff(str, PyEnum):
    """Retry backoff strategies."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"


class CrawlPath(str, PyEnum):
    """Ingestion path selection for a scraping target.

    Controls whether the crawler uses HTTPX fast path,
    Playwright browser automation, or hybrid fallback.
    """

    FAST = "fast"  # HTTPX only - fastest for static content
    BROWSER = "browser"  # Playwright only - handles dynamic content
    FAST_WITH_FALLBACK = "fast_fallback"  # HTTPX first, browser if quality fails


class ScrapingJobType(str, PyEnum):
    """Skill-aware job types for Layer 1 Source Intelligence.

    Extends the generic scraping pipeline with purpose-driven
    intelligence intake workflows.
    """

    GENERIC_SCRAPE = "generic_scrape"
    LICENSING_COMPANY_INTAKE = "licensing_company_intake"
    PROSPECT_RESEARCH = "prospect_research"


class AuthenticationType(str, PyEnum):
    """Authentication types for targets."""

    NONE = "NONE"
    BEARER = "BEARER"
    API_KEY = "API_KEY"
    BASIC = "BASIC"
    OAUTH2 = "OAUTH2"


class BrowserEngine(str, PyEnum):
    """Browser engines."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class LLMProvider(str, PyEnum):
    """LLM providers for AI extraction."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"


class PIIStatus(str, PyEnum):
    """PII detection status."""

    CLEAN = "clean"
    FLAGGED = "flagged"
    QUARANTINED = "quarantined"


# =============================================================================
# ENTITIES
# =============================================================================


class IngestedSource(Base):
    """Canonical source record for the unified source ingestion boundary.

    A logical source owned by a tenant and account. Each mutation creates a new
    immutable SourceVersion rather than overwriting existing evidence.
    """

    __tablename__ = "ingested_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    account_id = Column(String(255), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    external_reference = Column(String(500), nullable=True)
    fingerprint = Column(String(64), nullable=False, index=True)
    latest_version_id = Column(UUID(as_uuid=True), nullable=True)
    latest_version_number = Column(Integer, default=1, nullable=False)
    status = Column(String(50), nullable=False, default="active")
    retention_class = Column(String(50), nullable=True)
    # v3.0 custody and consent
    custody_mode = Column(String(1), nullable=False, default=CustodyMode.FULL_CUSTODY.value)
    consent_id = Column(UUID(as_uuid=True), ForeignKey("source_consents.id", ondelete="SET NULL"), nullable=True, index=True)
    # v3.0 external identity (excludes custody/runtime from deduplication)
    external_system = Column(String(100), nullable=True)
    external_object_type = Column(String(100), nullable=True)
    external_object_id = Column(String(255), nullable=True)
    external_version = Column(String(100), nullable=True)
    snapshot_hash = Column(String(64), nullable=True)
    field_scope_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by = Column(UUID(as_uuid=True), nullable=False)

    consent = relationship("SourceConsent", back_populates="sources")
    versions = relationship("SourceVersion", back_populates="source", cascade="all, delete-orphan", order_by="SourceVersion.version_number")
    runs = relationship("SourceIngestionRun", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "fingerprint", name="uix_ingested_source_fingerprint"),
        Index("idx_ingested_sources_tenant_account", "tenant_id", "account_id", "created_at"),
        Index("idx_ingested_sources_external_identity", "tenant_id", "external_system", "external_object_type", "external_object_id"),
        Index("idx_ingested_sources_consent", "consent_id"),
    )


class SourceVersion(Base):
    """Immutable version of an ingested source's content."""

    __tablename__ = "source_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingested_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False)
    raw_storage_uri = Column(Text, nullable=False)
    raw_bytes_size = Column(Integer, nullable=False, default=0)
    media_type = Column(String(100), nullable=False)
    language = Column(String(10), nullable=True)
    status = Column(String(50), nullable=False, default="stored")
    meta = Column(JSONB, default=dict)
    # v3.0: custody-aware storage
    fetched_at = Column(DateTime(timezone=True), nullable=True)
    source_uri = Column(Text, nullable=True)
    storage_backend = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)

    chunks = relationship("EvidenceChunk", back_populates="version", cascade="all, delete-orphan")
    normalized = relationship("NormalizedDocument", back_populates="version", uselist=False, cascade="all, delete-orphan")
    source = relationship("IngestedSource", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("source_id", "version_number", name="uix_source_version_number"),
        Index("idx_source_versions_source_created", "source_id", "created_at"),
    )


class IngestionRunStepStatus(str, PyEnum):
    """Status of a single pipeline stage attempt."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SourceIngestionRun(Base):
    """Durable asynchronous run for a source through the L1-L6 pipeline."""

    __tablename__ = "source_ingestion_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingested_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(50), nullable=False, default=IngestionRunStatus.ACCEPTED.value)
    requested_outputs = Column(JSONB, default=list)
    idempotency_key = Column(String(255), nullable=True, index=True)
    correlation_id = Column(String(100), nullable=True)
    stage_metadata = Column(JSONB, default=dict)
    error_code = Column(String(100), nullable=True)
    error_detail_safe = Column(Text, nullable=True)
    current_step_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    # v3.0 connector and consent binding
    connector_name = Column(String(100), nullable=True)
    connector_config_hash = Column(String(64), nullable=True)
    policy_version = Column(String(50), nullable=True)
    source_snapshot_hash = Column(String(64), nullable=True)
    consent_id = Column(UUID(as_uuid=True), ForeignKey("source_consents.id", ondelete="SET NULL"), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)

    source = relationship("IngestedSource", back_populates="runs")
    consent = relationship("SourceConsent", back_populates="runs")
    version = relationship("SourceVersion")
    steps = relationship("IngestionRunStep", back_populates="run", cascade="all, delete-orphan", order_by="IngestionRunStep.created_at")

    __table_args__ = (
        Index("idx_source_ingestion_runs_tenant_status", "tenant_id", "status"),
        Index("idx_source_ingestion_runs_idempotency", "tenant_id", "idempotency_key"),
        Index("idx_source_ingestion_runs_consent", "consent_id"),
    )


class IngestionRunStep(Base):
    """A single stage attempt within a source ingestion pipeline run.

    Records idempotency, input/output artifact references, errors, and timing
    so that the pipeline can resume, retry, and audit every stage.
    """

    __tablename__ = "ingestion_run_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("source_ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_name = Column(String(50), nullable=False)
    attempt = Column(Integer, nullable=False, default=1)
    status = Column(
        String(50),
        nullable=False,
        default=IngestionRunStepStatus.PENDING.value,
    )
    input_artifact_ids = Column(JSONB, default=dict)
    output_artifact_ids = Column(JSONB, default=dict)
    error_code = Column(String(100), nullable=True)
    error_detail_safe = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    run = relationship("SourceIngestionRun", back_populates="steps")

    __table_args__ = (
        UniqueConstraint("run_id", "stage_name", "attempt", name="uq_ingestion_run_step_stage_attempt"),
        Index("idx_ingestion_run_steps_tenant_status", "tenant_id", "status"),
        Index("idx_ingestion_run_steps_run_stage", "run_id", "stage_name"),
        Index("idx_ingestion_run_steps_run_created", "run_id", "created_at"),
    )


class NormalizedDocument(Base):
    """Common normalized representation produced by an L1 connector."""

    __tablename__ = "normalized_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    document_id = Column(String(255), nullable=False, unique=True, index=True)
    media_type = Column(String(100), nullable=False)
    language = Column(String(10), nullable=True)
    content = Column(Text, nullable=False)
    sections = Column(JSONB, default=list)
    participants = Column(JSONB, default=list)
    source_metadata = Column(JSONB, default=dict)
    normalizer_version = Column(String(50), nullable=False)
    chunks = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    version = relationship("SourceVersion", back_populates="normalized")

    __table_args__ = (
        Index("idx_normalized_documents_tenant", "tenant_id", "created_at"),
    )


class SourceConsent(Base):
    """Consent record for a source ingestion scope.

    v3.0 requires explicit consent before a source ingestion run can be created.
    A single consent record may cover one or more sources of the same scope.
    """

    __tablename__ = "source_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    account_id = Column(String(255), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    scope = Column(JSONB, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default=SourceConsentStatus.PENDING.value)
    consent_hash = Column(String(64), nullable=False)
    granted_by = Column(UUID(as_uuid=True), nullable=True)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    sources = relationship("IngestedSource", back_populates="consent")
    runs = relationship("SourceIngestionRun", back_populates="consent")

    __table_args__ = (
        Index("idx_source_consents_tenant_account", "tenant_id", "account_id", "created_at"),
        Index("idx_source_consents_status", "tenant_id", "status"),
    )


class EvidenceChunk(Base):
    """Atomic evidence unit produced by the L1 chunking stage.

    Every chunk keeps an anchor (provenance pointer) back to its source version
    and the raw text segment. v3.0 requires every chunk to be linkable as
    evidence for downstream signals and claims.
    """

    __tablename__ = "evidence_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default=EvidenceChunkStatus.ACTIVE.value)
    content = Column(Text, nullable=False)
    anchor = Column(JSONB, nullable=False, default=dict)
    confidence = Column(Numeric(3, 2), nullable=False, default=1.00)
    trust_score = Column(Numeric(3, 2), nullable=False, default=1.00)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    version = relationship("SourceVersion", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("source_version_id", "chunk_index", name="uq_evidence_chunk_version_index"),
        Index("idx_evidence_chunks_version", "source_version_id", "created_at"),
        Index("idx_evidence_chunks_tenant", "tenant_id", "status"),
    )


class ScrapingTarget(Base):
    """Configuration entity for a scraping target.

    Defines what to scrape, how to extract it, scheduling, rate limits, etc.
    """

    __tablename__ = "scraping_targets"

    # Primary Identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Target Configuration
    url = Column(Text, nullable=False)
    url_pattern = Column(String(500), nullable=True)  # Regex for URL matching
    target_type = Column(String(50), nullable=False, default=TargetType.SINGLE_PAGE.value)
    source_category = Column(String(50), nullable=True)

    # Extraction Configuration (JSONB for nested structure)
    extraction_config = Column(JSONB, default=dict)  # {
    # "method": "AI_LLM|DETERMINISTIC|HYBRID",
    # "llm_provider": "openai|anthropic|azure_openai",
    # "extraction_schema": {...},  # JSON Schema
    # "visual_hints": false,
    # "max_depth": 2,
    # "follow_links": true,
    # "link_selectors": [...]
    # }

    # Browser Configuration
    browser_config = Column(JSONB, default=dict)  # {
    # "engine": "chromium",
    # "headless": true,
    # "viewport": {"width": 1920, "height": 1080},
    # "user_agent": "...",
    # "javascript_enabled": true,
    # "wait_for_selector": null,
    # "wait_timeout": 30000,
    # "stealth_mode": true
    # }

    # Scheduling
    schedule = Column(JSONB, nullable=True)  # {
    # "enabled": true,
    # "cron_expression": "0 0 * * *",
    # "timezone": "UTC",
    # "max_concurrent_jobs": 1
    # }

    # Rate Limiting
    rate_limit = Column(JSONB, default=dict)  # {
    # "requests_per_second": 1,
    # "requests_per_minute": 30,
    # "requests_per_hour": 500,
    # "burst_limit": 5,
    # "retry_attempts": 3,
    # "retry_backoff": "exponential",
    # "retry_delay_ms": 1000
    # }

    # Compliance Settings
    compliance = Column(JSONB, default=dict)  # {
    # "respect_robots_txt": true,
    # "user_agent_string": "...",
    # "crawl_delay_seconds": 1,
    # "domain_allowlist": [],
    # "domain_blocklist": [],
    # "pii_redaction_enabled": true,
    # "sensitive_field_patterns": []
    # }

    # Proxy Configuration
    proxy_config = Column(JSONB, default=dict)  # {
    # "enabled": false,
    # "rotation_strategy": "ROUND_ROBIN|RANDOM|GEO_BASED|SESSION_BASED",
    # "proxy_pool_id": "uuid",
    # "sticky_sessions": false,
    # "session_duration_minutes": 30
    # }

    # Authentication
    authentication = Column(JSONB, nullable=True)  # {
    # "type": "NONE|BEARER|API_KEY|BASIC|OAUTH2",
    # "credentials_ref": "secret_manager_key"
    # }

    # Metadata
    status = Column(String(50), nullable=False, default=TargetStatus.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )
    created_by = Column(UUID(as_uuid=True), nullable=False)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    average_execution_time_ms = Column(Integer, default=0)
    tags = Column(JSONB, default=list)  # ["tag1", "tag2"]

    # Relationships
    jobs = relationship("ScrapingJob", back_populates="target", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_scraping_targets_tenant_status", "tenant_id", "status"),
        Index("idx_scraping_targets_created", "tenant_id", "created_at"),
    )


class ScrapingJob(Base):
    """Execution entity for a scraping job.

    Represents a single execution instance of a ScrapingTarget.
    Contains snapshot of target config at job creation time.
    """

    __tablename__ = "scraping_jobs"

    # Primary Identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    target_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Job Configuration (snapshot of target config at creation)
    configuration = Column(JSONB, default=dict)  # ScrapingTargetSnapshot

    # Skill-aware metadata
    job_type = Column(
        String(50), nullable=False, default=ScrapingJobType.GENERIC_SCRAPE.value
    )
    skill_name = Column(String(100), nullable=True)
    target_entity_id = Column(String(255), nullable=True)
    target_entity_type = Column(String(100), nullable=True)
    output_contract = Column(String(100), nullable=True)
    downstream_events = Column(JSONB, default=list)

    # Execution State
    status = Column(String(50), nullable=False, default=JobStatus.PENDING.value, index=True)
    priority = Column(Integer, default=5)  # 1-10, higher = more urgent

    # Timing
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_duration_ms = Column(Integer, nullable=True)

    # Progress Tracking
    progress_total_pages = Column(Integer, nullable=True)
    progress_processed_pages = Column(Integer, default=0)
    progress_failed_pages = Column(Integer, default=0)
    progress_current_url = Column(Text, nullable=True)
    progress_stage = Column(String(50), default=PipelineStage.INIT.value)
    progress_percent_complete = Column(Integer, default=0)

    # Results Summary
    results_raw_content_count = Column(Integer, default=0)
    results_extracted_record_count = Column(Integer, default=0)
    results_storage_bytes_used = Column(Integer, default=0)
    results_output_location = Column(Text, nullable=True)

    # Resource Usage
    resources_browser_sessions_used = Column(Integer, default=0)
    resources_proxy_requests_made = Column(Integer, default=0)
    resources_llm_tokens_consumed = Column(Integer, default=0)
    resources_compute_time_ms = Column(Integer, default=0)

    # Audit
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    triggered_by = Column(String(50), default=TriggeredBy.MANUAL.value)
    correlation_id = Column(String(100), nullable=True)  # Distributed tracing
    idempotency_key = Column(String(255), nullable=True)  # API-level idempotency

    # Relationships
    target = relationship("ScrapingTarget", back_populates="jobs")
    stages = relationship("JobStageDetail", back_populates="job", cascade="all, delete-orphan")
    errors = relationship("JobError", back_populates="job", cascade="all, delete-orphan")
    raw_contents = relationship("RawContent", back_populates="job", cascade="all, delete-orphan")
    extracted_data = relationship(
        "ExtractedData", back_populates="job", cascade="all, delete-orphan"
    )
    compliance_logs = relationship("ComplianceLog", back_populates="job")

    __table_args__ = (
        Index("idx_scraping_jobs_tenant_status", "tenant_id", "status"),
        Index("idx_scraping_jobs_target", "target_id", "created_at"),
        Index("idx_scraping_jobs_status_created", "status", "created_at"),
    )


class JobStageDetail(Base):
    """Pipeline stage execution details for a job."""

    __tablename__ = "job_stage_details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    stage = Column(String(50), nullable=False)  # PipelineStage value
    status = Column(
        String(50), nullable=False, default="PENDING"
    )  # PENDING, RUNNING, COMPLETED, FAILED

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    error_message = Column(Text, nullable=True)
    meta = Column(JSONB, default=dict)  # Stage-specific details

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    job = relationship("ScrapingJob", back_populates="stages")

    __table_args__ = (
        Index("idx_job_stage_details_job_stage", "job_id", "stage"),
        UniqueConstraint("job_id", "stage", name="uq_job_stage"),
    )


class JobError(Base):
    """Error tracking for scraping jobs."""

    __tablename__ = "job_errors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    stage = Column(String(50), nullable=False)  # PipelineStage where error occurred
    error_code = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    url = Column(Text, nullable=True)  # URL being processed when error occurred

    retryable = Column(Boolean, default=True)
    retry_count = Column(Integer, default=0)

    occurred_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(Text, nullable=True)

    # Relationships
    job = relationship("ScrapingJob", back_populates="errors")

    __table_args__ = (
        Index("idx_job_errors_job_occurred", "job_id", "occurred_at"),
        Index("idx_job_errors_retryable", "retryable", "retry_count"),
    )


class RawContent(Base):
    """Raw crawled content storage references."""

    __tablename__ = "raw_content"

    # Primary Identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    target_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_targets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Source Information
    source_url = Column(Text, nullable=False)
    source_final_url = Column(Text, nullable=True)  # After redirects
    source_domain = Column(String(255), nullable=False, index=True)
    source_ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    source_accessed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    source_http_status = Column(Integer, nullable=True)
    source_headers = Column(JSONB, default=dict)
    source_content_type = Column(String(255), nullable=True)
    source_content_length = Column(Integer, nullable=True)

    # Storage References (S3/MinIO paths)
    storage_html_path = Column(Text, nullable=True)
    storage_screenshot_path = Column(Text, nullable=True)
    storage_dom_snapshot_path = Column(Text, nullable=True)
    storage_har_path = Column(Text, nullable=True)
    storage_text_content_path = Column(Text, nullable=True)

    # Content Metadata
    meta_title = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    meta_language = Column(String(10), nullable=True)
    meta_charset = Column(String(50), nullable=True)
    meta_viewport = Column(String(255), nullable=True)
    meta_canonical_url = Column(Text, nullable=True)
    meta_robots_meta = Column(String(255), nullable=True)
    meta_og_tags = Column(JSONB, default=dict)
    meta_structured_data = Column(JSONB, default=list)  # JSON-LD, microdata

    # Capture Information
    capture_method = Column(String(50), default="DYNAMIC")  # STATIC, DYNAMIC, HYBRID
    capture_browser_version = Column(String(100), nullable=True)
    capture_rendering_engine = Column(String(100), nullable=True)
    capture_javascript_executed = Column(Boolean, default=True)
    capture_wait_time_ms = Column(Integer, default=0)
    capture_scroll_depth = Column(Integer, nullable=True)
    capture_interactions = Column(JSONB, default=list)  # ["click", "hover"]

    # Content Hash for deduplication
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(
        UUID(as_uuid=True), ForeignKey("raw_content.id", ondelete="SET NULL"), nullable=True
    )

    # Processing Status
    processing_status = Column(
        String(50), default="PENDING"
    )  # PENDING, EXTRACTING, EXTRACTED, FAILED
    extracted_data_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Retention
    retention_raw_content_expiry_days = Column(Integer, default=30)
    retention_screenshot_expiry_days = Column(Integer, default=30)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    job = relationship("ScrapingJob", back_populates="raw_contents")
    duplicate_of = relationship("RawContent", remote_side=[id])

    __table_args__ = (
        Index("idx_raw_content_job_status", "job_id", "processing_status"),
        Index("idx_raw_content_tenant_domain", "tenant_id", "source_domain"),
        Index("idx_raw_content_hash", "tenant_id", "content_hash"),
    )


class ExtractedData(Base):
    """Structured extracted data from raw content."""

    __tablename__ = "extracted_data"

    # Primary Identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_content_id = Column(
        UUID(as_uuid=True),
        ForeignKey("raw_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    target_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_targets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Extraction Method
    extraction_method = Column(String(50), nullable=False)
    extraction_llm_model = Column(String(100), nullable=True)
    extraction_prompt_version = Column(String(50), nullable=True)
    extraction_time_ms = Column(Integer, default=0)
    extraction_confidence_score = Column(Numeric(3, 2), default=0.00)  # 0.0 - 1.0
    extraction_schema_version = Column(String(50), nullable=True)

    # Structured Output
    data = Column(JSONB, default=dict)  # Schema-defined fields

    # Validation Results
    validation_schema_valid = Column(Boolean, default=True)
    validation_errors = Column(JSONB, default=list)
    validation_required_fields_present = Column(JSONB, default=list)
    validation_required_fields_missing = Column(JSONB, default=list)
    validation_data_quality_score = Column(Numeric(3, 2), default=0.00)

    # Provenance
    provenance_source_url = Column(Text, nullable=False)
    provenance_extracted_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    provenance_extraction_version = Column(String(50), nullable=True)

    # Post-Processing
    post_pii_redaction_applied = Column(Boolean, default=False)
    post_redacted_fields = Column(JSONB, default=list)
    post_normalized_fields = Column(JSONB, default=list)
    post_enriched_fields = Column(JSONB, default=list)

    # Ontology Mapping
    ontology_concept_ids = Column(JSONB, default=list)
    ontology_relationship_ids = Column(JSONB, default=list)
    ontology_mapped_at = Column(DateTime(timezone=True), nullable=True)
    ontology_mapping_confidence = Column(Numeric(3, 2), nullable=True)

    # Storage
    storage_path = Column(Text, nullable=True)
    format = Column(String(20), default="JSON")  # JSON, JSONL, PARQUET, MARKDOWN
    size_bytes = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    job = relationship("ScrapingJob", back_populates="extracted_data")
    raw_content = relationship("RawContent")

    __table_args__ = (
        Index("idx_extracted_data_job", "job_id", "created_at"),
        Index("idx_extracted_data_tenant_quality", "tenant_id", "validation_data_quality_score"),
    )


class ComplianceLog(Base):
    """Compliance audit trail."""

    __tablename__ = "compliance_logs"

    # Primary Identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_targets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Event Details
    event_type = Column(String(50), nullable=False, index=True)  # ComplianceEventType
    severity = Column(String(20), nullable=False, default="INFO")  # INFO, WARNING, ERROR, CRITICAL

    # robots.txt Compliance
    robots_txt_check = Column(JSONB, nullable=True)  # {
    # "url": "...",
    # "robots_txt_url": "...",
    # "user_agent": "...",
    # "allowed": true,
    # "crawl_delay": 1,
    # "sitemap_urls": [...],
    # "rules": [...]
    # }

    # Rate Limiting
    rate_limit_event = Column(JSONB, nullable=True)  # {
    # "domain": "...",
    # "requests_in_window": 10,
    # "limit": 30,
    # "window_seconds": 60,
    # "action_taken": "DELAYED|THROTTLED|BLOCKED",
    # "delay_ms": 1000
    # }

    # PII Detection
    pii_detection = Column(JSONB, nullable=True)  # {
    # "detection_method": "REGEX|ML_MODEL|LLM",
    # "patterns_detected": [...],
    # "redaction_applied": true,
    # "redacted_count": 5
    # }

    # Domain Policy
    domain_policy = Column(JSONB, nullable=True)  # {
    # "domain": "...",
    # "action": "ALLOWED|BLOCKED|REQUIRES_REVIEW",
    # "policy_type": "ALLOWLIST|BLOCKLIST|DEFAULT",
    # "reason": "..."
    # }

    # Request Details
    request_url = Column(Text, nullable=False)
    request_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    request_ip_address = Column(String(45), nullable=True)
    request_proxy_used = Column(String(500), nullable=True)
    request_user_agent = Column(String(500), nullable=True)
    request_headers = Column(JSONB, default=dict)

    # Response
    response_status_code = Column(Integer, nullable=True)
    response_action_taken = Column(String(100), nullable=True)
    response_reason = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    meta = Column(JSONB, default=dict)

    # Relationships
    job = relationship("ScrapingJob", back_populates="compliance_logs")

    __table_args__ = (
        Index("idx_compliance_logs_tenant_event", "tenant_id", "event_type"),
        Index("idx_compliance_logs_timestamp", "created_at"),
        Index("idx_compliance_logs_job", "job_id", "created_at"),
    )


class ProxyPool(Base):
    """Proxy pool for rotating requests."""

    __tablename__ = "proxy_pools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Proxies stored as JSONB array
    proxies = Column(JSONB, default=list)  # [{
    # "id": "uuid",
    # "host": "...",
    # "port": 8080,
    # "protocol": "http|https|socks5",
    # "username": "...",
    # "password_ref": "secret_key",
    # "country": "US",
    # "region": "...",
    # "city": "...",
    # "isp": "...",
    # "type": "RESIDENTIAL|DATACENTER|MOBILE",
    # "status": "ACTIVE|FAILED|QUARANTINED",
    # "failure_count": 0,
    # "last_used_at": "...",
    # "last_success_at": "...",
    # "average_response_time_ms": 0
    # }]

    # Rotation Configuration
    rotation_strategy = Column(String(50), default=ProxyRotationStrategy.ROUND_ROBIN.value)
    rotation_max_failures_before_quarantine = Column(Integer, default=3)
    rotation_quarantine_duration_minutes = Column(Integer, default=60)
    rotation_health_check_interval_minutes = Column(Integer, default=5)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        Index("idx_proxy_pools_tenant", "tenant_id", "created_at"),
        UniqueConstraint("tenant_id", "name", name="uq_proxy_pool_tenant_name"),
    )


class RobotsTxtCache(Base):
    """Cache for robots.txt files."""

    __tablename__ = "robots_txt_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(255), nullable=False, unique=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # LEGACY: System-owned only. Global public cache requires no tenant isolation.

    content = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    rules = Column(JSONB, default=dict)

    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    http_status = Column(Integer, nullable=True)

    is_valid = Column(Boolean, default=True)
    parse_error = Column(Text, nullable=True)

    __table_args__ = (Index("idx_robots_txt_cache_tenant", "tenant_id", "domain"),)


# =============================================================================
# QUEUE ITEM (Updated for new model)
# =============================================================================


class CrawlQueueItem(Base):
    """Items waiting to be crawled - updated for ScrapingJob."""

    __tablename__ = "crawl_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    url = Column(Text, nullable=False)
    domain = Column(String(255), nullable=False, index=True)

    depth = Column(Integer, default=0)
    parent_url = Column(Text, nullable=True)

    priority = Column(Integer, default=5)
    status = Column(
        String(50), default="PENDING", index=True
    )  # PENDING, PROCESSING, COMPLETED, FAILED, RETRYING

    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "job_id", "url", name="uq_crawl_queue_tenant_job_url"),
        Index("idx_crawl_queue_tenant_job_status", "tenant_id", "job_id", "status"),
        Index("idx_crawl_queue_next_retry", "status", "next_retry_at"),
        Index("idx_crawl_queue_domain_priority", "domain", "priority"),
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def create_scraping_target(
    tenant_id: uuid.UUID,
    name: str,
    url: str,
    target_type: TargetType,
    created_by: uuid.UUID,
    description: str | None = None,
    extraction_config: dict | None = None,
    browser_config: dict | None = None,
    schedule: dict | None = None,
    rate_limit: dict | None = None,
    compliance: dict | None = None,
    proxy_config: dict | None = None,
    tags: list[str] | None = None,
    source_category: SourceCategory | None = None,
) -> ScrapingTarget:
    """Factory function to create a new scraping target."""
    return ScrapingTarget(
        tenant_id=tenant_id,
        name=name,
        url=url,
        target_type=target_type.value,
        source_category=source_category.value if source_category else None,
        created_by=created_by,
        description=description,
        extraction_config=extraction_config or {},
        browser_config=browser_config or {},
        schedule=schedule,
        rate_limit=rate_limit or {},
        compliance=compliance or {},
        proxy_config=proxy_config or {},
        tags=tags or [],
    )


def create_scraping_job(
    tenant_id: uuid.UUID,
    target_id: uuid.UUID,
    created_by: uuid.UUID,
    configuration: dict,
    priority: int = 5,
    triggered_by: TriggeredBy = TriggeredBy.MANUAL,
    correlation_id: str | None = None,
    idempotency_key: str | None = None,
) -> ScrapingJob:
    """Factory function to create a new scraping job."""
    return ScrapingJob(
        tenant_id=tenant_id,
        target_id=target_id,
        created_by=created_by,
        configuration=configuration,
        priority=priority,
        triggered_by=triggered_by.value,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
    )


def create_proxy_pool(
    tenant_id: uuid.UUID,
    name: str,
    proxies: list[dict] | None = None,
    rotation_strategy: ProxyRotationStrategy = ProxyRotationStrategy.ROUND_ROBIN,
) -> ProxyPool:
    """Factory function to create a proxy pool."""
    return ProxyPool(
        tenant_id=tenant_id,
        name=name,
        proxies=proxies or [],
        rotation_strategy=rotation_strategy.value,
    )


# =============================================================================
# CRAWL DECISION MODEL (for Smart Router)
# =============================================================================


class CrawlDecision(Base):
    """Canonical record of crawl routing decisions.

    Stores immutable history of routing decisions, quality assessments,
    and execution outcomes for debugging, metrics, and optimization.
    """

    __tablename__ = "crawl_decisions"

    # Primary key
    decision_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    job_id = Column(UUID(as_uuid=True), ForeignKey("scraping_jobs.id"), nullable=True, index=True)
    # Tenant context
    # - NULL = global/router-level decision not tied to a specific tenant
    # - UUID = tenant-scoped decision
    # RLS policy intentionally allows all tenants to read NULL-tenant rows
    # (global routing rules, Smart Router observability data)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # no FK — tenant table is in Layer 4

    # Request context
    url = Column(Text, nullable=False)
    domain = Column(String(255), nullable=False, index=True)
    requested_path = Column(String(20), nullable=False)  # fast/browser/fast_fallback

    # Routing decision
    router_decision = Column(String(20), nullable=False)  # What router chose
    router_rule = Column(String(50), nullable=False, index=True)  # Which rule triggered

    # Quality evaluation
    quality_passed = Column(Boolean, nullable=True)
    quality_checks = Column(JSONB, nullable=True)  # Dict of check_name -> bool
    fallback_reason = Column(String(50), nullable=True, index=True)

    # Execution outcome
    final_path = Column(String(20), nullable=False)  # What actually executed
    status_code = Column(Integer, nullable=True)

    # Performance metrics
    fast_duration_ms = Column(Integer, nullable=False, default=0)
    browser_duration_ms = Column(Integer, nullable=True)
    fetch_time_ms = Column(Integer, nullable=False, default=0)
    bytes_transferred = Column(Integer, nullable=False, default=0)

    # Content analysis
    spa_detected = Column(Boolean, nullable=False, default=False)
    text_length = Column(Integer, nullable=False, default=0)

    # Error tracking
    error_type = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_crawl_decisions_job_created", "job_id", "created_at"),
        Index("idx_crawl_decisions_domain_created", "domain", "created_at"),
    )


# =============================================================================
# SKILL-SPECIFIC OUTPUT MODELS
# =============================================================================


class SourceCorpus(Base):
    """Structured output from Licensing Company Ontology Intake Skill.

    Packages normalized, provenance-backed source materials
    for downstream ontology construction (Layer 2/3).
    """

    __tablename__ = "source_corpuses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Entity reference
    company_id = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=False)
    corpus_type = Column(
        String(50), nullable=False, default="licensing_company_ontology_seed"
    )

    # Aggregated source intelligence
    source_groups = Column(JSONB, default=list)  # [{"source_type": "product_page", "count": 18}]
    candidate_concepts = Column(JSONB, default=list)  # ["sales enablement", ...]
    provenance = Column(JSONB, default=list)  # [{"url": "...", "source_type": "...", ...}]

    # Downstream tracking
    extraction_status = Column(
        String(50),
        nullable=False,
        default="ready_for_extraction",
    )  # pending, ready_for_extraction, sent_to_layer_2, failed

    # Job linkage
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_source_corpuses_tenant_created", "tenant_id", "created_at"),
        Index("idx_source_corpuses_company", "tenant_id", "company_id"),
    )


class AccountIntelligencePacket(Base):
    """Structured output from Prospect Research Skill.

    Packages account intelligence for downstream signal
    extraction and value hypothesis generation (Layer 2/4).
    """

    __tablename__ = "account_intelligence_packets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Entity reference
    account_id = Column(String(255), nullable=True)
    account_name = Column(String(255), nullable=False)
    packet_type = Column(String(50), nullable=False, default="prospect_research")

    # Aggregated intelligence
    company_profile = Column(JSONB, default=dict)  # {size, geography, business_model, industry}
    observed_signals = Column(JSONB, default=list)  # [{signal, source, confidence, detail}]
    likely_pain_areas = Column(JSONB, default=list)  # ["distributed seller onboarding", ...]
    likely_stakeholders = Column(JSONB, default=list)  # ["CRO", "VP Sales Enablement", ...]
    source_references = Column(JSONB, default=list)  # [{url, source_type, confidence}]

    # Quality and routing
    confidence_summary = Column(JSONB, default=dict)  # {signal_count, high_confidence_signals}
    next_recommended_events = Column(JSONB, default=list)

    # Job linkage
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scraping_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "idx_account_intel_packets_tenant_created", "tenant_id", "created_at"
        ),
        Index("idx_account_intel_packets_account", "tenant_id", "account_id"),
    )


# =============================================================================
# EVENT OUTBOX
# =============================================================================


class OutboxStatus(str, PyEnum):
    """Lifecycle states for an EventOutbox record."""

    PENDING = "pending"
    DISPATCHED = "dispatched"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class EventOutbox(Base):
    """Durable transactional outbox for Layer 1 downstream event emission.

    Records are inserted in the same transaction as the skill output storage.
    A Celery dispatcher task delivers each event to configured sinks and
    marks it dispatched. Failed deliveries are retried with backoff up to
    MAX_DISPATCH_ATTEMPTS, then moved to dead_letter.
    """

    __tablename__ = "event_outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)

    # Event identity
    event_type = Column(String(100), nullable=False)
    aggregate_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(255), nullable=False)

    # Pipeline routing (nullable — used for canonical source-ingestion pipeline events)
    stage_name = Column(String(50), nullable=True, index=True)
    topic = Column(String(100), nullable=True, index=True)

    # Full event payload (tenant_id, job_id, output_id, output_contract, emitted_at, ...)
    payload = Column(JSONB, nullable=False)

    # Delivery state
    status = Column(
        String(50),
        nullable=False,
        default=OutboxStatus.PENDING.value,
        server_default="pending",
    )
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    last_error = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    dead_lettered_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_event_outbox_status_created", "status", "created_at"),
        Index("idx_event_outbox_tenant_id", "tenant_id"),
        Index("idx_event_outbox_event_type", "event_type"),
        Index("idx_event_outbox_aggregate", "aggregate_type", "aggregate_id"),
    )


# =============================================================================
# TENANT REGISTRY (system table — no RLS)
# =============================================================================


class TenantRegistry(Base):
    """System registry of active tenants for maintenance operations.

    Explicitly NOT covered by RLS.  Populated when scraping jobs are
    created so that system maintenance tasks can enumerate tenants
    without bypassing tenant-owned tables.
    """

    __tablename__ = "tenant_registry"

    tenant_id = Column(UUID(as_uuid=True), primary_key=True)
    registered_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_activity_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    is_active = Column(Boolean, nullable=False, default=True)



# =============================================================================
# SQLALCHEMY EVENT LISTENERS
# =============================================================================


@event.listens_for(ScrapingJob, "after_insert")
def _upsert_tenant_registry(mapper, connection, target):
    """Keep tenant_registry in sync with active tenants.

    Runs in the same transaction as the job insert so the registry
    is always consistent without requiring a separate commit.
    """
    if target.tenant_id is not None:
        from datetime import UTC, datetime

        from sqlalchemy import text
        now = datetime.now(UTC)
        connection.execute(
            text("""
                INSERT INTO tenant_registry (tenant_id, registered_at, last_activity_at, is_active)
                VALUES (:tenant_id, :now, :now, true)
                ON CONFLICT (tenant_id) DO UPDATE SET
                    last_activity_at = EXCLUDED.last_activity_at,
                    is_active = true;
            """),
            {"tenant_id": str(target.tenant_id), "now": now},
        )
