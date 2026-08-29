# Goal: Enterprise Authorization Control-Plane Foundation

## User Request

Implement the first, foundation-building milestone of the enterprise
authorization architecture described in
`Fabric_4L_Enterprise_Authorization_Implementation_Design.md`. The design
proposes a hybrid constrained-RBAC + ReBAC + ABAC model evaluated through a
single PBAC (policy decision) plane, uses OPA/Rego as the single policy
decision point behind a stable Fabric authorization facade, and defines a
"critical four" first enforcement milestone:
`claim.approve`, `deliverable.publish_external`, `exception.activate`,
`opportunity.lock_realization`.

This goal delivers the **P0 architecture and control-plane work** (Section 27
of the design) plus an initial signed/tested Rego policy bundle covering the
critical four verbs, without yet wiring enforcement into every live domain
route (that is a later milestone). It establishes the durable, reviewable
architecture so the big-bang rewrite is never required.

## Refined Goal

Establish a self-contained authorization control plane inside the existing
`services/api` gateway that is contract-first, tenant-safe, and fail-closed:

1. A typed **action/resource catalog** and **v1 request/decision schemas** for
   authorization decisions, modeled as the stable `fabric.authz.request.v1`
   and `fabric.authz.decision.v1` contracts.
2. A **Fabric authorization facade** (stable Python interface) in the API
   gateway with a **fail-closed decision path**: unknown actions, unknown
   resources, invalid inputs, unavailable decision engine, or unrecognized
   obligations all **deny**. The facade exposes decision IDs, normalized reason
   codes, policy version, and obligations, and persists decision records
   through an outbox so protected decisions are never silently dropped.
3. An initial **OPA/Rego policy bundle** under `policies/authorization/`
   implementing global deny-by-default, categorically forbidden agent actions,
   and the four critical verbs (`claim.approve`, `deliverable.publish_external`,
   `exception.activate`, `opportunity.lock_realization`) per the design's
   Section 11 examples, **without** allowing raw role strings or tenant-id
   presence alone to grant authority. It must include Rego unit tests.
4. **Architecture Decision Records** (ADR-Authz-001..006) committed under
   `docs/explanations/adr/` capturing the six decisions from design Section 23.
5. A **CI ratchet** (`scripts/ci/check_raw_role_guards.py` + a Makefile target,
   wired into the structural/gate surface) that fails on any **new** raw
   role-string check (`role ==`, `has_role(`, `require_role`, membership
   comparisons) added outside an explicit approval allowlist, matching the
   design's "no new legacy role guard" rule.
6. **Security tests** (in `tests/security/authorization/`) covering the design's
   Section 20 safety matrix at the control-plane level: cross-tenant deny
   without resource-existence disclosure, agent categorical deny for the
   forbidden verbs, fail-closed on decision-engine unavailability, unknown-action
   deny, and direct-generic-update-bypass denial.

The facade and policy bundle must be built and tested even though OPA may not be
installed in the local environment — the client must fail closed (deny) when the
engine is unreachable, and the Rego content must be written so it passes
`opa test` when run (OPA coverage is validated by Rego unit tests; live `opa`
binary execution is a validation aid only, not a hard local gate).

## Acceptance Criteria

- [ ] **AC1 — Catalog & schemas**: A typed action/resource catalog exists in
      `services/api/app/authz/` (e.g. `actions.py`) enumerating the namespaced
      permission identifiers from design Section 9, and Pydantic/JSON models for
      `fabric.authz.request.v1` and `fabric.authz.decision.v1` exist with stable,
      versioned `schema_version` fields and typed reason/deny codes.
- [ ] **AC2 — Fail-closed facade**: `services/api/app/authz/` exposes an
      `AuthorizationService`/decision function, adapted from the existing
      `AuthContext` (via `value_fabric.shared.identity.fabric_auth`), that returns
      a typed decision and **denies** for: unknown action, unknown resource type,
      tenant/principal mismatch, decision-engine unavailable/unreachable, invalid
      input, and unrecognized mandatory obligation. A unit test asserts each of
      these deny cases.
- [ ] **AC3 — Decision records / outbox**: Protected decisions are persisted into
      a durable decision record carrying `decision_id`, tenant, principal, action,
      resource, `allowed`, reason codes, obligations, policy version, input
      fingerprint, and revisions; an outbox/queue path ensures a failing exporter
      does not silently drop a decision for a protected write (fail closed or
      durable retry).
