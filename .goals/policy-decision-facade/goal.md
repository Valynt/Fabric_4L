# Goal: Canonical Policy Decision Facade

## User Request

Evolve the existing GATE and authorization components into one canonical,
transport-neutral **policy-decision facade** under
`value_fabric.shared.governance`. The facade composes existing tenant-context
validation, action/permission policy, ABOM/OPA evaluation, LLM safety,
approval, and masking evaluators. It must **not** reimplement them and must
**not** create a second policy engine under `shared/security`.

Note: the review that motivated this work suggested a "*shared/security
Policy Engine*", but that reflection was corrected in discussion: the intended
outcome is a thin coordinator over the evaluators already present, not a new
parallel engine. The goal here is to close the real defect — policy
enforcement exists but some execution paths can still bypass or gracefully
degrade around it.

## Refined Goal

Introduce a single canonical decision contract and a thin coordinator
(`PolicyDecisionFacade`) that composes the already-present evaluators
(`PolicyEngineClient`/OPA, ABOM, `InvariantEvaluator`, `policy_registry`,
`llm_safety`) into one fail-closed decision path. The core is
transport-neutral: it returns a `Decision` value with an `ALLOW`/`DENY`
effect and typed `obligations`, and never raises HTTP-specific errors.
Each privileged execution boundary (HTTP, tool, memory, LLM, worker,
scheduler, event consumers) applies the decision through a thin adapter that
converts `DENY` into its native failure mode. Bypassing the canonical
enforcement path is made detectable by CI architecture checks, and fail-closed
semantics (INDETERMINATE → DENY; the existing ABOM-only fallback must **not**
authorize after an OPA failure) are made explicit.

## Acceptance Criteria

- [ ] **C1 — Decision contract:** A new `Decision` type exists with
      `effect` (`ALLOW`/`DENY`), `reason_code`, `reason`, typed
      `obligations` (e.g. `MASK`, `REQUIRE_APPROVAL`, `AUDIT`, `RATE`),
      `policy_ids`, `policy_bundle_hash`, `decision_id`, `tenant_id`,
      `actor_id`, `action`, and `resource`. Masking and approval are modeled
      as obligations (coexisting, applied after/before execution), **not** as
      peer authorization effects.

- [ ] **C2 — Transport-neutral core:** A `PolicyDecisionFacade` under
      `value_fabric.shared.governance` composes existing evaluators and
      returns/raises no HTTP-specific behavior. Deny-to-HTTP conversion lives
      only in a FastAPI adapter (401/403); worker/tool/workflow adapters map
      DENY to reject / `ToolGatewayDenied` / approval interrupt respectively.

- [ ] **C3 — Fail-closed by default:** INDETERMINATE decision → DENY.
      `PolicyEngineClient` is corrected so the ABOM-only fallback does not
      authorize after OPA failure; unknown action, missing/malformed/mismatched
      tenant context, missing evaluator, and malformed/empty policy response
      all deny.

- [ ] **C4 — Mandatory enforcement at each boundary:** Tool execution goes only
      through `ToolGateway` (close the `BaseWorkflow._execute_tool()` direct
      `tool_registry.execute()` bypass); governed LLM calls only through the
      approved client; memory/retrieval only through a policy-enforcing
      `MemoryGateway`; privileged HTTP routes use a mandatory authorization
      dependency; workers/schedulers/event consumers use service-principal
      decision contexts. Identity/tenant isolation and RLS are **not**
      replaced — the facade is composition, not the only defense.

- [ ] **C5 — CI architecture gates reject bypass:** Static checks reject
      prohibited direct calls (`ToolRegistry.execute(...)` outside ToolGateway,
      `provider.complete_text(...)` outside approved adapters,
      `retrieval_engine.query(...)` outside approved memory adapters, privileged
      routes lacking a registered action policy, unknown action identifiers).
      Exceptions are narrowly documented for adapter internals and tests.

- [ ] **C6 — Negative integration tests** prove a denied decision prevents the
      underlying side effect, and an allowed decision emits audit containing
      actor, tenant, action, resource, policy IDs, obligations, bundle hash,
      decision ID, and trace ID. The acceptance matrix (missing tenant, malformed
      tenant, tenant mismatch, unknown action/tool, OPA timeout/malformed/empty,
      high-privilege during outage, prompt-injection, PII masking, approval
      gating, direct execution) must be covered by tests.

## Scope Boundaries

**In scope:**
- `Decision`, `DecisionEffect`, `Obligation` types; the `PolicyDecisionFacade`
  coordinator; boundary adapters (FastAPI, tool, worker, workflow).
- Correcting the `PolicyEngineClient` fallback to be fail-closed.
- Wiring `ToolGateway`, `MemoryGateway`, and the governed LLM client to the
  facade; closing the `BaseWorkflow._execute_tool()` bypass.
- CI architecture-gate checks for prohibited direct/privileged calls.
- Tests per the acceptance matrix; documentation of the facade and exceptions.

**Out of scope:**
- Rewriting or replacing OPA, ABOM, `InvariantEvaluator`, `policy_registry`,
  or `llm_safety` evaluators (they remain authoritative evaluators).
- Replacing PostgreSQL RLS, tenant-scoped queries, or service-level validation
  (the facade composes, it does not subsume defense-in-depth).
- A brand-new engine under `value_fabric.shared.security`.
- Routing every database statement through OPA (policy applies at the
  operation/resource boundary, not per-statement).
- Migration rename churn (e.g. renaming `PolicyEngineClient` → `OpaPolicyClient`
  is a nice-to-have future step, not required here).

## Applicable Project Conventions

**Quality gate command:**
- `make test-shared` (shared-package suite), `make lint`, `make typecheck`,
  `make contract-tests`, `make verify`. Static ratchets: `make
  check-model-provider-boundaries`, `make check-raw-http-exception-usage`,
  `make check-value-fabric-public-imports`.

**Commit convention:**
- Conventional commits: `type(scope): description` (≤72 chars), imperative mood.
- Project trailer (override): `Co-authored-by: Ona <no-reply@ona.com>`
- Skill trailer (required by goal skill): `Assisted-by: <PROVIDER>:<MODEL>`
  (Builder: `OpenAI:GPT-5.6 Luna`; Inspector: `OpenAI:GPT-5.6 Sol`).
- Builder markers `[B]`, Inspector markers `[I]` in commit titles.

**Guidelines:**
- `.windsurf/AGENTS.md` (autonomous agent fleet registry)
- `docs/AGENTS.md`, `AGENTS.md` (root agent rules)

**Rules:**
- Multi-tenant isolation is a first-class invariant; never bypass tenant scoping.
- Contract-first: never silently change a response shape; update contracts,
  types, and tests together.
- Fail closed for security, tenant isolation, money, workflow, and governance
  paths.
- Do not add code that is not tested; encode intended allowed + denied behavior.