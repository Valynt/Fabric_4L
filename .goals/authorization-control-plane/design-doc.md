Fabric_4L Enterprise Authorization Implementation Design

Document status: Proposed target architecture and delivery plan
Repository basis: Valynt/Fabric_4L, inspected against main on 2026-08-29
Primary scope: Fine-grained authorization for human users, services, external viewers, agents, tools, workflows, and governed value-model operations
Decision class: Security architecture, domain governance, platform architecture

1. Executive decision

Fabric_4L should implement a hybrid authorization model with four cooperating concerns:

Constrained RBAC defines the classes of work a principal may perform.

ReBAC limits that authority to resources to which the principal has a governed relationship.

ABAC evaluates request-time facts such as authorship, approval ceilings, claim state, model version, exception state, publication state, risk, and time.

PBAC is the decision and enforcement plane that evaluates those inputs consistently at every protected boundary.

PBAC is not a fourth entitlement store and must not become a parallel permissions model. It is the common policy decision mechanism through which RBAC, ReBAC, ABAC, separation of duties, state-machine rules, and explicit deny rules are evaluated.

The target design uses:

Clerk as the human identity provider and authentication source.

Fabric-owned principal, membership, workflow-role, relationship, delegation, and exception records as authorization facts.

Open Policy Agent (OPA) and Rego as the single policy decision point and policy-as-code runtime.

A Fabric authorization facade as the stable application interface, preventing application code from depending directly on OPA internals.

PostgreSQL row-level security as tenant containment and defense in depth, not as the complete workflow authorization system.

Explicit policy enforcement points in the API, command handlers, MCP tools, workers, service-to-service calls, external sharing gateway, and administrative flows.

Default deny for all actions not present in the permission catalog.

Fail closed for protected writes and sensitive reads when a decision cannot be obtained.

A separate domain audit trail and verification ledger, both correlated to the authorization decision identifier.

The first enforcement milestone is deliberately narrow: protect claim.approve, deliverable.publish_external, exception.activate, and opportunity.lock_realization. These verbs carry the greatest financial, customer, and governance risk and establish the reusable architecture without forcing a big-bang rewrite.

2. Starting principles from the supplied authorization model

The supplied model establishes the following non-negotiable product and security semantics:

Fabric cannot be RBAC-only. Roles identify the job, while approval, publication, and exceptions depend on role plus resource plus relationship plus current attributes.

Lenses are presentation contexts, not roles. Viewing a CFO lens does not make a principal a finance approver.

Humans, agents, external viewers, and system control runners are different principal types.

A typed name is never an approver identity. Approval requires an authenticated and eligible principal.

validate and approve are distinct permissions and distinct domain events.

A request to activate an exception must be separate from submitting or approving the exception.

Agents may propose but must not approve, validate, publish, activate exceptions, mark a model canonical, lock realization, or resolve disputes.

Static and dynamic separation of duties are required.

Permissions are defined as resource type plus action, with field and state constraints where required. They are not screen-level controls.

The API is authoritative. Hidden or disabled UI controls improve usability but do not provide security.

Missing authority returns a uniform authorization denial and must not fall through to an unguarded handler.

Every sensitive transition records the acting principal, target resource, version, policy decision, and resulting state.

These principles are retained throughout this design rather than translated into a generic Admin/User/ReadOnly matrix.

3. Current-state assessment and migration posture

3.1 Existing assets to preserve

Fabric_4L already has important foundations that should be extended rather than replaced:

A canonical Clerk/JWT authentication path.

Internal resolution from Clerk subjects and organizations to Fabric user and tenant identifiers.

Active-membership and tenant-binding checks.

An AuthContext concept carrying user, tenant, roles, permissions, request identity, and envelope metadata.

PostgreSQL tenant context and row-level security patterns.

Shared identity abstractions used by some API routes.

Security, tenant-isolation, architecture, and policy-oriented CI checks.

Separate service layers and agent/tool surfaces where enforcement points can be installed.

Authentication and tenant resolution remain prerequisites to authorization, but they are not themselves sufficient authorization decisions.

3.2 Current risks to eliminate

The migration should assume that authorization logic is presently fragmented until every protected route is proven otherwise. The following patterns must be inventoried and removed or isolated:

Raw role-string checks in routers, services, UI components, or tools.

Multiple role vocabularies with unclear precedence.

Client-supplied role, tenant, approver, or resource-state attributes treated as authoritative.

Coarse read, write, or admin checks applied to financially or operationally sensitive domain operations.

Service API keys that identify an application but do not express workload identity, delegation, or action scope.

UI-only permission checks.

Domain state transitions executed without a policy decision in the same transaction boundary.

Direct database writes that can bypass the domain command and policy enforcement path.

Approval state represented as free text, a boolean, or a mutable field without actor and version provenance.

Reuse of one ledger record for both authorization/audit evidence and control verification.

3.3 Role taxonomy correction

The current Clerk-to-Fabric normalization seam should be retained only for broad platform membership. It must not become the source of all workflow authority.

Fabric should maintain two separate namespaces:

Platform roles: tenant administration and platform access, such as platform.tenant_admin, platform.member, platform.billing_admin, and platform.read_only.

Workflow roles: value-governance responsibilities, such as workflow.value_engineer, workflow.finance_approver, and workflow.realization_owner.

A platform administrator is not automatically a finance approver. A finance approver is not automatically a tenant administrator. The two namespaces may be assigned to the same human only when static separation-of-duty policy permits it.

4. Target authorization architecture

4.1 Logical components

+------------------------- Identity and trust --------------------------+
| Clerk / IdP | Fabric directory | Workload identity | External grants |
+------------------------------+----------------------------------------+
                               |
                               v
+------------------------- Request context -----------------------------+
| Authenticated principal | tenant | delegation | channel | request ID  |
+------------------------------+----------------------------------------+
                               |
                               v
+--------------------- Fabric authorization facade ---------------------+
| Typed action catalog | resource loader | attribute resolver | client  |
+-----------+----------------------+---------------------+---------------+
            |                      |                     |
            v                      v                     v
       Role facts            Relationship facts    Resource/context facts
       Fabric DB             Fabric DB              Domain DB/services
            \______________________|_____________________/
                                   |
                                   v
+------------------------ OPA policy decision point --------------------+
| RBAC + ReBAC + ABAC + SoD + state-machine rules + explicit denies    |
| Output: allow/deny, reasons, obligations, policy version, decision ID |
+----------------------------------+------------------------------------+
                                   |
                                   v
+-------------------------- Enforcement points -------------------------+
| FastAPI | domain commands | MCP tools | workers | service APIs | BFF  |
| external sharing gateway | tenant administration | scheduled controls |
+----------------------------------+------------------------------------+
                                   |
                    +--------------+--------------+
                    v                             v
             Domain transaction             Decision/audit stream
             and RLS boundary               and verification ledger

