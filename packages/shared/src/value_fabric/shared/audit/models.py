"""Audit event model and action enum.

Audit records are append-only — no UPDATE or DELETE operations are ever
issued against the audit_events table (enforced at the DB level via a
trigger in production; enforced in application code by design).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AuditAction(str, Enum):
    """Canonical set of auditable actions across all layers."""

    # ── Identity / auth ────────────────────────────────────────────────────
    USER_INVITED = "user.invited"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"
    USER_LOGIN = "user.login"
    USER_LOGIN_FAILED = "user.login_failed"

    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    API_KEY_USED = "api_key.used"

    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"
    TENANT_SUSPENDED = "tenant.suspended"
    TENANT_DELETED = "tenant.deleted"

    # ── Data lifecycle ──────────────────────────────────────────────────────
    DOCUMENT_INGESTED = "document.ingested"
    EXTRACTION_RUN = "extraction.run"
    EXTRACTION_QUARANTINED = "extraction.quarantined"
    KG_NODE_CREATED = "kg.node_created"
    KG_NODE_UPDATED = "kg.node_updated"
    KG_NODE_DELETED = "kg.node_deleted"

    # ── OIDC ────────────────────────────────────────────────────────────────
    OIDC_LOGIN = "oidc.login"
    OIDC_LOGIN_FAILED = "oidc.login_failed"

    # ── Model registry ──────────────────────────────────────────────────────
    MODEL_REGISTERED = "model.registered"
    MODEL_PROMOTED = "model.promoted"
    MODEL_DEPRECATED = "model.deprecated"
    MODEL_EVALUATED = "model.evaluated"

    # ── Feature flags ───────────────────────────────────────────────────────
    FEATURE_FLAG_CREATED = "feature_flag.created"
    FEATURE_FLAG_UPDATED = "feature_flag.updated"
    FEATURE_FLAG_DELETED = "feature_flag.deleted"

    # ── Agent / workflow ────────────────────────────────────────────────────
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_CANCELLED = "workflow.cancelled"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"
    CHECKPOINT_RESUMED = "checkpoint.resumed"
    BUSINESS_CASE_GENERATED = "business_case.generated"
    BUSINESS_CASE_UPDATED = "business_case.updated"
    BUSINESS_CASE_APPROVED = "business_case.approved"
    ROI_CALCULATED = "roi.calculated"
    BENCHMARK_COMPARED = "benchmark.compared"
    BENCHMARK_VALIDATED = "benchmark.validated"
    EXPORT_REQUESTED = "export.requested"
    EXPORT_PACKAGE_GENERATED = "export.package_generated"
    EXPORT_DOWNLOAD_ACCESSED = "export.download_accessed"

    # ── Integrations ─────────────────────────────────────────────────────────
    WEBHOOK_RECEIVED = "webhook.received"
    WEBHOOK_PROCESSING_FAILED = "webhook.processing_failed"

    # ── Billing ──────────────────────────────────────────────────────────────
    BILLING_SUBSCRIPTION_CREATED = "billing.subscription.created"
    BILLING_SUBSCRIPTION_UPDATED = "billing.subscription.updated"
    BILLING_SUBSCRIPTION_CANCELED = "billing.subscription.canceled"
    BILLING_SUBSCRIPTION_REACTIVATED = "billing.subscription.reactivated"
    BILLING_PLAN_CHANGED = "billing.plan.changed"
    BILLING_CHECKOUT_INITIATED = "billing.checkout.initiated"
    BILLING_PORTAL_OPENED = "billing.portal.opened"
    BILLING_INVOICE_CREATED = "billing.invoice.created"
    BILLING_INVOICE_UPDATED = "billing.invoice.updated"
    BILLING_INVOICE_FINALIZED = "billing.invoice.finalized"
    BILLING_INVOICE_VOIDED = "billing.invoice.voided"
    BILLING_CHARGE_RECORDED = "billing.charge.recorded"
    BILLING_USAGE_INGESTED = "billing.usage.ingested"
    BILLING_CUSTOMER_SYNCED = "billing.customer.synced"
    BILLING_WEBHOOK_RECEIVED = "billing.webhook.received"

    # ── Ground Truth ────────────────────────────────────────────────────────
    TRUTH_CREATED = "truth.created"
    TRUTH_VALIDATED = "truth.validated"
    TRUTH_DELETED = "truth.deleted"
    TRUTH_SYNCED = "truth.synced"

    # ── Ingestion / compliance ───────────────────────────────────────────────
    URL_SAFETY_BLOCKED = "url.safety_blocked"
    URL_ROBOTS_BLOCKED = "url.robots_blocked"
    OUTBOX_DEAD_LETTERED = "outbox.dead_lettered"

    # ── Merged from root shared/audit/models.py ──────────────────────────────
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_FAIL = "workflow_fail"
    TENANT_RESOLVED = "tenant_resolved"
    TENANT_CONTEXT_SET = "tenant_context_set"
    API_CALL = "api_call"
    LLM_USAGE = "llm_usage"
    AGENT_EXECUTION = "agent_execution"
    CROSS_TENANT_ACCESS = "cross_tenant_access"
    TENANT_PROVISIONED = "tenant_provisioned"
    TENANT_PROVISIONING_FAILED = "tenant_provisioning_failed"
    TENANT_PROVISIONING_STEP_COMPLETE = "tenant_provisioning_step_complete"
    TENANT_PROVISIONING_ROLLBACK = "tenant_provisioning_rollback"
    TENANT_PROVISIONED_WEBHOOK = "tenant_provisioned_webhook"
    TENANT_STATUS_CHANGED = "tenant_status_changed"
    INFISICAL_PATH_CREATED = "infisical_path_created"
    INFISICAL_SECRET_SEEDED = "infisical_secret_seeded"
    TOOL_INVOCATION = "tool_invocation"
    POLICY_DECISION = "policy_decision"
    LEDGER_COMMIT = "ledger_commit"
    MEMORY_ACCESS = "memory_access"
    REPLAY_SNAPSHOT = "replay_snapshot"


class AuditOutcome(str, Enum):
    """Outcome of the audited action."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    DENIED = "denied"


