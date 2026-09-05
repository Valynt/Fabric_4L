# Goal: Fabric_4L Enterprise Authorization Control Plane

## User Request

A production-grade authorization control plane for Valynt/Fabric_4L covering
human users, service principals, AI agents, external viewers, and system
workers. It must compose constrained RBAC (job class), ReBAC (tenant /
opportunity / account / resource relationships), ABAC (state, ownership,
amount, version, risk, time, approval limits) through a single PBAC decision
and enforcement layer (OPA + Rego), with PostgreSQL RLS as the
tenant-containment backstop. The canonical target architecture design document
is at `.goals/authorization-control-plane/design-doc.md` (the long form of this
goal); it is authoritative where it conflicts with this summary.

## Refined Goal

Build an authorization foundation for Fabric_4L: a typed action catalog,
explicit principal model, separate platform/workflow role namespaces,
opportunity/resource relationship bindings, approval ceilings, delegation and
external-access grants, break-glass grants, Rego policy bundles with tests,
a single `authorize(principal, action, resource, environment) -> Decision`
facade (fail-closed OPA client), PostgreSQL RLS policies on all tenant-owned
authorization tables, decision records correlated to domain events, and
guarded enforcement on four critical verbs: `claim.approve`,
`deliverable.publish_external`, `exception.activate`,
`opportunity.lock_realization`. Preserve the existing Clerk-to-Fabric identity
mapping, AuthContext, tenant propagation, and RLS infrastructure. All changes
must be layered, tenant-safe, contract-aligned, and CI-gated so no new raw role
checks, uncatalogued actions, unguarded protected transitions, or skipped
mandatory authorization tests are introduced.

## Acceptance Criteria

- [ ] **A1 — Principle model and facade.** A shared authorization facade
  `authorize(principal, action, resource, environment) -> Decision` with typed
  principals (`human`, `agent`, `service`, `system_control`,
  `external_viewer`), a typed `Decision` (allowed, decision_id, policy_version,
  reason_codes, obligations, evaluated_at, resource_revision), fail-closed
  behavior when the PDP is unavailable or input is invalid, and default-deny
  for unknown actions. The facade must be usable from `services/api` and
  `packages/shared`.
- [ ] **A2 — Action catalog.** A machine-checkable catalog covering at least:
  `claim.view`, `claim.edit_working`, `claim.validate`, `claim.approve`,
  `claim.include_in_case`, `claim.open_dispute`, `claim.resolve_dispute`,
  `model.mark_canonical`, `deliverable.publish_external`,
  `deliverable.revoke_link`, `exception.submit`, `exception.approve`,
  `exception.activate`, `exception.revoke`, `opportunity.lock_realization`,
  `membership.assign_role`, `break_glass.approve`, plus the discovery /
  administration actions in the design. Every catalog action has a resource
  type, principal-type constraint, and risk class.
- [ ] **A3 — Role model.** Separate `platform.*` and `workflow.*` namespaces.
  `workflow.finance_approver`, `workflow.value_engineer`,
  `workflow.value_manager`, `workflow.technical_reviewer`,
  `workflow.deal_desk`, `workflow.security_reviewer`,
  `workflow.realization_owner`, `workflow.tenant_admin` implemented as
  role-assignment records (not role-string checks). No new `has_role`
  role-string guards on protected paths.
- [ ] **A4 — Relationship model.** `authz_resource_bindings` with typed
  relations (assigned_value_engineer, economic_reviewer, technical_reviewer,
  deal_desk_owner, security_reviewer, realization_owner, review_pool_member,
  etc.), tenant-scoped, versioned, for opportunity and resource scoping.
- [ ] **A5 — DB migrations + RLS.** Alembic migration(s) creating
  `authz_principals`, `authz_role_assignments`, `authz_resource_bindings`,
  `authz_delegation_grants`, `authz_external_access_grants`,
  `authz_break_glass_grants`, `authz_decisions`. RLS enabled and enforced
  (FORCE ROW LEVEL SECURITY) on all tenant-owned authz tables with tenant
  context set via the existing transaction-scoped mechanism. Break-glass
  dual-control check constraints. Append-only decisions.