4.2 Component responsibilities

Policy administration point

The policy administration point is the Git-controlled policy repository under policies/authorization/. It owns:

Rego policies.

The action and resource schema.

Role definitions and constraints.

Policy data that changes through governed deployment rather than application transactions.

Policy tests and decision tables.

Bundle manifest, semantic version, digest, signing metadata, and compatibility range.

It does not own tenant-specific role assignments, opportunity bindings, claims, approval ceilings, exception instances, or grants. Those are transactional authorization facts in Fabric databases.

Policy decision point

OPA is the sole general-purpose policy decision point. It receives a normalized, server-created input document and returns a typed decision. It must not query application databases directly. All required facts are loaded by the Fabric attribute resolver or supplied as trusted policy data.

This choice avoids two equal policy engines whose decisions can diverge. The thin relationship model is evaluated in OPA using relationship facts loaded from PostgreSQL. A dedicated Zanzibar-style relationship service should be introduced only if Fabric later reaches graph-scale sharing requirements that cannot be served reliably by the current model.

Policy information point

The Fabric attribute resolver is the policy information point. It loads and normalizes:

Principal type and status.

Tenant membership revision.

Platform and workflow role assignments.

Approval ceiling and exception capability.

Opportunity and resource bindings.

Resource tenant, author, validator, approver, owner, version, state, risk, and materiality.

Open disputes and included claim status.

Exception scope, state, approver, and expiry.

Delegation scope and expiry.

External grant scope and revocation state.

Request time, channel, model version, and authentication assurance.

The resolver must read authoritative server-side sources. Client payloads may identify a target resource or requested version but cannot assert authorization facts.

Policy enforcement points

Every protected operation has an enforcement point immediately before the protected action:

FastAPI route or application command.

Domain state-machine transition.

MCP tool execution.

Agent tool gateway.

Worker job that performs a user-initiated or autonomous action.

Service-to-service API boundary.

Next.js server action or BFF endpoint.

External deliverable read gateway.

Tenant role and binding administration.

A policy decision made in the browser is advisory only. The server repeats the decision using authoritative facts.

5. Trust boundaries and invariants

5.1 Global invariants

Every resource has exactly one authoritative tenant_id unless explicitly classified as platform-global.

A principal acts within one tenant context per request or job execution.

Tenant equality is necessary but never sufficient for sensitive operations.

All unrecognized actions, resource types, principal types, states, and policy input schema versions are denied.

An agent's effective authority is never greater than either its own capability set or the delegating human's authority.

Approval, publication, exception activation, canonicalization, and realization lock are explicit commands, not generic updates.

Protected commands cannot be completed solely through direct table updates by the normal application role.

Policy facts come from trusted server-side records.

A policy decision is associated with one policy version and one resource authorization revision.

Authorization failures do not reveal whether an out-of-tenant resource exists.

Break-glass access never applies to agent principals.

External viewers never acquire tenant membership or workflow roles through a sharing token.

5.2 Enforcement ordering

The protected command sequence is:

Authenticate the caller.

Resolve the Fabric principal and active tenant membership.

Establish transaction-scoped tenant context for RLS.

Load the target resource and authorization attributes under tenant containment.

Validate the request action and resource type against the catalog.

Evaluate policy using the current membership, policy, and resource revisions.

Verify required obligations and request preconditions.

Execute the explicit domain transition using optimistic concurrency.

Recheck authorization-relevant revisions before commit when the operation is high risk.

Commit the domain event and authorization decision reference atomically through an outbox.

Export decision telemetry and append separate verification evidence asynchronously.

This ordering prevents a policy engine from becoming a substitute for tenant containment and reduces time-of-check/time-of-use exposure.

6. Principal and identity model

6.1 Principal types

Principal type

Authentication

Intended authority

Prohibited authority

human

Clerk/IdP token resolved to Fabric user and membership

Role-, relationship-, and attribute-constrained actions

Anything outside active membership or explicit grants

agent

Workload identity for a named agent plus optional delegation

Read, search, propose, draft, compare, suggest

Validate, approve, publish, activate, mark canonical, lock, resolve disputes

service

Workload identity

Narrow service functions and scheduled processing

Human governance acts unless explicitly modeled as system transitions

external_viewer

Scoped, revocable external access grant

Read one deliverable/version or approved projection

Tenant roles, editing, approval, discovery outside scope

system_control

Workload identity

Write verification outcomes and system transitions explicitly allowed by policy

Human approval, business authorship, exception request or approval

6.2 Workload identity

Each deployed service, worker, operator, MCP server, and agent runtime receives a distinct workload principal. Shared environment-wide API keys are transitional only.

Recommended identifier format:

service:api-gateway
service:layer2-extraction
service:layer3-knowledge
service:layer4-agent-runtime
agent:value-copilot
system:verification-runner
system:exception-expiry-controller

Kubernetes workloads should eventually receive short-lived workload credentials from a workload identity system. The authorization model must not depend on that later migration; the Fabric principal record and action catalog remain stable.

6.3 Delegation and on-behalf-of execution

Agent and service calls initiated for a human must carry both identities:

{
  "actor": "agent:value-copilot",
  "subject": "user:7c2...",
  "delegation_id": "dlg_01...",
  "tenant_id": "tn_01...",
  "scopes": ["claim.propose_edit", "evidence.search"],
  "expires_at": "2026-08-29T19:30:00Z"
}

The decision rule is intersection, not union:

effective_actions =
    agent_capabilities
  INTERSECT delegation_scopes
  INTERSECT human_authority_for_resource
  INTERSECT tenant_and_state_policy

The prompt, conversation, model output, or tool arguments never grant authority. Authorization is evaluated at the tool execution boundary.

6.4 External access grants

An external deliverable link is represented by a server-side grant, not a tenant role. The grant includes:

Random opaque token hash or signed token identifier with server-side revocation record.

Tenant, deliverable, exact version, and approved audience.

Allowed actions, normally deliverable.view_external only.

Issue time, expiry, revocation time, and issuer.

Optional email/domain binding and authentication assurance.

Watermark and disclosure obligations.

Maximum access count or one-time use when required.

Publication and access are separate decisions. A deliverable may have been publishable when created but no longer accessible after revocation, expiry, version supersession, or tenant policy change.

7. Role model

7.1 Workflow roles

Fabric should implement the following small, stable workflow-role set:

Role

Primary authority

Important restrictions

workflow.value_engineer

Edit working model, ingest evidence, open disputes, draft exceptions, request validation

Cannot materially approve own canonical writes

workflow.value_manager

Reassign cases, review VE work, manage queues

Cannot alone activate publication exceptions

workflow.finance_approver

Validate methodology and approve economic inclusion for monetary claims

Cannot approve authored input; amount ceiling applies

