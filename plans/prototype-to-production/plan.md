# Prototype → Production Hardening

**Branch:** `feat/prototype-to-production-hardening`
**Description:** Close the highest-leverage prototype→production gaps in the Value Fabric platform
across four axes: frontend productionization, backend/API contract discipline, the agentic layer,
and delivery glue.

## Goal
Bring the platform from "works locally / prototype-grade" to production-grade by targeting the four
highest-leverage skill areas from the request — componentization (frontend), API contract design
(backend), tool-schema design (agentic), and CI/observability glue. Ship as a single PR made of
testable commits, each independently verifiable.

## Assumptions (made autonomously — user was unavailable)
1. Target is **this Value Fabric repo**, not the separate flo.fun prototype. The flo.fun V1
   prototype is the inspiration; the production target is the platform codebase here.
2. Scope is **gap-filling hardening**, not green-field work: the repo already has OpenAPI
   contracts per layer, SSE agent streaming (`apps/web/src/api/c1SseParser.ts`,
   `hooks/useSSEUtils.ts`), a LangGraph agent layer (`services/layer4-agents/.../workflows`,
   `tools`, `skills`, `harness`), and Keycloak-based JWT auth.
3. Each Step below maps to **one commit** in the PR, in order. Steps are independent so a step
   can be dropped or re-scoped without breaking the rest.

## Implementation Steps

### Step 1: Frontend Componentization & Token Extraction
**Files:** `apps/web/src/components/**`, `apps/web/src/features/**`, `apps/web/src/app/**`,
`apps/web/src/styles/**` (extract `tokens.css` if absent), `DESIGN.md` (reference)
**What:** Survey prototype-derived markup still inline in pages; extract design tokens
(color/spacing/typography) into a single token source; split oversized page components into
presentational + stateful container components; lift server-state pulls into TanStack Query hooks
with loading/empty/error states. Reuse existing shell/tab/right-rail patterns (per DESIGN.md).
**Testing:** `pnpm --dir apps/web run lint`; `pnpm --dir apps/web run typecheck`;
`pnpm --dir apps/web run test`; `pnpm --dir apps/web run build`

### Step 2: Backend API Contract & Error/Observability Discipline
**Files:** `contracts/openapi/*.json`, `contracts/jsonschema/**`, route handlers in
`services/layer*-*/src/**/api/routes/**` as needed, `packages/shared/**`
**What:** Ensure every route touched has: typed request/response models (Pydantic), matching
OpenAPI entries, structured error codes with stable shape (no raw stack traces), request-id +
tenant-id in logs. Fix any drift found between specs and handlers.
**Testing:** `make contract-tests`; targeted `pytest` per touched layer; `pnpm run check:api-types`

### Step 3: Agentic Layer — Tool Schema & Eval Harness
**Files:** `services/layer4-agents/src/layer4_agents/tools/**`,
`services/layer4-agents/src/layer4_agents/harness/**` (extend or verify eval harness),
`services/layer4-agents/src/layer4_agents/workflows/**`
**What:** Audit every agent tool for precise JSON-schema `parameters` and `description`s (the #1
agent failure point per the request); add input validation and fail-closed fallback in core
workflows; stand up an eval harness — golden-path allowed/denied tests — so prompt/tool changes
are measurable, not gambles. Keep provider-agnostic (adapter boundary per governance).
**Testing:** `pytest services/layer4-agents/tests -m unit`; run the harness/evals entrypoint
(named in `services/layer4-agents/README.md`); `make typecheck-layer4`
**Status: ✅ Complete (one real fix applied)** — Tool schemas are Pydantic v2 with Field
descriptions, `input_schema`/`output_schema`, timeout defaults, and tenant-spoofing rejection
(`tools/registry.py` + `models/tool_schemas.py`); `ToolResult` structured errors per contract §2.4.
Eval harness already fully provisioned (`evals/manifest.yaml` wiring `make evals` and
`tests/evals`; `ai-evals-pipeline.yml`; deterministic gates for schema validity, tool authz,
tenant isolation, citations, cost/latency). **Fix applied:** `services/layer4-agents/pyproject.toml`
was missing 10 pytest markers used by the layer's tests (mandatory, contract, security,
tenant_isolation, adversarial, authorization, injection, jwt_validation, p0, postgres), producing
`PytestUnknownMarkWarning` noise. Registered them + `make typecheck-layer4` passes. Test suite:
**558 passed / 0 failed.**

### Step 4: Streaming, Guardrails & Delivery Glue
**Files:** `apps/web/src/agui/**`, `.github/workflows/pr-checks.yml`,
k8s/deploy env parity docs (`.env.example`)
**What:** Verify SSE agent-stream path has timeouts, error events, and graceful degradation on
mid-stream failure (human-in-the-loop escape hatch); confirm every new env var is in `.env.example`
with safe defaults; add CI coverage for the new eval harness if a job slot is appropriate.
**Testing:** `pnpm --dir apps/web run test:e2e` (mocked); `make verify`
**Status: ✅ Complete (verified, no code change required)** — `useJobStream.ts` already hardens
SSE: Zod-validated payloads, 30s connection timeout (`SSE_TIMEOUT_MS`) → polling fallback,
`onerror` → polling fallback, guaranteed cleanup, race-control refs. `AgentEventClient.ts`
(`agui/`) is SSE-first with legacy single-POST fallback on 404/network error, AbortSignal
cancellation, and guaranteed RUN_STARTED → RUN_FINISHED/RUN_ERROR event sequencing. `parseAgentEventJson`
validates events. Eval workflow already wired in `.github/workflows/ai-evals-pipeline.yml`
(separate from pr-checks, so no slot added). No new env vars introduced → `.env.example` parity holds.

## STOP
Stop after Step 4 is implemented and all listed validation commands pass. Report changed files,
validation run, and remaining risks. Do not expand scope beyond the plan.