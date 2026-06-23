# Contract Remediation Queue by Layer (From 2026-05-02 Audit)

Source: `reports/CONTRACT_AUDIT_REPORT.md`.

Last updated: 2026-05-18 (Sprint 2 progress pass).

## Prioritized Queue (highest risk + lowest compliance first)

### Layer 4 (current score: 45% → 58% as of 2026-05-18)
Owner: Layer 4 Platform Team (`@layer4-agents`)

- **Cluster L4-C1: Tool exceptions violate Contract §2.4** — ✅ CLOSED 2026-05-18
  - Audit finding: ~27 high-severity throws in tools.
  - Resolution: All `raise` calls in `tools/` are either inside `try/except` blocks in
    `execute()` that return structured error outputs, in internal helpers called within
    those blocks, in non-`BaseTool` route helpers where `HTTPException` is correct, or
    in registry registration methods (startup-time). No bare throws at the tool execution
    boundary. Confirmed by full audit of all files in `services/layer4-agents/src/tools/`.
- **Cluster L4-C2: Agent output parsing via `json.loads` violates Contract §2.5** — ✅ CLOSED 2026-05-18
  - Audit finding: ~8 high-priority `json.loads` on LLM output.
  - Resolution: Canonical `parse_llm_json` boundary created in
    `services/layer4-agents/src/services/llm_output_parser.py`. All three LLM output
    parse sites migrated: `governed_llm_client.call_structured`,
    `together_provider.extract_structured`, `llm_intent_classifier.classify`.
    Private `_parse_json` / `_parse_json_response` methods removed.

Targets/deadlines:
- **2026-05-23:** 45% → 58% ✅ (L4-C1 + L4-C2 closed ahead of deadline)
- **2026-06-06:** 58% → 70% (remaining: inline tool definitions, workflow output schema alignment)
- **2026-06-27:** 70% → 85%

### Layer 2 (current score: 58% → 65% as of 2026-05-18)
Owner: Layer 2 Extraction Team (`@layer2-extraction`)

- **Cluster L2-C1: Agent output `json.loads` usage (§2.5)** — ✅ CLOSED 2026-05-18
  - Audit finding: `json.loads` on LLM function-call arguments in `llm_extractor.py`.
  - Resolution: Canonical `parse_llm_json` boundary created in
    `services/layer2-extraction/src/layer2_extraction/shared/llm_output_parser.py`.
    `_parse_tool_arguments` in `llm_extractor.py` migrated. Note: `json.loads` in
    `api/main.py` and `job_store.py` are deserializing stored structured data (not LLM
    output) and are not §2.5 violations — left unchanged.
- **Cluster L2-C2: Tenant context propagation drift (§2.1)** — OPEN
  - Remaining: tenant_id parameterization gaps in extraction pipeline services.

Targets/deadlines:
- **2026-05-30:** 58% → 65% ✅ (L2-C1 closed ahead of deadline)
- **2026-06-13:** 65% → 75% (L2-C2 tenant propagation)
- **2026-07-04:** 75% → 85%

### Layer 1 (current score: 62%)
Owner: Layer 1 Ingestion Team (`@layer1-ingestion`)

- **Cluster L1-C1: Tenant context parameterization drift (§2.1)** — PARTIALLY CLOSED
  - `get_db_with_tenant` → `get_db_from_context` migration completed (Sprint 1, 2026-05-18).
  - Remaining: broader tenant_id parameterization gaps across ingestion services.
- **Cluster L1-C2: DB session isolation gaps (§2.2)** — OPEN

Targets/deadlines:
- **2026-05-30:** 62% → 70%
- **2026-06-20:** 70% → 80%
- **2026-07-11:** 80% → 85%

### Frontend (current score: 67% → 72% as of 2026-05-18)
Owner: Web Platform Team (`@web-platform`)

- **Cluster FE-C1: Imperative navigation (§2.6)** — ✅ CLOSED 2026-05-18
  - Audit finding: `HypothesesTab.tsx` used `useNavigate()` directly with router state.
  - Resolution: `useNavigation()` already supported `state?: Record<string, unknown>` in
    `NavigationOptions`. Migrated `HypothesesTab.tsx` to `useNavigation()` + `navigateTo(path, { state })`.
    No hook changes required. Zero `useNavigate()` calls remain outside `apps/web/src/navigation/`.