workflow.technical_reviewer

Validate implementation, scope, timeline, and technical assumptions

Does not imply financial approval

workflow.deal_desk

Gate commercial consistency and publication eligibility

Must not be primary working-model author for the same opportunity

workflow.security_reviewer

Review compliance path and exception eligibility

Cannot activate an exception they requested

workflow.realization_owner

Lock baseline, map KPIs, accept actuals after won

Cannot rewrite locked pre-sale canonical claims

workflow.tenant_admin

Assign tenant roles and maintain approval policy

Does not imply case editing or business approval

7.2 Role assignment scope

A role assignment includes:

Principal identifier.

Tenant identifier.

Role identifier.

Optional organizational unit, region, product, segment, or portfolio scope.

Effective and expiry times.

Assignment source and approving principal.

Assignment revision.

Static separation-of-duty evaluation result.

Do not mint finance_approver_50k, finance_approver_100k, or workflow-step roles. Approval amount, duration, risk, and product constraints are attributes evaluated by policy.

7.3 Static separation of duties

Static constraints apply when roles or grants are assigned. Initial rules:

Agent and service principals cannot receive any *_approver role.

A tenant administrator cannot exercise case-editor authority in the same privileged admin session.

Finance approval and deal-desk authority on the same opportunity require a second eligible person when policy marks the transaction material.

A principal cannot receive a break-glass grant they requested or approved.

A system-control principal cannot receive business-authoring or approval roles.

The system should support a stricter tenant policy but not a weaker policy than the Fabric baseline for protected actions.

7.4 Dynamic separation of duties

Dynamic rules are evaluated on every relevant command:

Claim author is not the claim approver for the same claim and model version.

Exception requester is not the exception approver or activator.

Publisher is not the sole approver of a claim first included in that deliverable version.

A principal cannot exercise both value-manager acceptance and sole finance approval for a material claim in one approval chain.

A break-glass approver cannot be the beneficiary of the grant.

8. Relationship model

Tenant-wide role assignment is intentionally insufficient for opportunity-sensitive work.

8.1 Opportunity relationships

Each opportunity supports typed bindings:

assigned_value_engineer

value_manager

economic_reviewer

technical_reviewer

deal_desk_owner

security_reviewer

realization_owner

account_team_member

review_pool_member

Each binding contains tenant, opportunity, principal, relation, effective period, source, and revision.

8.2 Relationship evaluation

Examples:

A finance approver may approve a claim only if bound as economic_reviewer, assigned through an eligible review pool, or selected through a logged escalation policy.

A value engineer may edit the opportunity only if assigned or granted temporary coverage.

A technical reviewer may review a dispute only if bound to the opportunity or eligible to pick it up from the queue.

A realization owner relationship is inactive before the configured lifecycle state.

Customer contacts are not tenant principals unless Fabric later introduces authenticated external collaboration seats. A CRM contact must not appear in an internal approver picker.

9. Permission catalog

Permission identifiers are stable, namespaced contracts. UI labels may change without changing authorization semantics.

9.1 Opportunity

opportunity.view

opportunity.assign

opportunity.edit_working

opportunity.change_stage

opportunity.lock_realization

opportunity.archive

9.2 Claim and input

claim.view

claim.edit_working

claim.propose_edit

claim.set_derivation

claim.link_evidence

claim.validate

claim.approve

claim.include_in_case

claim.exclude_from_case

claim.open_dispute

claim.resolve_dispute

Validation writes a validation event and status. Approval writes an approval event with principal, model version, policy version, decision identifier, and approved materiality. Neither is a generic update.

9.3 Model version

model.create_version

model.compare_versions

model.mark_canonical

model.tag_scenario

model.accept_candidate

9.4 Deliverable

deliverable.render_lens

deliverable.share_internal

deliverable.publish_external

deliverable.view_external

deliverable.revoke_link

9.5 Exception

exception.draft

exception.submit

exception.review

exception.approve

exception.reject

exception.activate

exception.revoke

exception.extend

9.6 Evidence

evidence.ingest

evidence.search

evidence.accept

evidence.reject

evidence.reclassify

evidence.link

9.7 Administration and audit

membership.assign_role

membership.revoke_role

relationship.assign

relationship.revoke

policy.view_effective

policy.simulate

audit.read_business

audit.read_security

verification.read

verification.append - system control only

break_glass.request

break_glass.approve

break_glass.revoke

9.8 Field-level obligations

Field-level control should be returned as obligations rather than proliferating field-specific role names. Examples:

Redact customer PII.

Hide source evidence content but expose provenance metadata.

Watermark a provisional deliverable.

Permit update only to candidate fields.

Require step-up authentication before revealing or changing a sensitive field.

Require a reason code and narrative.

Require dual control.

10. Authorization decision contract

10.1 Request schema

{
  "schema_version": "fabric.authz.request.v1",
  "request_id": "req_01...",
  "principal": {
    "id": "user_01...",
    "type": "human",
    "tenant_id": "tenant_01...",
    "status": "active",
    "platform_roles": ["platform.member"],
    "workflow_roles": ["workflow.finance_approver"],
    "membership_revision": 42,
    "approval_ceiling_usd": 500000,
    "authn_assurance": "mfa"
  },
  "delegation": null,
  "action": "claim.approve",
  "resource": {
    "type": "claim",
    "id": "claim_01...",
    "tenant_id": "tenant_01...",
    "authz_revision": 17,
    "attributes": {
      "author_id": "user_02...",
      "validation_state": "REVIEWED",
      "approval_state": "PENDING",
      "model_version": "model_v12",
      "impact_usd": 240000,
      "materiality": "material",
      "opportunity_id": "opp_01...",
      "publication_state": "WORKING",
      "open_dispute_count": 0
    },
    "relationships": ["economic_reviewer"]
  },
  "context": {
    "now": "2026-08-29T18:00:00Z",
    "channel": "api",
    "requested_model_version": "model_v12",
    "trace_id": "tr_01...",
    "ip_risk": "low",
    "break_glass_grant_id": null
  }
}

10.2 Decision schema

{
  "schema_version": "fabric.authz.decision.v1",
  "decision_id": "azd_01...",
  "allow": true,
  "reason_codes": ["ROLE_ELIGIBLE", "BOUND_REVIEWER", "SOD_PASS", "CEILING_PASS"],
  "deny_code": null,
  "policy_version": "authz-1.3.0",
  "bundle_digest": "sha256:...",
  "input_fingerprint": "sha256:...",
  "obligations": [
    {"type": "record_approval_reason"},
    {"type": "append_domain_audit"}
  ],
  "cache_ttl_ms": 0,
  "evaluated_at": "2026-08-29T18:00:00.015Z"
}

10.3 Denial semantics

Externally, protected API denials use a stable 403 response with a correlation identifier. Internally, decisions retain precise reason codes such as:

