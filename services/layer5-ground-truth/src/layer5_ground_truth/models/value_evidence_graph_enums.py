"""Enums for the Value Evidence Graph."""
from enum import Enum as PyEnum


class ClaimType(str, PyEnum):
    """Semantic category of a ValueClaim."""

    COST_SAVINGS = "cost_savings"
    REVENUE_GROWTH = "revenue_growth"
    RISK_REDUCTION = "risk_reduction"
    PRODUCTIVITY_GAIN = "productivity_gain"
    CYCLE_TIME_REDUCTION = "cycle_time_reduction"
    COMPLIANCE_IMPROVEMENT = "compliance_improvement"
    CUSTOMER_EXPERIENCE = "customer_experience"
    STRATEGIC_CAPABILITY = "strategic_capability"


class ClaimStatus(str, PyEnum):
    """Lifecycle states of a ValueClaim.

    A claim progresses from raw insight to customer-facing, auditable,
    and eventually realized value statement.
    """

    DRAFT = "draft"
    SUPPORTED = "supported"
    MODELED = "modeled"
    APPROVED = "approved"
    PUBLISHED = "published"
    CHALLENGED = "challenged"
    COMMITTED = "committed"
    VALIDATED = "validated"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"


class Confidence(str, PyEnum):
    """Confidence level for a claim, assumption, or piece of evidence."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScenarioType(str, PyEnum):
    """Scenario variety for value quantification."""

    BASE = "base"
    CONSERVATIVE = "conservative"
    EXPECTED = "expected"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class AssumptionType(str, PyEnum):
    """Classification of an input to a value model."""

    FACT = "fact"
    ASSUMPTION = "assumption"
    BENCHMARK = "benchmark"


class ImpactLevel(str, PyEnum):
    """Impact of an assumption on the overall claim."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, PyEnum):
    """Approval state for assumptions, formulas, and benchmarks."""

    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EvidenceType(str, PyEnum):
    """Source category for an evidence link."""

    CALL_TRANSCRIPT = "call_transcript"
    WEB_SIGNAL = "web_signal"
    CRM_NOTE = "crm_note"
    BENCHMARK = "benchmark"
    CUSTOMER_DATA = "customer_data"
    DOCUMENT = "document"
    OBSERVED_BEHAVIOR = "observed_behavior"
    CASE_STUDY = "case_study"
    STAKEHOLDER_QUOTE = "stakeholder_quote"
