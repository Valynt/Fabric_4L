from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ============================================================================
# Shared primitives
# ============================================================================


class AuditMeta(BaseModel):
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    created_by: Literal["agent", "user", "system"] = "system"
    review_state: Literal[
        "draft", "needs_review", "approved", "modified", "rejected", "published"
    ] = "draft"
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    source: str = "system"


# ============================================================================
# Tenant & User
# ============================================================================


class Tenant(BaseModel):
    id: str
    name: str
    default_value_pack_id: str | None = None
    plan: Literal["free", "team", "enterprise"] = "team"
    status: Literal["active", "suspended", "trial"] = "active"


class User(BaseModel):
    id: str
    tenant_id: str
    email: str
    name: str
    role: Literal["tenant_admin", "content_admin", "analyst", "read_only"] = "analyst"
    password_hash: str | None = None
    status: Literal["invited", "active", "deactivated"] = "active"
    invited_by: str | None = None
    # Brute-force protection fields (F-05)
    failed_login_attempts: int = 0
    locked_until: str | None = None  # ISO-8601 UTC timestamp


# ============================================================================
# Account & Stakeholder
# ============================================================================


class Account(BaseModel):
    id: str
    tenant_id: str
    name: str
    industry: str
    segment: str | None = None
    website: str | None = None
    annual_revenue: float | None = None
    employee_count: int | None = None
    crm_stage: str | None = None
    value_pack_id: str | None = None
    summary: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class Stakeholder(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    name: str
    title: str
    persona_id: str | None = None
    department: str | None = None
    priorities: list[str] = Field(default_factory=list)
    pains: list[str] = Field(default_factory=list)
    influence_level: Literal["low", "medium", "high"] = "medium"
    decision_role: Literal["economic", "technical", "user", "champion", "none"] = "none"


# ============================================================================
# Value Pack
# ============================================================================


class ValuePack(BaseModel):
    id: str
    name: str
    industry: str
    description: str | None = None
    status: Literal["draft", "published", "deprecated"] = "published"
    version: str = "1.0.0"
    formula_count: int = 0
    variable_count: int = 0
    entity_count: int = 0
    tags: list[str] = Field(default_factory=list)
    path: str | None = None


# ============================================================================
# Signal & Evidence
# ============================================================================


class Signal(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    source_document_id: str | None = None
    signal_type: Literal["pain", "opportunity", "risk", "trend"] = "pain"
    title: str
    description: str | None = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    extracted_text: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    mapped_driver_ids: list[str] = Field(default_factory=list)
    status: Literal["new", "reviewed", "approved", "rejected"] = "new"
    audit: AuditMeta = Field(default_factory=AuditMeta)


class Evidence(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    source_document_id: str | None = None
    title: str
    excerpt: str | None = None
    source_type: Literal[
        "crm", "call_transcript", "pdf", "web", "case_study", "product_doc", "spreadsheet", "api"
    ] = "web"
    url: str | None = None
    page: int | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    tags: list[str] = Field(default_factory=list)
    supports_claim_ids: list[str] = Field(default_factory=list)
    audit: AuditMeta = Field(default_factory=AuditMeta)


# ============================================================================
# Hypothesis & Driver Tree
# ============================================================================


class ValueHypothesis(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    title: str
    persona_id: str | None = None
    driver_ids: list[str] = Field(default_factory=list)
    pain_signal_ids: list[str] = Field(default_factory=list)
    claim: str | None = None
    expected_outcome: str | None = None
    discovery_questions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    status: Literal["generated", "approved", "modified", "skipped", "rejected"] = "generated"
    audit: AuditMeta = Field(default_factory=AuditMeta)


class ValueLever(BaseModel):
    id: str
    driver_id: str
    name: str
    description: str | None = None
    formula_id: str | None = None
    baseline_metric: float | None = None
    target_metric: float | None = None
    unit: str | None = None
    assumption_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)


class ValueDriver(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    name: str
    category: Literal["revenue_uplift", "cost_savings", "risk_reduction"] = "revenue_uplift"
    description: str | None = None
    linked_signals: list[str] = Field(default_factory=list)
    linked_evidence: list[str] = Field(default_factory=list)
    levers: list[ValueLever] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    audit: AuditMeta = Field(default_factory=AuditMeta)


# ============================================================================
# Formula & Scenario
# ============================================================================


class FormulaInput(BaseModel):
    name: str
    display_name: str
    type: Literal["currency", "integer", "float", "percent", "string"] = "float"
    unit: str | None = None
    default_value: float | None = None
    valid_range: dict[str, float] | None = None
    description: str | None = None


class FormulaOutput(BaseModel):
    name: str
    unit: str | None = None
    description: str | None = None


class Formula(BaseModel):
    id: str
    value_pack_id: str | None = None
    name: str
    category: Literal["revenue_uplift", "cost_savings", "risk_reduction", "productivity"] = (
        "revenue_uplift"
    )
    expression: str
    inputs: list[FormulaInput] = Field(default_factory=list)
    outputs: list[FormulaOutput] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    benchmark_ids: list[str] = Field(default_factory=list)
    validation_status: Literal["draft", "validated", "approved", "deprecated"] = "draft"
    version: str = "1.0.0"
    audit: AuditMeta = Field(default_factory=AuditMeta)


class Scenario(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    name: Literal["conservative", "expected", "optimistic", "custom"] = "expected"
    assumptions: dict[str, Any] = Field(default_factory=dict)
    roi_summary: dict[str, Any] | None = None
    payback_months: float | None = None
    npv: float | None = None
    irr: float | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)


# ============================================================================
# ROI & Business Case
# ============================================================================




class DSARRequestCreate(BaseModel):
    subject_identity: dict[str, str]
    scope: list[str] = Field(default_factory=list)
    legal_basis: Literal["gdpr_art_15", "ccpa_1798_110", "other"] = "gdpr_art_15"
    requester_channel: Literal["portal", "email", "api", "support"] = "portal"
    tenant_context: dict[str, str] = Field(default_factory=dict)


class DSARRequestRecord(BaseModel):
    id: str
    tenant_id: str
    requester_user_id: str
    subject_identity: dict[str, str]
    scope: list[str] = Field(default_factory=list)
    legal_basis: str
    requester_channel: str
    tenant_context: dict[str, str] = Field(default_factory=dict)
    data_categories: list[str] = Field(default_factory=list)
    redaction_status: Literal["pending", "applied", "not_required"] = "pending"
    completion_evidence: list[str] = Field(default_factory=list)
    status: Literal["registered", "exporting", "reconciling", "complete", "escalated"] = "registered"
    requested_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    sla_deadline_at: str
    completed_at: str | None = None
    escalated_at: str | None = None
    package_id: str | None = None


class DSARPackage(BaseModel):
    id: str
    dsar_request_id: str
    tenant_id: str
    requester_user_id: str
    export_payload: dict[str, Any] = Field(default_factory=dict)
    completeness_verified: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str


class ROICalculation(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    scenario_id: str
    revenue_uplift: float = 0.0
    cost_savings: float = 0.0
    risk_reduction: float = 0.0
    total_benefit: float = 0.0
    solution_cost: float = 0.0
    net_benefit: float = 0.0
    roi_percent: float = 0.0
    payback_months: float = 0.0
    calculation_trace: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    assumption_ids: list[str] = Field(default_factory=list)
    audit: AuditMeta = Field(default_factory=AuditMeta)


class BusinessCase(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    title: str
    executive_summary: str | None = None
    value_narrative: str | None = None
    roi_calculation_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    status: Literal["draft", "review", "approved", "published", "archived"] = "draft"
    audit: AuditMeta = Field(default_factory=AuditMeta)


# ============================================================================
# Ground Truth & Governance
# ============================================================================


class GroundTruthObject(BaseModel):
    id: str
    tenant_id: str
    object_type: str
    object_id: str
    claim: str
    validated_by: str | None = None
    validation_status: Literal["pending", "verified", "disputed", "deprecated"] = "pending"
    evidence_ids: list[str] = Field(default_factory=list)
    review_decision_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ReviewDecision(BaseModel):
    id: str
    tenant_id: str
    object_type: str
    object_id: str
    decision: Literal["approve", "reject", "modify", "escalate"] = "approve"
    reason: str | None = None
    reviewer_id: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class AuditLogEvent(BaseModel):
    id: str
    tenant_id: str
    actor_type: Literal["user", "agent", "system"] = "system"
    actor_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    payload: dict[str, Any] | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class GovernanceGate(BaseModel):
    id: str
    tenant_id: str
    name: str
    category: Literal[
        "architecture",
        "security",
        "tenant_isolation",
        "contract_drift",
        "observability",
        "agent_safety",
        "smoke_tests",
        "data_provenance",
        "human_review",
    ] = "security"
    status: Literal["pending", "passed", "failed", "waived"] = "pending"
    evidence: str | None = None
    checked_at: str | None = None


class ReviewComment(BaseModel):
    id: str
    review_id: str
    tenant_id: str
    author_id: str
    text: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ReviewRequest(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    requester_id: str
    reviewer_id: str | None = None
    status: Literal["pending", "approved", "rejected", "changes_requested"] = "pending"
    scope: Literal["value_model", "business_case", "formula", "evidence"] = "business_case"
    target_id: str | None = None
    comments: list[ReviewComment] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    resolved_at: str | None = None


class AccountVersionSnapshot(BaseModel):
    id: str
    account_id: str
    tenant_id: str
    created_by: str
    snapshot_type: Literal["auto", "manual"] = "manual"
    signals: list[Signal] = Field(default_factory=list)
    drivers: list[ValueDriver] = Field(default_factory=list)
    roi_calculations: list[ROICalculation] = Field(default_factory=list)
    business_case_ids: list[str] = Field(default_factory=list)
    label: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# ============================================================================
# Agents
# ============================================================================


class ToolResult(BaseModel):
    id: str
    agent_run_id: str
    tool_name: str
    status: Literal["success", "error", "partial", "skipped"] = "success"
    output: dict[str, Any] | None = None
    error: str | None = None
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None


class AgentRun(BaseModel):
    id: str
    tenant_id: str
    account_id: str | None = None
    workflow_type: str
    status: Literal["pending", "running", "paused", "completed", "failed", "cancelled"] = "pending"
    current_step: str | None = None
    checkpoint_id: str | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    tool_results: list[ToolResult] = Field(default_factory=list)
    review_required: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