TENANT_MISMATCH

PRINCIPAL_INACTIVE

ROLE_MISSING

RELATIONSHIP_MISSING

SELF_APPROVAL_FORBIDDEN

APPROVAL_CEILING_EXCEEDED

MODEL_VERSION_STALE

DISPUTE_OPEN

EXCEPTION_NOT_ACTIVATED

EXCEPTION_EXPIRED

AGENT_ACTION_FORBIDDEN

POLICY_INPUT_INVALID

PDP_UNAVAILABLE

RESOURCE_REVISION_CHANGED

User-facing messages must avoid resource-existence disclosure across tenant boundaries.

11. Policy examples

The following Rego examples are illustrative. Production policy should be split into reusable invariants, action modules, and reason generation rather than one monolithic file.

11.1 Global deny rules

package fabric.authz

import rego.v1

default allow := false

known_principal_types := {"human", "agent", "service", "external_viewer", "system_control"}

valid_input if {
  input.schema_version == "fabric.authz.request.v1"
  input.principal.type in known_principal_types
  input.principal.tenant_id == input.resource.tenant_id
}

agent_forbidden_actions := {
  "claim.validate",
  "claim.approve",
  "claim.include_in_case",
  "claim.resolve_dispute",
  "model.mark_canonical",
  "deliverable.publish_external",
  "exception.submit",
  "exception.approve",
  "exception.activate",
  "opportunity.lock_realization"
}

deny_reason contains "AGENT_ACTION_FORBIDDEN" if {
  input.principal.type == "agent"
  input.action in agent_forbidden_actions
}

11.2 Claim approval

package fabric.authz.claim

import rego.v1

allow if {
  input.action == "claim.approve"
  input.principal.type == "human"
  "workflow.finance_approver" in input.principal.workflow_roles
  input.principal.tenant_id == input.resource.tenant_id
  "economic_reviewer" in input.resource.relationships
  input.principal.id != input.resource.attributes.author_id
  input.resource.attributes.validation_state in {"REVIEWED", "DISPUTED_RESOLVED"}
  input.resource.attributes.model_version == input.context.requested_model_version
  abs(input.resource.attributes.impact_usd) <= input.principal.approval_ceiling_usd
  input.resource.attributes.open_dispute_count == 0
  realization_constraint_passes
}

realization_constraint_passes if {
  input.resource.attributes.publication_state != "LOCKED_REALIZATION"
}

realization_constraint_passes if {
  input.resource.attributes.publication_state == "LOCKED_REALIZATION"
  "workflow.realization_owner" in input.principal.workflow_roles
}

11.3 External publication

Publication should be authorized against a server-generated publication projection containing all included claim approvals and disputes. OPA must not independently fetch each claim.

package fabric.authz.deliverable

import rego.v1

allow if {
  input.action == "deliverable.publish_external"
  input.principal.type == "human"
  publication_role
  input.resource.attributes.all_included_claims_approved
  input.resource.attributes.open_included_dispute_count == 0
  input.resource.attributes.quote_matches_model
  exception_requirement_passes
  publisher_sod_passes
}

publication_role if {
  "workflow.deal_desk" in input.principal.workflow_roles
}

publication_role if {
  "workflow.value_manager" in input.principal.workflow_roles
}

exception_requirement_passes if {
  not input.resource.attributes.exception_required
}

exception_requirement_passes if {
  input.resource.attributes.exception_required
  input.resource.attributes.exception_state == "ACTIVATED"
  time.parse_rfc3339_ns(input.context.now) < time.parse_rfc3339_ns(input.resource.attributes.exception_expires_at)
  input.resource.attributes.exception_covers_deliverable
}

11.4 Exception activation

package fabric.authz.exception

import rego.v1

allow if {
  input.action == "exception.activate"
  input.principal.type == "human"
  input.principal.id == input.resource.attributes.approver_id
  input.principal.id != input.resource.attributes.requester_id
  input.resource.attributes.state == "APPROVED"
  input.resource.attributes.policy_eligibility == "PASS"
  input.resource.attributes.scope_non_empty
  time.parse_rfc3339_ns(input.context.now) < time.parse_rfc3339_ns(input.resource.attributes.approval_expires_at)
}

11.5 Obligations

Policy may permit an action only with obligations:

require_reason_code

require_mfa_step_up

require_second_approver

watermark_provisional

redact_fields

limit_export_columns

write_audit_event

notify_security_reviewer

The enforcement point must reject the action if it does not recognize or cannot satisfy a returned mandatory obligation.

12. Domain state machines

12.1 Claim governance

Recommended states are separate dimensions rather than one overloaded status:

Working state:    CANDIDATE -> WORKING -> CANONICAL -> LOCKED
Validation state: NOT_REVIEWED -> REVIEWED | DISPUTED -> DISPUTED_RESOLVED
Approval state:   NOT_REQUESTED -> PENDING -> GRANTED | REJECTED | REVOKED

Approval is scoped to claim identifier plus model version plus material content hash. Editing a material approved field invalidates the approval through a new claim authorization revision and a domain rule, not through an after-the-fact UI warning.

12.2 Exception lifecycle

DRAFT -> SUBMITTED -> UNDER_REVIEW -> APPROVED -> ACTIVATED -> EXPIRED
                                  \-> REJECTED
ACTIVATED -> REVOKED

Legal transitions:

From

To

Eligible actor

DRAFT

SUBMITTED

Requester with exception.submit

SUBMITTED

UNDER_REVIEW

Named eligible approver or deal desk

UNDER_REVIEW

APPROVED or REJECTED

Eligible approver other than requester

APPROVED

ACTIVATED

Named approver confirmation or explicit system controller after policy pass

ACTIVATED

EXPIRED

System expiry controller

ACTIVATED

REVOKED

Approver or security reviewer

Submission never activates an exception. Approval never silently publishes a deliverable. Clearing a dispute is a separate transaction.

Required exception fields include requester, approver, reason code, narrative, exact claim/model/deliverable/lens scope, requested duration, policy maximum, disclosure text, state-transition actors, and timestamps.

12.3 Realization lock

opportunity.lock_realization creates an immutable baseline version and changes the allowable command set. It requires:

Realization-owner relationship.

Opportunity in a permitted lifecycle state.

Required approvals complete.

No blocking dispute.

Policy decision at the exact model version.

Idempotency key.

Audit event with before/after version identifiers.

After lock, changes occur through governed adjustment or actuals workflows rather than rewriting pre-sale claims.

13. Persistence model

The following is a logical schema. Naming should conform to the repository's existing migration and ORM conventions.

13.1 Principals and memberships

create table authz_principals (
    id uuid primary key,
    tenant_id uuid null,
    principal_type text not null,
    external_subject text null,
    canonical_name text not null,
    status text not null,
    authz_revision bigint not null default 1,
    created_at timestamptz not null,
    deactivated_at timestamptz null
);

