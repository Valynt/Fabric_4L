"""Pydantic models for the Tool Manifest Registry.

These models MIRROR the canonical JSON Schema defined in
:file:`contracts/tool-manifests/tool-manifest.schema.json` and
:file:`contracts/tool-manifests/registry.schema.json`. The JSON Schemas are
the source of truth; any field-name drift here would violate the platform
contract-first rule, so field names and structure must match the schemas
exactly (including ``tenant_binding.client_supplied_tenant_authoritative``,
``resource_resolver`` as an object, ``approval_requirement``,
``data_controls.allowed``/``prohibited``, and ``runtime.timeout_ms``).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RegistryModel(BaseModel):
    """Base model mirroring the JSON Schemas' ``additionalProperties: false``.

    Every model in this module must reject undeclared fields so the runtime
    Pydantic layer cannot drift from the canonical JSON Schema envelopes.
    """

    model_config = ConfigDict(extra="forbid")


class SideEffectClass(str, Enum):
    """Side-effect classification for every tool manifest."""

    READ_ONLY = "READ_ONLY"
    CALCULATION_ONLY = "CALCULATION_ONLY"
    DRAFT_ONLY = "DRAFT_ONLY"
    REVERSIBLE_MUTATION = "REVERSIBLE_MUTATION"
    PROTECTED_MUTATION = "PROTECTED_MUTATION"
    IRREVERSIBLE = "IRREVERSIBLE"


class ManifestStatus(str, Enum):
    """Lifecycle status of a tool manifest."""

    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    EXPERIMENTAL = "EXPERIMENTAL"
    DISABLED = "DISABLED"


class PrincipalType(str, Enum):
    """Principal types permitted to discover a tool."""

    AGENT = "agent"
    USER = "user"
    SERVICE = "service"
    MCP_CLIENT = "mcp_client"


class ResourceResolver(RegistryModel):
    """Reviewed server-side resolver that owns resource resolution."""

    name: str = Field(..., min_length=1, description="Name of the reviewed server-side resolver")
    authoritative_service: str = Field(..., min_length=1, description="Service that owns the resolver")


class TenantBinding(RegistryModel):
    """Tenant isolation binding for the tool."""

    client_supplied_tenant_authoritative: bool = Field(
        ...,
        description="If false, the tenant must be resolved server-side; caller-selected tenant IDs are rejected.",
    )
    resolve_server_side: bool = Field(..., description="If true, the implementing service resolves tenant and billing account.")


class Implementation(RegistryModel):
    """Where and how the tool is wired to the platform runtime."""

    service: str = Field(..., min_length=1, description="Canonical service name (e.g., services/layer7-billing)")
    operation_id: str = Field(..., min_length=1, description="OpenAPI operationId or handler name in the implementing service")
    route: str | None = Field(None, description="Optional HTTP route for runtime routing verification")


class ApprovalRequirement(RegistryModel):
    """Approval requirements for side-effecting tools."""

    required: bool | None = Field(None, description="Whether pre-execution approval is required")
    separation_of_duty: bool | None = Field(None, description="Whether separation of duty is required")
    approver_principal_types: list[str] | None = Field(
        None,
        description="Principal types that may approve (user, admin, service)",
    )


class AuditRequirement(RegistryModel):
    """Audit logging obligations for the tool."""

    required: bool = Field(..., description="Whether audit logging is required")
    action: str = Field(..., min_length=1, description="Canonical audit action name")
    include_authorization_decision_id: bool | None = Field(None, description="Record the authz decision id")
    include_correlation_id: bool | None = Field(None, description="Record the correlation id")
    include_causation_id: bool | None = Field(None, description="Record the causation id")
    evidence_requirements: list[str] | None = Field(None, description="Evidence captured in the audit record")


class DataControls(RegistryModel):
    """Data access and redaction controls."""

    allowed: list[str] | None = Field(None, description="Data fields the tool may return or process")
    prohibited: list[str] | None = Field(None, description="Data fields the tool must never return or process")
    prompt_visible_fields: list[str] | None = Field(None, description="Fields that may be exposed in agent prompts")
    redaction_policy: str | None = Field(None, description="Name of the redaction policy to apply")


class Idempotency(RegistryModel):
    """Idempotency controls for side-effecting tools."""

    required: bool | None = Field(None, description="Whether an idempotency key is required")
    key_input_fields: list[str] | None = Field(None, description="Input fields that form the idempotency key")


class Revision(RegistryModel):
    """Optimistic concurrency controls."""

    etag_required: bool | None = Field(None, description="Whether an ETag is required")
    optimistic_locking: bool | None = Field(None, description="Whether optimistic locking is applied")


class Runtime(RegistryModel):
    """Runtime limits and retry semantics."""

    timeout_ms: int = Field(..., ge=100, description="Hard timeout in milliseconds")
    retry_policy: str | None = Field(None, description="Retry semantics")
    rate_limit_class: str | None = Field(None, description="Rate-limit bucket identifier")


class Deprecation(RegistryModel):
    """Deprecation metadata for the tool."""

    replacement_tool_id: str | None = Field(None, description="Tool ID to migrate to")
    sunset_date: str | None = Field(None, description="ISO 8601 sunset date")
    migration_guide_url: str | None = Field(None, description="URL to migration guide")


class ManifestTests(RegistryModel):
    """Required test coverage metadata."""

    required_coverage: str | None = Field(None, description="Required coverage level")
    test_suite_path: str | None = Field(None, description="Path to the test suite")


class ToolManifest(RegistryModel):
    """Single tool manifest — the authoritative governance envelope.

    Field names and structure mirror :file:`contracts/tool-manifests/tool-manifest.schema.json`.
    """

    tool_id: str = Field(..., min_length=1, description="Stable, fully-qualified tool identifier (e.g., billing.invoice.explain)")
    version: str = Field(..., pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", description="SemVer of this manifest")
    status: ManifestStatus = Field(..., description="Lifecycle status")
    owner: str = Field(..., min_length=1, description="Owning team or domain (e.g., agents/billing-experience)")
    description: str = Field(..., min_length=1, description="Human-readable purpose")
    implementation: Implementation = Field(..., description="Runtime wiring")
    action_id: str = Field(..., min_length=1, description="Canonical action identifier from the command/permission catalog")
    principal_types: list[PrincipalType] = Field(..., min_length=1, description="Principal types permitted to discover this tool")
    input_schema_ref: str = Field(..., min_length=1, description="Resolvable reference to the input JSON Schema")
    output_schema_ref: str = Field(..., min_length=1, description="Resolvable reference to the output JSON Schema")
    resource_resolver: ResourceResolver | None = Field(None, description="Reviewed server-side resolver")
    tenant_binding: TenantBinding | None = Field(None, description="Tenant isolation binding")
    side_effect: SideEffectClass = Field(..., description="Side-effect classification")
    financial_state_change: bool | None = Field(None, description="Whether the tool can mutate financial state")
    human_confirmation_required: bool | None = Field(None, description="Whether human confirmation is required before execution")
    approval_requirement: ApprovalRequirement | None = Field(None, description="Approval requirements")
    data_controls: DataControls | None = Field(None, description="Data access controls")
    idempotency: Idempotency | None = Field(None, description="Idempotency controls")
    revision: Revision | None = Field(None, description="Optimistic concurrency controls")
    audit: AuditRequirement = Field(..., description="Audit logging obligations")
    runtime: Runtime = Field(..., description="Runtime limits")
    supported_agent_classes: list[str] | None = Field(None, description="Agent classes that may discover this tool")
    feature_flag: str | None = Field(None, description="Feature flag or emergency disable control")
    deprecation: Deprecation | None = Field(None, description="Deprecation metadata")
    tests: ManifestTests | None = Field(None, description="Test coverage metadata")
    provenance: dict[str, Any] | None = Field(None, description="Provenance metadata")


class RegistryValidationReport(RegistryModel):
    """Summary of the validation run that produced an index."""

    passed: bool = True
    violations: int = 0
    manifests_loaded: int = 0
    manifests_valid: int = 0


class ToolManifestSummary(RegistryModel):
    """Lightweight entry in the compiled registry index."""

    tool_id: str
    version: str
    status: str
    side_effect: str
    action_id: str
    principal_types: list[str]
    human_confirmation_required: bool | None = None
    financial_state_change: bool | None = None
    supported_agent_classes: list[str] | None = None
    tenant_binding: TenantBinding | None = None
    source_path: str | None = None


class AgentPolicy(RegistryModel):
    """Agent-type filter policy keyed by agent class name."""

    allowed_side_effects: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    denied_tools: list[str] = Field(default_factory=list)
    denied_side_effects: list[str] = Field(default_factory=list)
    require_human_confirmation_for_financial_tools: bool = False
    description: str | None = None


class ToolRegistryIndex(RegistryModel):
    """Compiled registry index consumed by Layer 4 at startup.

    Mirrors :file:`contracts/tool-manifests/registry.schema.json`.
    """

    registry_version: str = Field(..., pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", description="SemVer of the registry index itself")
    generated_at: str = Field(..., description="ISO 8601 timestamp when the index was generated")
    snapshot_sha: str = Field(..., description="Content-addressable snapshot identifier pinning the exact manifest set")
    tool_manifests: list[ToolManifestSummary] = Field(default_factory=list)
    policies: dict[str, AgentPolicy] = Field(default_factory=dict)
    agent_class_bindings: dict[str, str] = Field(default_factory=dict)
    validation_report: RegistryValidationReport | None = None