- **Cluster FE-C2: URL string concatenation (§2.6)** — ✅ CLOSED 2026-05-18
  - Audit finding: 12 UI route template-literal concatenation sites across 9 files.
  - Resolution:
    - Created `apps/web/src/navigation/deliverableRoutes.ts` — canonical helper for
      deliverable routes using `getStatePath`. Migrated `ExecutiveView`, `TechnicalView`,
      `CFOView`.
    - Migrated `IntelligenceWorkspaceTabs.tsx` → `workspacePath()`.
    - Migrated `DriverTreeShell`, `CalculatorShell`, `HypothesisShell`, `IntelligenceShell`,
      `ValueStudioShell` → `buildPath()`.
    - Migrated `shell/router.tsx` (2 sites) → `workspacePath()` + `buildPath/getStatePath`.
    - Migrated `Layout.tsx` active-state checks → `isRouteActive()` from `navHelpers.ts`.
  - Tests added: `deliverableRoutes.test.ts`, `navHelpers.test.ts`, `useNavigation.test.tsx`,
    additions to `accountRouting.test.ts`.

Targets/deadlines:
- **2026-05-30:** 67% → 72% ✅ (FE-C1 + FE-C2 closed ahead of deadline)
- **2026-06-20:** 72% → 80% (remaining: type-sync drift, hook architecture gaps)
- **2026-07-11:** 80% → 85%

### Layer 3 (current score: 71%)
Owner: Layer 3 Knowledge Team (`@layer3-knowledge`)

- **Cluster L3-C1: Agent output parsing drift (§2.5)** — OPEN
- **Cluster L3-C2: Tenant/DB contract drift (§2.1/§2.2)** — OPEN

Targets/deadlines:
- **2026-05-30:** 71% → 76%
- **2026-06-20:** 76% → 82%
- **2026-07-11:** 82% → 88%

### Layer 5 (current score: 85%)
Owner: Ground Truth Team (`@layer5-ground-truth`)

- Sustainment only: no regressions, close residual partials.

Targets/deadlines:
- **2026-06-06:** 85% → 87%
- **2026-06-27:** 87% → 90%

### Layer 6 (current score: 90%)
Owner: Benchmarks Team (`@layer6-benchmarks`)

- Sustainment only: maintain green baseline and guardrails.

Targets/deadlines:
- **2026-06-27:** Maintain ≥90%

## Cluster Closure Rule (No Partial Drift)
Each cluster is only marked closed when all are merged together:
1. Runtime contract-aligned backend change.
2. Updated schema/type artifacts.
3. Updated consumers (frontend and/or downstream service).
4. Regression tests proving non-reintroduction.


## Tenant Isolation Coverage Remediation Queue (endpoint-level)

Last updated: 2026-05-18.

| Layer | Uncovered endpoint/route-group backlog | Owner | Due date | Notes |
|---|---|---|---|---|
| L1 | Ingestion exports/admin compatibility surfaces not yet in hostile matrix | @layer1-ingestion | 2026-05-30 | Add route-level hostile tests + matrix row updates. |
| L2 | Secondary extraction admin/reporting routes missing explicit cross-tenant/missing-context assertions | @layer2-extraction | 2026-06-13 | Extend matrix to include remaining status/admin endpoints. |
| L3 | Non-product graph search/subgraph endpoints missing route-level hostile tests in matrix | @layer3-knowledge | 2026-06-20 | Add tenant-hostile coverage for list/read/search variants. |
| L4 | Workflow adjunct endpoints (stream/replay/archive variants) require full matrix mapping | @layer4-agents | 2026-06-06 | Align with existing security invariants suite; add missing fail-closed cases. |
| L5 | Bulk/sync expansion endpoints need explicit endpoint rows tied to hostile tests | @layer5-ground-truth | 2026-06-06 | Keep matrix current for new bulk/sync operations. |
| L6 | Compare/industry-list/validation endpoint families not fully represented in cross-layer matrix | @layer6-benchmarks | 2026-06-27 | Add route-specific hostile + missing-context tests. |