create table authz_role_assignments (
    id uuid primary key,
    tenant_id uuid not null,
    principal_id uuid not null,
    role_id text not null,
    scope_type text not null default 'tenant',
    scope_id uuid null,
    approval_ceiling_usd numeric(19,2) null,
    effective_at timestamptz not null,
    expires_at timestamptz null,
    assigned_by uuid not null,
    assignment_reason text not null,
    revision bigint not null default 1,
    unique (tenant_id, principal_id, role_id, scope_type, scope_id)
);

Approval ceiling may alternatively be stored in a separate policy profile when multiple currencies, regions, and claim classes require a richer model.

13.2 Relationships

create table authz_resource_bindings (
    id uuid primary key,
    tenant_id uuid not null,
    resource_type text not null,
    resource_id uuid not null,
    relation text not null,
    principal_id uuid not null,
    effective_at timestamptz not null,
    expires_at timestamptz null,
    assigned_by uuid not null,
    revision bigint not null default 1,
    unique (tenant_id, resource_type, resource_id, relation, principal_id)
);

Use typed relations and validated resource types. Do not use an unrestricted entity-attribute-value table for core authorization facts.

13.3 Delegation and external grants

create table authz_delegation_grants (
    id uuid primary key,
    tenant_id uuid not null,
    subject_principal_id uuid not null,
    actor_principal_id uuid not null,
    scopes text[] not null,
    resource_constraints jsonb not null,
    issued_at timestamptz not null,
    expires_at timestamptz not null,
    revoked_at timestamptz null,
    issued_by uuid not null,
    revision bigint not null default 1
);

create table authz_external_access_grants (
    id uuid primary key,
    tenant_id uuid not null,
    token_hash bytea not null unique,
    deliverable_id uuid not null,
    deliverable_version text not null,
    actions text[] not null,
    audience_constraints jsonb not null,
    issued_by uuid not null,
    issued_at timestamptz not null,
    expires_at timestamptz not null,
    revoked_at timestamptz null,
    revision bigint not null default 1
);

13.4 Break-glass

create table authz_break_glass_grants (
    id uuid primary key,
    tenant_id uuid not null,
    beneficiary_principal_id uuid not null,
    requested_by uuid not null,
    approved_by_primary uuid not null,
    approved_by_secondary uuid not null,
    scopes text[] not null,
    resource_constraints jsonb not null,
    reason_code text not null,
    narrative text not null,
    starts_at timestamptz not null,
    expires_at timestamptz not null,
    revoked_at timestamptz null,
    status text not null,
    constraint check (requested_by <> approved_by_primary),
    constraint check (beneficiary_principal_id <> approved_by_primary),
    constraint check (approved_by_primary <> approved_by_secondary)
);

Break-glass is short-lived, dual-controlled, highly visible, and misuse-adjacent even when policy permits it.

13.5 Decision records

create table authz_decisions (
    decision_id uuid primary key,
    tenant_id uuid not null,
    request_id text not null,
    trace_id text null,
    principal_id uuid not null,
    actor_principal_id uuid null,
    action text not null,
    resource_type text not null,
    resource_id uuid not null,
    allowed boolean not null,
    reason_codes text[] not null,
    obligations jsonb not null,
    policy_version text not null,
    bundle_digest text not null,
    input_fingerprint text not null,
    resource_authz_revision bigint not null,
    membership_revision bigint not null,
    evaluated_at timestamptz not null,
    latency_ms numeric(12,3) not null
);

Do not store raw JWTs, secrets, full prompts, or unrestricted evidence content in decision logs.

13.6 Domain record additions

At minimum:

Claims: author_id, validator_id, approver_id, model_version, material_content_hash, authz_revision, validation and approval states.

Exceptions: full state machine, principal identifiers, exact scope, requested and effective durations, transition timestamps, disclosure text, authz_revision.

Deliverables: exact included-claim snapshot, model version, publication policy decision, publisher, external-grant references, provisional status.

Opportunities: lifecycle state, canonical model version, realization lock actor/time, authz_revision.

14. Fabric_4L module and file structure

Recommended additions:

services/api/app/authz/
  __init__.py
  actions.py                 # Typed action and resource catalog
  models.py                  # AuthzRequest, AuthzDecision, obligations
  principal_context.py       # Adapts existing AuthContext
  attribute_resolver.py      # Server-side PIP
  resource_projections.py    # Minimal policy-safe resource views
  client.py                  # OPA client with timeout/fail-closed behavior
  dependencies.py            # FastAPI authorization dependencies
  command_guard.py           # Transactional command wrapper
  decisions.py               # Decision persistence/outbox
  obligations.py             # Mandatory obligation handlers
  errors.py                  # Stable external denial mapping
  cache.py                   # Revision-aware decision cache

packages/value_fabric/shared/identity/
  fabric_auth.py             # Existing authentication context
  authorization.py           # Stable cross-service authz protocol
  workload_identity.py       # Service/agent principal envelope
  delegation.py              # On-behalf-of envelope validation

policies/authorization/
  bundle/
    manifest.json
    data/
      baseline_roles.json
      action_catalog.json
      static_sod.json
    policy/
      global.rego
      claims.rego
      opportunities.rego
      deliverables.rego
      exceptions.rego
      evidence.rego
      administration.rego
      external_access.rego
  tests/
    global_test.rego
    claims_test.rego
    deliverables_test.rego
    exceptions_test.rego
  schemas/
    request.schema.json
    decision.schema.json
  README.md

services/authorization/              # Add only when sidecar coordination needs a service
  bundle_publisher/
  policy_simulator/
  decision_log_exporter/

migrations/
  ...authz_principals...
  ...authz_role_assignments...
  ...authz_resource_bindings...
  ...authz_grants...
  ...authz_decisions...

scripts/ci/
  check_authorization_catalog.py
  check_raw_role_guards.py
  check_protected_transition_guards.py
  check_policy_bundle.py
  authz_decision_matrix.py

tests/security/authorization/
  test_cross_tenant_decisions.py
  test_dynamic_sod.py
  test_agent_capability_ceiling.py
  test_external_grants.py
  test_pdp_failure_modes.py
  test_authz_cache_revocation.py
  test_direct_transition_bypass.py

The shared authorization protocol is the stable interface. Application and service code must not import Rego policy names or OPA-specific response shapes directly.

15. Integration by execution surface

15.1 FastAPI and domain commands

A route should declare the requested action, then delegate resource loading, decision evaluation, and command execution to a common guard.