- [ ] **AC4 — Rego bundle**: `policies/authorization/` contains `global.rego` plus
      per-domain files (`claims.rego`, `deliverables.rego`, `exceptions.rego`,
      `opportunities.rego`), a request JSON schema, and Rego unit test files
      (`*_test.rego`). The bundle implements: default-deny, the design's
      `agent_forbidden_actions` set (validate/approve/publish_external/submit/
      approve/activate exception, include_in_case, resolve_dispute,
      mark_canonical, lock_realization), tenant equality as necessary-but-not-
      sufficient, self-approval denial, and approval-ceiling denial — with tests.
- [ ] **AC5 — ADRs**: `ADR-Authz-001` through `ADR-Authz-006` are committed under
      `docs/explanations/adr/` following the existing `ADR-NNN-slug.md` naming
      convention and matching design Section 23's six decisions.
- [ ] **AC6 — CI ratchet**: `scripts/ci/check_raw_role_guards.py` exists, is wired
      into the Makefile (a `check-*` target referenced by CI), and **passes cleanly**
      against the current tree while failing when a synthetic prohibited raw
      role-string guard is introduced (proven by a self-test or fixture).
- [ ] **AC7 — Security tests**: `tests/security/authorization/` tests run and pass
      with the `security` marker, covering cross-tenant deny (no disclosure),
      agent categorical deny, PDP-unavailable fail-closed, unknown-action deny,
      and direct-generic-update-bypass denial.
- [ ] **AC8 — Quality gates pass**: `make lint` (ruff), the gateway
      `services/api` tests (`pytest services/api/app/tests`), and the new
      `tests/security/authorization/` tests pass with no new drift; `make
      check-migration-heads` and structural preflight remain green. New ADRs pass
      `check_adr_numbering.py`.

## Scope Boundaries

**In scope:**
- New `services/api/app/authz/` control-plane module (catalog, models, facade,
  decision persistence, outbox, dependencies).
- New `policies/authorization/` Rego bundle + JSON schema + Rego tests.
- Six `ADR-Authz-*` records under `docs/explanations/adr/`.
- `scripts/ci/check_raw_role_guards.py` + Makefile wiring + allowlist baseline.
- New `tests/security/authorization/` security tests.
- Reusing/adapting the existing `AuthContext` (no rewriting of Clerk auth).

**Out of scope:**
- Wiring enforcement into live domain mutation endpoints (claim approve API,
  deliverable publish, exception activate, opportunity lock) — a later milestone.
- Introducing OPA as a live running service/sidecar in deployment manifests.
- Frontend UI changes, BFF capability-projection endpoints, MCP tool registry,
  workload-identity service, external sharing gateway, break-glass, or
  relationship/binding UI (later phases 3–6).
- Migrating existing role checks already in the tree (only new ones are gated).
- Introducing new third-party runtime Python dependencies.
- Touch registered CI workflow definitions under `.github/workflows/`.

## Applicable Project Conventions

**Quality gate commands:** (run, in order)
- `make lint` — ruff across all Python layers
- `pytest services/api/app/tests` — gateway unit tests
- `pytest tests/security/authorization -m security` — new security tests
- `make check-adr-numbering` / `python scripts/ci/check_adr_numbering.py`
- `make check-migration-heads`
- `make verify-structure` — structural preflight + Python contract lint
- Rego: `opa test policies/authorization/...` (validation aid; if the `opa`
  binary is unavailable locally, relying on Rego unit-test correctness is
  acceptable but must be stated)

**Commit convention:**
- Conventional commits with role markers `[B]` (Builder) and `[I]` (Inspector),
  e.g. `feat(authz): [B] add fail-closed authorization facade`, ≤72 chars.
- Assisted-by trailer required on every commit:
  - Builder: `Assisted-by: OpenAI:GPT-5.6 Luna`
  - Inspector: `Assisted-by: OpenAI:GPT-5.6 Sol`
- Follow the repo's existing conventional-commit style used in recent history.

**Guidelines:**
- `AGENTS.md` (top-level) and `.agent/AGENTS.md` — governance and rules.
- `docs/development/DISCOVERY_MAP.md` — source-of-truth routing.
- `docs/contract.md` — platform contract (tenant context, middleware, envelopes).
- Existing `scripts/ci/check_route_auth_dependencies.py` as a structural-check
  style reference.
- `DESIGN.md` for frontend rules (not triggered here — no UI changes).

**Rules:**
- Default deny; fail closed for protected decisions you cannot evaluate.
- Tenant equality is necessary but never sufficient — never grant authority from
  tenant presence or raw role strings alone.
- Preserve tenant isolation; do not remove or weaken existing security tests,
  RLS contracts, or auth gates.
- Do not commit secrets, and do not weaken `ProductionSafetyValidator` checks.
- Keep the shared authorization protocol the stable interface; application code
  must not depend on raw Rego/OPA response shapes.
- No new third-party runtime Python dependencies.
- Do not edit `.github/workflows/` definitions.