- [ ] **A6 — Rego policy bundle.** `policies/authorization/` with Rego packages
  for global invariants (default deny, agent categorical deny), claims,
  deliverables, exceptions, evidence, administration, external access;
  request/decision JSON schemas; policy tests (`*_test.rego`); manifest with
  semantic version and digest. Policies implement the exact rules in the
  design section 11 (claim approval gates, publication gates, exception
  activation gates).
- [ ] **A7 — Enforcement on four critical actions.** `claim.approve`,
  `deliverable.publish_external`, `exception.activate`, and
  `opportunity.lock_realization` are enforced through the facade at their
  API/command handlers, with the exception state machine
  (Draft → Submitted → Under Review → Approved/Rejected → Activated →
  Expired). Agents categorically denied for approve/validate/publish/
  activate/lock. Failure to obtain a decision fails closed.
- [ ] **A8 — Tests.** Hostile and regression tests for: cross-tenant access,
  self-approval, missing opportunity relationship, approval ceiling exceeded,
  stale model/resource revision, open dispute, invalid exception transition,
  expired exception, agent attempting a human-only action, unauthorized
  direct state mutation, revoked delegation/external grant, PDP/policy-bundle
  outage, cache invalidation after role removal, RLS bypass attempts,
  break-glass missing dual control, and decision↔audit correlation.
- [ ] **A9 — CI gates.** Checks wired into the existing gate system that fail
 on: new raw `has_role` guards on protected paths (via AST/grep), uncatalogued
  authorization actions, protected commands without an enforcement point,
  direct updates to protected state fields, agent tools without declared
  authorization metadata, and skipped mandatory authorization tests.
- [ ] **A10 — Docs.** Architecture and threat-model documentation, action and
  role catalogs, a staged migration plan for removing legacy role checks, and
 verification evidence (a decision matrix demonstrating fail-closed).

## Scope Boundaries

**In scope:**
- All acceptance criteria A1–A10 listed above.
- The four critical actions (claim.approve, deliverable.publish_external,
  exception.activate, opportunity.lock_realization) — full enforcement.
- The supporting data model, policies, facade, RLS, decision log, and CI wiring
  needed for those actions.
- Documentation of the full phased plan (0–6).

**Out of scope (for this run):**
- Enforcement on the remaining catalog actions beyond the four critical ones
  (model.mark_canonical, exception.revoke, membership.assign_role,
  break_glass.approve, deliverable.revoke_link, and the read/edit actions all
  remain cataloged but not fully enforced end-to-end; their policies exist and
  are tested in Rego).
- Production OPA deployment topology (sidecar vs central) — the deployment
  model is documented, not deployed.
- UI feature work beyond the capability-projection contract if it already
  exists (UI hiding is not enforcement).
- Migration of every legacy role check today — a staged plan is required, and
  the CI gate prevents new additions; full removal is a later phase.
- Cross-layer agent runtime integration beyond the agent categorical-deny
  policy and tool metadata declarations.

## Applicable Project Conventions

**Quality gate commands:**
- `make verify`
- `make lint`, `make typecheck` (per-layer variants exist)
- `pytest -m "unit or security"` (markers include `unit`, `security`,
  `tenant_isolation`, `tenant_boundary`, `contract_static`, `mandatory`)
- `make check-migration-heads`
Rego tests can be run with `opa test` if the binary is available; otherwise
the bundle must parse (warnings documented) and the test policy files exist.

**Commit convention:**
- Conventional commits with role markers: `type(scope): [B] description`
  (Builder) and `type(scope): [I] description` (Inspector), ≤72 chars.
- Trailer `Assisted-by:` with the Builder/Inspector model.
- PR body sections per `.github/pull_request_template.md` when a PR is made
  (Governance Impact, Release & Policy Checklist, Validation).

**Guidelines:**
- `AGENTS.md` (repo rules: six-layer boundaries, tenant isolation, contract
  -first, no critical behavior without a test, no generic Admin/User matrix,
  fail closed, no dev auth bypass, pnpm-only for JS).
- Extraction patterns: Pydantic v2, provenance preserved.

**Rules:**
- No new frameworks or unapproved dependencies beyond an OPA client library.
- Do not weaken existing auth/RBAC/RLS.
- Do not move domain logic across layer boundaries.
- Do not change the six-layer responsibilities.