@router.post("/claims/{claim_id}/approve", response_model=ClaimView)
async def approve_claim(
    claim_id: UUID,
    body: ApproveClaimRequest,
    ctx: AuthContext = Depends(get_auth_context),
    uow: UnitOfWork = Depends(get_uow),
    authz: AuthorizationService = Depends(get_authorization_service),
) -> ClaimView:
    async with uow.transaction():
        claim = await uow.claims.get_for_update(claim_id)
        decision = await authz.authorize(
            principal=ctx,
            action=Action.CLAIM_APPROVE,
            resource=ClaimPolicyProjection.from_domain(claim),
            context={"requested_model_version": body.model_version},
            cache_mode="disabled",
        )
        decision.require_allowed()
        decision.require_obligations_supported()

        approved = claim.approve(
            actor_id=ctx.user_id,
            model_version=body.model_version,
            reason=body.reason,
            policy_decision_id=decision.id,
            expected_authz_revision=claim.authz_revision,
        )
        await uow.outbox.add(approved.audit_event)
        return ClaimView.from_domain(approved)

Do not expose a generic endpoint that allows clients to set approval_state=GRANTED.

15.2 Frontend and BFF

The frontend may request a batched capability projection to render controls:

{
  "resource": {"type": "claim", "id": "claim_01..."},
  "decisions": {
    "claim.edit_working": {"allowed": true},
    "claim.validate": {"allowed": false, "display_reason": "Independent review required"},
    "claim.approve": {"allowed": false, "display_reason": "Finance approval required"}
  },
  "policy_version": "authz-1.3.0",
  "resource_authz_revision": 17
}

This response is for presentation and workflow guidance. Every write is reauthorized server-side. Capability responses should be short-lived and invalidated by resource or membership revision.

15.3 MCP and agent tools

Every MCP tool is registered with:

Stable action identifier.

Resource type and resource-ID extraction rule.

Required attribute projection.

Whether delegation is mandatory.

Whether the action is categorically unavailable to agents.

Output data classification and redaction obligations.

Example registration:

ToolPolicy(
    name="propose_claim_edit",
    action=Action.CLAIM_PROPOSE_EDIT,
    resource_type=ResourceType.CLAIM,
    delegation_required=True,
    permitted_principal_types={PrincipalType.AGENT},
)

The tool gateway evaluates policy after parsing and validating arguments and immediately before invoking the domain operation. The language model cannot choose a broader action identifier.

15.4 Background jobs

A job envelope includes:

Initiating principal and optional delegation.

Workload principal that executes the job.

Tenant.

Requested action and resource.

Creation-time policy version for audit.

Expiry and idempotency key.

Long-running jobs reauthorize before irreversible or externally visible steps. A permission valid when the job was queued is not assumed valid at publication time.

15.5 Service-to-service calls

Internal calls use signed, short-lived workload envelopes carrying:

Caller workload principal.

Tenant.

Original subject and delegation when applicable.

Allowed audience.

Request and trace identifiers.

Issued, not-before, and expiry times.

The receiving service authenticates the envelope and makes its own policy decision. Trusting the network location or an API-gateway decision alone is insufficient.

15.6 External sharing gateway

The gateway resolves the external token to a grant, verifies scope and revocation, evaluates deliverable.view_external, applies obligations, and serves only the approved immutable projection. It never loads an unrestricted tenant session for an external viewer.

16. PostgreSQL RLS and database hardening

RLS remains a hard tenant boundary and defense-in-depth control.

Required practices:

Enable and force RLS on tenant-owned tables.

Use transaction-scoped tenant context such as SET LOCAL, not a connection-global setting that can leak across pooled requests.

Ensure the normal application database role cannot bypass RLS and is not the table owner where ownership would bypass policy.

Reset and test tenant context across pooled connections.

Use explicit policies for system workloads rather than disabling RLS.

Prevent normal application roles from directly setting protected states.

Prefer append-only approval and transition records with constrained command procedures where database-level protection adds value.

Verify tenant and authorization revisions in the same transaction as high-risk transitions.

RLS answers which tenant rows may be visible or modified. It does not answer whether a finance approver authored the claim, whether an exception is activated, or whether a deliverable is publishable. Those remain domain-policy decisions.

17. Caching, availability, and failure behavior

17.1 Deployment model

Run OPA close to each protected workload, preferably as a sidecar or local decision service. Distribute signed policy bundles from a central publishing pipeline. This reduces network latency and avoids making every application authorization decision dependent on a remote central service.

17.2 Decision caching

Cache only decisions whose semantics tolerate caching. Cache keys include:

tenant_id
principal_id
membership_revision
delegation_revision
action
resource_type
resource_id
resource_authz_revision
policy_version
relevant_context_bucket

Rules:

No positive decision caching for approvals, external publication, exception activation, realization lock, role assignment, break-glass, or revocation.

Sensitive reads use very short TTLs and revision-aware invalidation.

Denials may be cached briefly when revision-aware.

Role, grant, relationship, or resource changes increment revisions and publish invalidation events.

Never cache solely by role and endpoint.

17.3 Failure modes

Invalid policy input: deny and alert as an application defect.

OPA unavailable or bundle not ready: fail closed for protected writes and sensitive reads.

Decision log exporter unavailable: preserve decisions in a durable local outbox; do not silently discard.

Attribute source unavailable: deny protected action unless a narrowly defined read-only degraded mode is approved in policy.

Stale policy bundle: reject startup or remove instance from service when outside the allowed compatibility window.

Unknown obligation: deny.

17.4 Initial service objectives

These are proposed engineering objectives, not measured current guarantees:

Local policy evaluation p95 under 10 ms excluding attribute retrieval.

End-to-end authorization facade p95 under 30 ms for uncached interactive decisions.

Policy bundle propagation under 60 seconds for normal releases and under 10 seconds for emergency revocation bundles.

No lost decision records for protected writes.

99.99 percent availability for the local decision path through redundant application instances.

18. Audit, verification, and observability

18.1 Authorization decision log

Every protected decision records:

Decision, request, trace, and tenant identifiers.

Subject principal and actor principal.

Delegation or external grant identifier.

Action, resource type, and resource identifier.

Allow or deny and normalized reason codes.

Obligations returned and completion status.

Policy version and bundle digest.

Membership, delegation, and resource revisions.

Input fingerprint, not unrestricted raw data.

Evaluation latency and PDP instance.

Break-glass status.

18.2 Domain audit log

The domain audit records what changed:

Actor and subject.

Command.

Before and after state or hashes.

Business reason.

Model and claim versions.

Evidence identifiers.

Authorization decision identifier.

Idempotency key.

18.3 Verification ledger

The verification ledger records control results, such as:

Control identifier.

Test or verification result.

Policy and model version.

Claim and deliverable identifiers.

Evidence references.

Runner workload principal.

It is not the same record as the authorization or domain audit event.

18.4 Dashboards and alerts

Minimum telemetry:

Decision rate and deny rate by action, principal type, tenant class, and policy version.

