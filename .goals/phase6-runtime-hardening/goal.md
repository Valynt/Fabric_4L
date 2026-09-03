# Goal: Complete Phase 6 — Layer 4 Agent Runtime Hardening & Migration

## User Request

> Continue from where you left off. Phase 6 — Hardening & migration — IN PROGRESS.
>
> The Layer 4 Agent Runtime (a thin, provider-agnostic execution spine under
> `services/layer4-agents/src/layer4_agents/runtime/`) has shipped Phases 0–5 and
> Phase 6 tasks #1–#3 (tenant fail-closed, ModelProviderBridge, durable Postgres
> memory/checkpoint adapters + migration 048). The remaining Phase 6 items are:
> (1) add the deferred `/v1/runtime/*` introspection/ops routes + gateway/OpenAPI
> surface and land the SDK's remote HTTP transport against them; (2) deprecate
> duplicated legacy `engine/` paths and align `OrchestrationController` as a thin
> facade over `AgentRuntimeImpl`; (3) add contract-breaking change policy notes;
> (4) run `make verify` and `make contract-tests`.

## Refined Goal

Complete the remaining Phase 6 hardening and migration work for the Layer 4
Agent Runtime so the runtime exposes a real HTTP surface, the SDK can talk to it
remotely, legacy duplicated paths are deprecated (not silently removed), the
contract-breaking change policy is documented, and the repo's verification gates
pass. The runtime must remain provider-agnostic, tenant-safe (fail closed on
missing tenant), contract-first, and drift-resistant. No legacy behavior may be
silently broken; deprecations must be additive and documented.

## Acceptance Criteria

- [ ] AC1 — `/v1/runtime/*` introspection/ops routes exist and are registered:
      at minimum `GET /v1/runtime/health`, `GET /v1/runtime/metrics`, and
      `GET /v1/runtime/types` (workflow types / tools / providers). Routes use the
      established auth pattern (`Depends(require_authenticated)` +
      `RequestContext`), are tenant-scoped where data is tenant-specific, and fail
      closed on missing tenant context. A new `api/routes/runtime.py` (or
      equivalent) is registered in `api/routers.py` `register_routers()`.
- [ ] AC2 — The OpenAPI contract (`contracts/openapi/layer4-agents.json`) is
      regenerated/updated to include the new `/v1/runtime/*` paths, and the
      contract-freshness/type-generation gate does not report drift for the new
      paths. Response models are explicit Pydantic DTOs (no raw dicts).
- [ ] AC3 — The SDK (`runtime/sdk/client.py`) gains a remote HTTP transport:
      `AgentRuntimeClient` (or a new `RemoteAgentRuntimeClient`) can bind to the
      `/v1/runtime/*` HTTP surface via an async HTTP client (httpx) instead of an
      in-process `AgentRuntime` port, without changing existing callers' surface.
      The remote transport maps runtime errors to the SDK's canonical error types
      (`RunNotFoundError`, `TenantRequiredError`, `SDKTimeoutError`, etc.) and
      preserves tenant scoping.
- [ ] AC4 — Legacy duplicated `engine/` paths are deprecated additively: a
      `DeprecationWarning` (or documented deprecation marker) is added to the
      duplicated `engine/` modules, and `OrchestrationController` is aligned as a
      thin facade over `AgentRuntimeImpl` where feasible — OR the facade alignment
      is explicitly documented as deferred with a clear rationale. No live startup
      path is broken; `api/startup.py` still boots.
- [ ] AC5 — Contract-breaking change policy notes are added to the appropriate
      governance doc (e.g. `docs/governance/` or `docs/reference/`), referencing
      the existing OpenAPI breaking-change gate and exception/approval model.
- [ ] AC6 — New behavior is tested: unit tests for the runtime routes (auth,
      tenant fail-closed, response shapes) and the SDK remote HTTP transport
      (success, error mapping, tenant scoping). Denied behaviors have passing
      hostile tests (e.g. missing tenant → 4xx, cross-tenant invisible).
- [ ] AC7 — Validation gates pass: `python -m pytest tests/unit -q --tb=short`
      (from `services/layer4-agents`) is green with no regressions; `ruff check`
      on changed files is clean; `python -m mypy src/layer4_agents/runtime` is
      clean. `make verify` and `make contract-tests` are run and their results
      reported (they may require infra; report what ran and what could not).
- [ ] AC8 — Inspector independently verifies each claim: gate commands actually
      run and pass, OpenAPI drift is genuinely resolved, deprecations are additive
      (no silent removal), and no auth/tenant/governance gate is weakened.

## Scope Boundaries

**In scope:**
- New `/v1/runtime/*` introspection/ops routes (health, metrics, types/tools/
  providers) with explicit Pydantic response models and tenant fail-closed.
- OpenAPI contract regeneration for the new paths and drift resolution.
- SDK remote HTTP transport (httpx-based) behind the existing client surface.
- Additive deprecation markers on duplicated `engine/` modules and
  `OrchestrationController` facade alignment (or documented deferral).
- Contract-breaking change policy notes in governance docs.
- Unit tests for routes and remote transport, including hostile/denied cases.
- Targeted validation (pytest unit, ruff, mypy) and reporting of `make verify` /
  `make contract-tests`.

**Out of scope:**
- Removing or rewriting the legacy `engine/` implementation (deprecate only).
- Changing the in-process `AgentRuntimeImpl` execution spine semantics.
- New provider integrations or new workflow types.
- Frontend (`apps/web/`) changes.
- Any silent change to existing API contracts, tenant isolation, governance
  middleware, or production gates.

## Applicable Project Conventions

**Quality gate command:**
- `python -m pytest tests/unit -q --tb=short` (from `services/layer4-agents`)
- `ruff check src/layer4_agents/runtime <changed test files>`
- `python -m mypy src/layer4_agents/runtime`
- `make verify`, `make contract-tests` (report results; may need infra)
- `pnpm contract:breaking` / contract-freshness gate for OpenAPI drift
- See the repo `custom_instruction` Value Fabric Agent Reference for the full
  command map and `docs/development/DISCOVERY_MAP.md`.

**Commit convention:**
- Conventional commits with role marker: `type(scope): [B] description` (Builder),
  `chore(scope): [I] description` (Inspector). Title <= 72 chars.
- Required trailer: `Assisted-by: OpenAI:GPT-5.6 Luna` (Builder) /
  `Assisted-by: OpenAI:GPT-5.6 Sol` (Inspector).
- pnpm-only repo: never `npm install`/`yarn install`.

**Guidelines:**
- `AGENTS.md` (project brain), `DESIGN.md` (frontend governance — not touched
  here), `docs/governance/behavior-first-testing.md` (behavior-first testing),
  `.agent/protocols/permissions.md` (read before tool calls).

**Rules:**
- No critical behavior exists unless tested; denied behaviors must have passing
  hostile tests.
- Never weaken auth, RBAC, tenant isolation, rate limiting, audit logging,
  governance middleware, contract validation, or production gates.
- Do not leak secrets; never commit real secrets.
- Drift prevention: update contracts/types/tests/docs when behavior changes.
  Contracts are the source of truth. Never silently change a response shape.
- Runtime must remain provider-agnostic; provider-specific code belongs in
  adapters.