class AuditEvent(BaseModel):
    """Immutable audit record.

    Fields mirror the ``audit_events`` DB table column-for-column so that
    the emitter can serialize directly to SQL without any transformation.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique event ID")
    tenant_id: Optional[UUID] = Field(None, description="Owning tenant (None for platform actions)")
    user_id: Optional[str] = Field(None, description="Acting user")
    api_key_id: Optional[str] = Field(None, description="API key used, if any")
    action: AuditAction
    resource_type: Optional[str] = Field(None, description="e.g. 'Tenant', 'User', 'Workflow'")
    resource_id: Optional[str] = Field(None, description="Primary key of the affected resource")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    outcome: AuditOutcome = AuditOutcome.SUCCESS
    details: Dict[str, Any] = Field(default_factory=dict, description="Action-specific metadata")
    chain_id: Optional[str] = Field(None, description="Hash-chain identifier for audit ledger")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __await__(self):
        """Allow async governance code to ``await`` an already-emitted audit event.

        The shared emitter is intentionally synchronous for low-latency logging and
        backward compatibility with existing service code. Several governance
        wrappers are async and historically awaited the helper, so returning an
        awaitable model preserves both call styles without duplicating emitters
        across layers.
        """

        async def _return_self() -> "AuditEvent":
            return self

        return _return_self().__await__()

    model_config = ConfigDict(use_enum_values=True)

# Merged from root audit/models.py
class TenantResolvedDetails(BaseModel):
    """Structured details for TENANT_RESOLVED audit events (Task 3.1).

    Provides a standardized schema for tenant resolution events without
    fragmenting the audit model into separate types.
    """

    resolution_source: str = Field(
        ...,
        description="How tenant was resolved: jwt_claim | api_key | service_account | unknown"
    )
    resolved_tenant_id: str | None = Field(
        None,
        description="Final tenant_id that was resolved"
    )
    requested_tenant_id: str | None = Field(
        None,
        description="Tenant_id that was originally requested (if different)"
    )
    user_id: str | None = Field(
        None,
        description="User ID if JWT authentication"
    )
    api_key_id: str | None = Field(
        None,
        description="API key ID if API key authentication"
    )
    service_account_id: str | None = Field(
        None,
        description="Service account ID if service account authentication"
    )
    auth_method: str = Field(
        ...,
        description="Authentication method: jwt | api_key | service_account | none"
    )
    has_org_id: bool = Field(
        default=False,
        description="Whether org_id was present in claims"
    )
    org_id: str | None = Field(
        None,
        description="Organization ID if present in claims"
    )
    tenant_role: str | None = Field(
        None,
        description="User's role within tenant context"
    )
    isolation_tier: str = Field(
        default="shared",
        description="Tenant isolation tier: shared | schema | database"
    )
    roles: list[str] = Field(
        default_factory=list,
        description="Roles assigned to the actor"
    )
    is_super_admin: bool = Field(
        default=False,
        description="Whether actor has super admin privileges"
    )
    bypass: bool = Field(
        default=False,
        description="Whether tenant context was bypassed (privileged access)"
    )
    bypass_reason: str | None = Field(
        None,
        description="Reason for bypass if applicable"
    )
    outcome: str = Field(
        default="success",
        description="Resolution outcome: success | failure | denied"
    )
    failure_reason: str | None = Field(
        None,
        description="Reason for failure if outcome is not success"
    )
    request_path: str | None = Field(
        None,
        description="API path being accessed"
    )
    request_method: str | None = Field(
        None,
        description="HTTP method of the request"
    )

    model_config = ConfigDict(from_attributes=True)

class TenantContextSetDetails(BaseModel):
    """Structured details for TENANT_CONTEXT_SET audit events (Task 3.1).

    Emitted when database session is configured with RLS tenant context.
    """

    tenant_id: str | None = Field(
        None,
        description="Tenant ID set for RLS context (empty string for bypass)"
    )
    isolation_tier: str = Field(
        default="shared",
        description="Isolation tier from request context"
    )
    bypass: bool = Field(
        default=False,
        description="Whether this is a super-admin bypass"
    )
    bypass_reason: str | None = Field(
        None,
        description="Reason for bypass if applicable"
    )
    context_source: str = Field(
        default="request_context",
        description="Source of tenant context: request_context | explicit_param | job_queue"
    )

class ToolInvocationRecord(BaseModel):
    """Structured details for TOOL_INVOCATION audit events (GATE Phase 1)."""

    tool_name: str
    tool_version: str | None = None
    tool_manifest_hash: str | None = None
    request_hash: str
    response_hash: str | None = None
    policy_decision: str | None = None  # "allowed" | "denied" | "invariant_blocked"
    invariant_checks: list[str] = Field(default_factory=list)
    execution_time_ms: int | None = None
    tenant_id: str | None = None
    actor_id: str | None = None
    trace_id: str | None = None

class LedgerCommitDetails(BaseModel):
    """Details for ledger commit events linking to previous state (GATE Phase 1)."""

    chain_head_hash: str | None = None
    commit_type: str  # "tool_invocation" | "policy_decision" | "agent_execution"
    bundle_hash: str | None = None  # Hash of policy/invariant bundle evaluated

class PolicyDecisionRecord(BaseModel):
    """Structured details for POLICY_DECISION audit events (GATE Phase 2)."""

    decision: bool
    reason: str | None = None
    obligations: list[str] = Field(default_factory=list)
    policy_bundle_hash: str | None = None

class MemoryAccessRecord(BaseModel):
    """Structured details for MEMORY_ACCESS audit events (GATE Phase 3)."""

    query: str
    tenant_id: str
    agent_id: str | None = None
    content_hash: str
    source_lineage: list[dict[str, Any]] = Field(default_factory=list)
    entity_count: int = 0
    relationship_count: int = 0
    trace_id: str | None = None

class ReplaySnapshotRecord(BaseModel):
    """Structured details for REPLAY_SNAPSHOT audit events (GATE Phase 3)."""

    agent_id: str
    agent_type: str | None = None
    manifest_hash: str | None = None
    snapshot_hash: str
    tool_invocation_count: int = 0
    memory_access_count: int = 0
    tenant_id: str | None = None
    trace_id: str | None = None

class PrivilegedAccessDetails(BaseModel):
    """Structured details for CROSS_TENANT_ACCESS audit events (Task 2).
    
    Captures comprehensive information about super-admin bypass operations
    for compliance and security monitoring.
    
    Example usage:
        details = PrivilegedAccessDetails(
            accessed_tenant_ids=["tenant-a", "tenant-b"],
            resource_types=["Entity", "Relationship"],
            session_duration_seconds=45,
            reason="Emergency data recovery for customer incident #12345",
            approval_ticket="JIRA-SEC-9876"
        )
        
        await emit_audit_event(
            action=AuditAction.CROSS_TENANT_ACCESS,
            outcome=AuditOutcome.SUCCESS,
            actor_id=admin_user_id,
            details=details.model_dump()
        )
    """
    
    accessed_tenant_ids: list[str] = Field(
        default_factory=list,
        description="List of tenant IDs accessed during privileged session"
    )
    resource_types: list[str] = Field(
        default_factory=list,
        description="Types of resources accessed (Entity, Relationship, etc.)"
    )
    session_duration_seconds: int = Field(
        default=0,
        description="Duration of privileged session in seconds"
    )
    reason: str = Field(
        ...,
        description="Justification for cross-tenant access (from X-Privileged-Reason header)"
    )
    approval_ticket: str | None = Field(
        None,
        description="Optional approval ticket/incident number"
    )
    query_count: int = Field(
        default=0,
        description="Number of cross-tenant queries executed"
    )
    data_exported: bool = Field(
        default=False,
        description="Whether data was exported/downloaded"
    )