Top deny reason codes.

PDP and attribute-resolution latency.

Unknown action, input-schema, or obligation events.

Agent requests for categorically forbidden actions.

Self-approval attempts.

Break-glass requests, approvals, usage, and expiry.

Policy-bundle version skew.

External-grant access, failure, and revocation.

Resource-revision race failures.

RLS denial and tenant-context anomalies.

Alerts should distinguish malicious behavior, expected workflow denial, policy defect, and availability failure.

19. Policy development lifecycle

19.1 Governance

Authorization policy is production code. Changes require:

Code review by platform security and a domain owner for affected actions.

Typed schema validation.

Unit tests and decision-table coverage.

Negative and invariant tests.

Policy diff showing changed decisions against a curated corpus.

Signed bundle generation.

Staged rollout with canary and rollback.

Changelog and semantic policy version.

Emergency process for revocation-only changes.

19.2 Policy testing

Required methods:

Rego unit tests.

Table-driven application tests.

Property-based tests for invariants.

Mutation tests that prove tests fail when a deny condition is removed.

Cross-tenant integration tests using live database/RLS behavior.

Decision replay against anonymized production-shaped events.

Shadow evaluation before enforcement.

Load and failure-injection tests.

19.3 Static enforcement in CI

Add repository checks that fail on:

Raw role-string checks outside approved adapters and policy fixtures.

Protected command handlers without an authorization guard.

Client-supplied authoritative role, tenant, approver, or state fields.

Generic update endpoints capable of changing protected states.

Agent tool registration without an action and principal-type policy.

New action identifiers absent from the catalog.

Policy actions unused by code or code actions missing policy.

Tests that skip mandatory tenant or protected-action suites.

OPA bundles without signature, version, schema, or tests.

Semgrep rules should catch local anti-patterns; architectural tests should verify full catalog and handler coverage.

20. Required security test matrix

Scenario

Expected result

Same role, different tenant

Deny without resource-existence disclosure

Finance approver not bound to opportunity

Deny

Claim author attempts approval

Deny SELF_APPROVAL_FORBIDDEN

Approver amount below claim impact

Deny APPROVAL_CEILING_EXCEEDED

Approved claim edited materially

Previous approval invalidated

Requested model version differs from claim

Deny MODEL_VERSION_STALE

Included claim has open dispute

External publication denied

Exception is approved but not activated

Publication remains blocked

Exception requester attempts activation

Deny

Exception expired or revoked

Publication denied; existing link follows revocation policy

Agent attempts validation or approval

Categorical deny

Agent proposes a candidate within delegation

Permit candidate write only

Human lacks action but agent service has capability

Deny because delegation intersection fails

Direct API call bypasses hidden UI control

Deny at API

Direct table update tries to grant approval

Block by DB permissions/constraints

PDP unavailable during approval

Fail closed

Unknown policy obligation returned

Fail closed

Role revoked after capability response

Server-side write recheck denies

Resource changed after policy check

Optimistic concurrency/revision check denies

External token targets superseded version

Deny or serve only exact approved immutable version per policy

Pooled DB connection retains previous tenant context

Test fails; connection is quarantined

Break-glass grant has one approver

Deny creation

Break-glass used by agent

Deny

No protected-path test may be unconditionally skipped in the merge gate.

21. Delivery plan

Phase 0: Inventory and contract freeze

Deliverables:

Enumerate every route, command, MCP tool, worker, and direct database path that reads or mutates governed resources.

Build the action/resource catalog and classify risk.

Identify every role string and legacy ACL implementation.

Publish ADRs for the architecture decisions.

Define the v1 request/decision schema.

Mark the four critical verbs as protected-transition inventory items.

Exit criteria:

Catalog covers 100 percent of known externally callable writes.

Every critical verb has one named domain owner and one canonical command path.

No new legacy role guard may be added.

Phase 1: Authorization facade and shadow mode

Deliverables:

Implement typed models, OPA client, attribute resolver, decision persistence, and policy bundle pipeline.

Adapt existing AuthContext into the new principal context.

Evaluate policy in shadow mode on selected routes while legacy behavior remains authoritative.

Compare legacy outcome with policy outcome and classify divergence.

Exit criteria:

Decision schema is stable and versioned.

Shadow decisions have complete telemetry.

No unexplained divergence for the four critical verbs in the test corpus.

Phase 2: Enforce the critical four

Enforce:

claim.approve

deliverable.publish_external

exception.activate

opportunity.lock_realization

Deliverables:

Explicit command handlers and state machines.

Dynamic SoD.

Revision checks and decision-linked audits.

Fail-closed behavior and negative tests.

UI capability projections and honest control visibility.

Exit criteria:

All four actions deny by default.

No direct generic update can produce the protected state.

Cross-tenant, self-approval, agent-denial, and PDP-failure tests pass in CI.

Phase 3: Relationships, workflow roles, and exception lifecycle

Deliverables:

Workflow role assignments separate from platform roles.

Opportunity bindings and eligible-reviewer picker.

Full exception state machine.

Approval ceilings and tenant policy profiles.

Static SoD at assignment time.

Exit criteria:

Tenant-wide workflow role alone is insufficient for opportunity-sensitive approval.

Submit, approve, activate, expire, and revoke are distinct audited transitions.

Phase 4: Agent, MCP, worker, and service authorization

Deliverables:

Workload principal registry.

Delegation grants and signed internal envelopes.

MCP tool action registry.

Agent categorical-deny policy.

Reauthorization for long-running jobs.

Service API key migration plan.

Exit criteria:

Every agent/tool invocation has an actor, subject when delegated, action, resource, and decision ID.

Agent output cannot cross from candidate to canonical without a human command and new policy decision.

Phase 5: External access and administration

Deliverables:

External access grants and revocation.

Tenant-admin role and relationship UI.

Policy simulation and effective-access view.

Break-glass dual-control workflow.

Redaction and watermark obligations.

Exit criteria:

External viewers cannot acquire tenant context.

All role/binding/grant changes are audited and invalidate revisions.

Phase 6: Full migration and legacy removal

Deliverables:

Migrate remaining reads and writes by risk tier.

Remove or quarantine legacy ACL helpers and raw role checks.

Make CI catalog coverage mandatory.

Run policy in enforcing mode everywhere required.

Complete operations runbooks and incident exercises.

Exit criteria:

No protected action depends on UI-only authorization or raw role strings.

One decision contract and one policy plane are authoritative across all application and AI surfaces.

22. Suggested pull-request sequence

Keep authorization work reviewable and avoid a megabranch:

ADRs, catalog, schemas, and no-new-raw-role CI rule.

OPA bundle build/test/sign pipeline and local development harness.

Authorization facade, decision models, and deny-safe client.

Server-side attribute resolver and policy projections.

Shadow integration for the four critical verbs.

Claim approval command plus author/version/ceiling/SoD enforcement.

Exception state machine with separate activation.

Deliverable publication projection and enforcement.

Realization lock command and immutable baseline.

Opportunity relationship bindings and reviewer eligibility.

Workload principals, delegation, and MCP tool registry.

External access grants and revocation.

Role administration and break-glass.

Legacy ACL removal and full catalog coverage gate.

Each PR should include policy tests, application tests, negative tests, observability, and rollback behavior for its slice.

23. Architecture decision records

Create at least these ADRs:

ADR-Authz-001: Hybrid constrained RBAC, ReBAC, and ABAC through a PBAC plane

Decision: Use roles for job class, relationships for resource scope, attributes for request-time constraints, and one policy decision plane for evaluation.

ADR-Authz-002: OPA as the single general-purpose policy decision point

Decision: Use OPA/Rego behind a Fabric facade; do not embed authorization policy independently in every service or add a second equal policy engine.

ADR-Authz-003: Platform roles and workflow roles are separate namespaces

Decision: Clerk/bootstrap organization roles do not automatically confer value-governance approval authority.

ADR-Authz-004: Workload identity and explicit delegation for AI and services

Decision: Preserve actor and subject; effective authority is the intersection of capabilities and delegation.

ADR-Authz-005: RLS is tenant containment, not complete authorization

Decision: Force RLS while keeping object-, relationship-, workflow-, and state-level decisions in the policy plane and domain commands.

ADR-Authz-006: Protected states are reachable only through explicit commands

Decision: Approval, publication, activation, canonicalization, and realization lock cannot be set through generic update APIs or normal direct database writes.

24. Operational runbooks

Required runbooks:

Policy bundle rollback.

Emergency deny/revocation policy release.

OPA unavailable or bundle-not-ready response.

Role or grant revocation propagation.

Suspected cross-tenant authorization incident.

Break-glass request and post-use review.

Agent forbidden-action spike.

External link compromise and mass revocation.

Decision-log backlog or outbox failure.

Policy-version skew across workloads.

RLS tenant-context leakage detection.

Policy decision replay for incident reconstruction.

Emergency processes must preserve auditability and must not instruct operators to disable authorization globally.

25. Risks and mitigations

Risk

Mitigation

Authorization becomes another parallel subsystem

One facade, one action catalog, one PDP, and mandatory handler coverage

Policy input becomes a giant copy of domain objects

Minimal typed policy projections and explicit attribute contracts

OPA policy and domain state machine disagree

Define legal transitions in domain code and test the same decision tables against policy

Role explosion

Small stable role set; thresholds and scope remain attributes and relationships

Stale cached permissions

Revision-aware cache keys, event invalidation, and no positive cache for critical writes

Agent inherits excessive user authority

Capability/delegation/human authority intersection and categorical deny list

Tenant admin becomes superuser

Separate platform/workflow roles and privileged admin session constraints

Direct DB writes bypass policy

RLS, restricted DB privileges, explicit command paths, immutable events, and CI/runtime tests

Policy outage blocks production

Local OPA instances, signed bundles, readiness checks, durable logs, and tested fail-closed behavior

Deny responses leak resource existence

Uniform external denial and tenant-contained resource loading

Policy changes silently broaden access

Decision diff, mutation tests, canary, signed bundles, and dual review

Break-glass becomes normal workflow

Short expiry, dual control, alerting, visible banners, and mandatory post-use review

Two policy engines emerge through ReBAC tooling

Keep thin relationships in Fabric DB and OPA; introduce a relationship service only through a future ADR

26. Definition of done

The enterprise authorization implementation is complete when:

Every governed action has one catalog identifier, resource type, owner, risk class, policy, and enforcement point.

Authentication, tenant containment, and authorization are separate but composed controls.

Platform roles are distinct from workflow roles.

Opportunity-sensitive approvals require a qualifying relationship.

Static and dynamic separation of duties are enforced and tested.

Agents, services, external viewers, humans, and control runners are distinct principal types.

Agent authority is constrained at the actual tool and command boundary.

Approval, publication, exception activation, canonicalization, and realization lock are explicit commands that cannot be reached through generic updates.

Protected decisions fail closed and produce a decision identifier, policy version, reason codes, and obligations.

High-risk writes evaluate current resource and membership revisions within the transaction boundary.

RLS is forced and pool tenant-context leakage is tested.

Domain audit, authorization decisions, and verification events are separate, correlated records.

Policy bundles are tested, signed, versioned, canaried, observable, and reversible.

CI prevents raw role checks, uncataloged actions, unguarded protected transitions, and skipped mandatory security tests.

External access is exact-version, scoped, expiring, revocable, and does not create tenant membership.

Break-glass is human-only, dual-controlled, time-boxed, alerted, and reviewed.

Legacy ACL paths and UI-only authorization have been removed or formally isolated with an expiring exception.

Security and domain owners have approved the negative decision matrix and incident runbooks.

27. Immediate implementation backlog

The first executable backlog should be:

P0 architecture and control-plane work

Add the action/resource catalog and schemas.

Add an ADR that makes PBAC the single decision plane.

Add a CI ratchet prohibiting new raw role checks.

Implement the Fabric authorization facade and fail-closed OPA client.

Implement decision IDs, reason codes, obligations, and decision outbox.

Build and sign the initial OPA bundle.

P0 domain enforcement

Add author, model version, material hash, and authorization revision to claims.

Replace any generic claim approval mutation with ApproveClaim command.

Implement exception states and prevent submit from activating.

Build publication eligibility projection and PublishDeliverable command.

Build realization lock command and immutable baseline.

Add all negative tests for the critical four actions.

P1 scope and identity work

Split platform roles from workflow roles.

Add workflow role assignments and approval ceilings.

Add opportunity principal bindings.

Add workload principals and delegation envelopes.

Register every MCP/agent tool with an action and resource extractor.

Add external access grants.

P1 operations and governance

Add policy decision dashboards and alerts.

Add bundle rollback and emergency-deny runbooks.

Add policy replay and decision-diff tooling.

Add tenant-admin effective-access and assignment views.

Add break-glass dual control.

28. Final architecture position

Fabric_4L should not choose between RBAC, ABAC, ReBAC, and policy enforcement. It should assign each the job it is good at:

RBAC identifies the chair a principal is eligible to occupy.

ReBAC determines whether that chair is relevant to this opportunity or object.

ABAC determines whether the current principal, resource, version, amount, state, exception, and context satisfy the rule now.

PBAC makes that combined decision consistently and ensures every application and AI execution boundary enforces it.

This architecture preserves the current Clerk and tenant-isolation investments, closes the gap between authentication and domain authorization, prevents agents from becoming implicit superusers, and makes financial approval and external publication independently verifiable controls.