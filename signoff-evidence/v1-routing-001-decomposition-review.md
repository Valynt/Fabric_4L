# V1-ROUTING-001 — Decomposition Review Packet

- **Task ID:** V1-ROUTING-001
- **PR:** #1252 — `feat(gateway): delegate agent orchestration to L4 + layer-segment delegation router + Meridian certification suite`
- **Repo:** bmsull560/Fabric_4L
- **Branch:** `k3/V1-ROUTING-001`
- **Head SHA:** `55794519d80e2dcf5e0a2953d6862c24671757b3`
- **Base SHA (origin/main at review time):** `e3ace52032f8c80436e46adee4fba27402ae9f31`
- **Merge-base (diff base used below):** `a09e67ef25caa9709f83fb04eaafa16d4eaebaae` (matches PR `baseRefOid`)
- **Size:** 27 files, +2743/−699, 16 commits
- **Review timestamp (UTC):** 2026-08-11T03:54:15Z
- **Method:** read-only. `gh pr view 1252 --json ...` for metadata; `git diff a09e67ef..origin/k3/V1-ROUTING-001` for content. No branches created, no code modified.

**Verdict up front:** the independent reviewer's TOO BROAD ruling is confirmed, and two **blocking defects** were found in the diff itself (§7, F-1/F-2). This PR should not merge as-is regardless of decomposition outcome.

---

## 1. Sub-criteria per component

The PR contains five logically separable components plus generated/config drift.

### C1 — Gateway agent-orchestration delegation to L4 (bug fix for finding A-1)

- **What:** `AgentOrchestrator` stops POSTing to the nonexistent L4 route `/internal/orchestrator/execute-step` (verified: `git grep execute-step` on the head tree returns zero hits under `services/`) and instead delegates create/get/pause/resume/cancel to the real L4 `/v1/workflows` API (verified: `services/layer4-agents/src/layer4_agents/api/routes/workflows.py` exposes `POST /workflows`, `GET /workflows/{id}`, `GET /workflows/{id}/result`, `DELETE /workflows/{id}`, `POST /workflows/{id}/resume`, `POST /workflows/{id}/pause`, mounted at `/v1` via `layer4_agents/api/routers.py:63`). `db.agent_runs` becomes a rebuildable projection refreshed on read; fail-closed 503/502/404 via new `Layer4UnavailableError`/`Layer4DependencyError` exception handlers in `main.py`.
- **Files:** `services/api/app/services/agent_orchestrator.py` (+305/−~60), `services/api/app/routers/agents.py` (+81/−~40), `services/api/app/main.py` (exception-handler portion), `services/api/app/models/schemas.py` (`interrupted` status literal only), `services/api/app/tests/test_agent_orchestrator.py`, `services/api/app/tests/test_i03_durable_persistence_and_llm.py`.
- **Acceptance criteria:** gateway `POST /v1/agents/runs` and `/v1/agents/workflows*` produce real L4 workflow instances; L4 down ⇒ 503 `layer4_unavailable` (never record-only success); invalid state transition ⇒ 409; not-found ⇒ 404; `pytest services/api/app/tests/test_agent_orchestrator.py services/api/app/tests/test_i03_durable_persistence_and_llm.py` green.
- **Independently landable:** **Yes**, except `main.py` and `schemas.py` are shared with C2 (see F-3). This is the launch-critical fix; it has the highest standalone value.

### C2 — Layer-segment delegation router (new capability, finding A-2)

- **What:** new catch-all router `services/api/app/routers/layer_delegation.py` serving `/v1/{agents,ingest,extract,graph,truths}[/ {path:path}]` for GET/POST/PUT/PATCH/DELETE/OPTIONS, delegating to owning layers via `DELEGATION_TARGETS`; tenant injected from verified auth (`X-Tenant-ID` overwritten, never forwarded); allowlisted identity headers forwarded verbatim; 503 `owning_layer_unavailable` on transport error. Registered **last** in `main.py` (after product routers and `layer_proxy`). Settings: `layer{1,2,3,5}_api_base_url`, `delegation_timeout_seconds`.
- **Files:** `services/api/app/routers/layer_delegation.py` (new, 176 lines), `services/api/app/main.py` (registration portion), `services/api/app/core/config.py`, `services/api/app/tests/test_layer_delegation.py` (new), `docs/reference/service-routing-and-api-version-matrix.md` (delegation table).
- **Acceptance criteria:** URL-construction table tests green; spoofed `X-Tenant-ID` from caller is overwritten; hop-by-hop headers stripped; 503 on transport failure; a routing-precedence test proving product routers and `layer_proxy` win over the catch-all (currently **absent** — see §3).
- **Independently landable:** **Yes**, after C1 (shares `main.py`/`config.py`). Depends on F-1 being fixed (config.py as written breaks existing clients).

### C3 — Meridian certification suite (test-only)

- **What:** 13-stage live L1→L6 certification journey entering through the gateway's frontend-convention paths; stage recorder writing `artifacts/certification/{manifest,execution-report}.json`; Tenant-B denial sweep; no mocks. New pytest marker `certification`; new Make target `certify-meridian-journey`. Harness extracted from `tests/backend_integrated/conftest.py` into `tests/shared/live_harness.py` (conftest shrinks ~306→~34 lines, pure refactor).
- **Files:** `tests/certification/{__init__.py,conftest.py,harness.py,test_meridian_production_path.py}` (new, ~1100 lines), `tests/shared/live_harness.py` (new, 302), `tests/backend_integrated/conftest.py` (−306/+34), `pytest.ini` (+1 marker), `Makefile` (+4, target + phony entry).
- **Acceptance criteria:** `pytest tests/certification -m certification` collects; suite fails closed when services are absent; `make test-backend-integrated-validation` still green after the conftest→live_harness extraction (refactor must be behavior-preserving for existing consumers).
- **Independently landable:** **Yes** — but note the suite is designed to be red against the current system and turn green as C1/C2 land ("stages fail against the current (broken) system"). Landing order matters for CI signal, not for correctness: the harness refactor + suite skeleton can land first; the journey only goes green after C1+C2.

### C4 — Canonical L4→L5 claim-type taxonomy (D6)

- **What:** new `layer4_agents/integration/claim_types.py` as L4's single source for the L5 taxonomy; new contract `contracts/jsonschema/claim-types.v1.json` registered in `contracts/schema-index.json`; three-way drift guard `tests/contract/test_claim_type_taxonomy.py`; `layer5_client.submit_truth` validates `claim_type` at the client boundary (local `ValueError` instead of remote 422); `workflows/business_case.py` dedupes its local mapping onto the canonical module via alias `_to_layer5_claim_type = to_layer5_claim_type`.
- **Files:** `services/layer4-agents/src/layer4_agents/integration/claim_types.py` (new), `.../integration/layer5_client.py`, `.../workflows/business_case.py`, `contracts/jsonschema/claim-types.v1.json` (new), `contracts/schema-index.json`, `tests/contract/test_claim_type_taxonomy.py` (new).
- **Acceptance criteria:** `pytest tests/contract/test_claim_type_taxonomy.py` green (L5 enum ↔ contract ↔ L4 mapping); `make test-layer4` green.
- **Independently landable:** **Yes**, fully separable from C1–C3 (different service, different concern). **Caveat (F-4):** the dedupe silently changes falsy-`claim_type` behavior in `business_case.py` (old code defaulted falsy → `"metric"` → `value_driver_metric`; new canonical function raises `ValueError`). Fail-fast is defensible, but it is an unannounced runtime behavior change riding inside a "refactor" commit (`3d1d99b59`).

### C5 — Docs

- **Files:** `docs/architecture/source-of-truth-ratification.md` (new, D1–D11), `docs/architecture/production-path-execution-graph.md` (new, E1–E13), `docs/reference/service-routing-and-api-version-matrix.md` (+32). Landable independently; should land with whichever code PR they describe.

### C6 — Generated / ratchet artifacts (drift surface)

- `config/ci/type_escape_baseline.json` — **present** in the PR (regenerated in commit `e6b7ccec1`, 556 diff lines, mostly line-number churn). The PR body's "intentionally not in this PR" claim is **stale** — the body predates `e6b7ccec1`. See §4.
- OpenAPI export + 2× TS clients — **absent** (see §4). Their absence means the PR as written **introduces contract drift** (F-2).

---

## 2. Changed-path inventory (grouped by subsystem)

Diff base `a09e67ef25caa9709f83fb04eaafa16d4eaebaae` → head `55794519d80e2dcf5e0a2953d6862c24671757b3`. (`gh pr view 1252 --json files` agrees: 27 paths.)

**Gateway (`services/api`) — single-writer surface, human merge review required:**
- `services/api/app/main.py` (M) — exception handlers + `layer_delegation` registered after `layer_proxy`
- `services/api/app/core/config.py` (M) — **removes `layer{1,2,3,5}_timeout_seconds`, adds `delegation_timeout_seconds`** (see F-1)
- `services/api/app/models/schemas.py` (M) — `interrupted` status literal; **undocumented `OntologyMatchResponse` shape change** (see F-2)
- `services/api/app/routers/agents.py` (M)
- `services/api/app/routers/layer_delegation.py` (A)
- `services/api/app/services/agent_orchestrator.py` (M)
- `services/api/app/tests/test_agent_orchestrator.py` (M), `test_i03_durable_persistence_and_llm.py` (M), `test_layer_delegation.py` (A)

**Layer 4 (`services/layer4-agents`):**
- `src/layer4_agents/integration/claim_types.py` (A)
- `src/layer4_agents/integration/layer5_client.py` (M)
- `src/layer4_agents/workflows/business_case.py` (M)

**Contracts — single-writer surface, human merge review required:**
- `contracts/jsonschema/claim-types.v1.json` (A; note: no trailing newline)
- `contracts/schema-index.json` (M; also normalizes a `\u2014` escape — unrelated churn)

**Config / CI — single-writer surface:**
- `config/ci/type_escape_baseline.json` (M, regenerated)
- `pytest.ini` (M, +`certification` marker)
- `Makefile` (M, +`certify-meridian-journey`)

**Cross-cutting test infrastructure:**
- `tests/backend_integrated/conftest.py` (M, −306 lines extracted)
- `tests/shared/live_harness.py` (A)
- `tests/certification/` (A: `__init__.py`, `conftest.py`, `harness.py`, `test_meridian_production_path.py`)
- `tests/contract/test_claim_type_taxonomy.py` (A)

**Docs:**
- `docs/architecture/source-of-truth-ratification.md` (A)
- `docs/architecture/production-path-execution-graph.md` (A)
- `docs/reference/service-routing-and-api-version-matrix.md` (M)

**Explicitly NOT touched** (relevant to reviewer concerns): `packages/shared/**`, `packages/platform-contract/**` (TS client absent — see §4), `apps/web/**`, any `migrations/`/`alembic` path, `k8s/**`, `infra/**`, `config/haproxy/**`, `.github/**`, `contracts/openapi/fabric-4l-api.json` (absent — see §4).

Note the file-count discrepancy: the PR body says "15 files, 13 commits"; the actual PR is 27 files / 16 commits. The body is stale relative to the head SHA.

---

## 3. No-parallel-routing-path proof

**Reviewer concern:** the new router must not create a parallel routing path alongside the canonical gateway.

**External ingress: no parallel path introduced.** The diff touches nothing in `k8s/`, `infra/compose/`, `config/haproxy/`, or `.github/`. `config/haproxy/haproxy.cfg` only fronts Postgres (ports 5434/8404), not HTTP layer traffic. All HTTP ingress remains browser → gateway (`services/api`) → layers, consistent with decision D1 in the PR's own `docs/architecture/source-of-truth-ratification.md`. Evidence: `git diff a09e67ef..HEAD --stat -- k8s infra config/haproxy .github` is empty.

**Inside the gateway: a dual-dispatch surface IS introduced — this is the real finding.** Two routers now serve overlapping URL segments under `/v1`:

- `layer_proxy.py` (pre-existing, unchanged by this PR, mounted at `/v1` in `main.py:247`-area) owns typed routes including `POST /extract`, `GET/POST /truths`, `GET /truths/{id}`, `POST /truths/{id}/validate`, `POST /truths/sync-kg`, `GET /truths/freshness-summary`, `POST /workflows`, `GET /workflows/{id}`, etc. (full decorator list verified from `origin/main`).
- `layer_delegation.py` (new) registers catch-alls `/v1/{agents,ingest,extract,graph,truths}` and `.../{path:path}` for all six methods, mounted **after** `layer_proxy`.

FastAPI matches in registration order, so `layer_proxy`'s exact routes win for their methods, and the delegation catch-all serves everything else on the same segments. Concretely: `POST /v1/extract` → `layer_proxy` (typed L2 client), while `GET /v1/extract` → `layer_delegation` → `L2 /v1` prefix; `GET /v1/truths` → `layer_proxy`, while `PATCH /v1/truths/{id}` → `layer_delegation` → `L5 /api/v1`. **The same URL segment is now dispatched by two different mechanisms depending on method and path depth.** That is not a second ingress path, but it is a parallel in-gateway dispatch surface with different auth plumbing (`tenant_required` + typed clients vs `require_authenticated` + raw header forwarding), different timeout config, and different error shapes.

Mitigating evidence:
- Registration order is explicit and commented in `main.py` ("registered last so product routers and layer_proxy keep precedence").
- Tenant is always overwritten from verified auth in `layer_delegation._request_headers`; spoofed caller `X-Tenant-ID` cannot pass through (covered by `test_layer_delegation.py`).
- `benchmarks` is deliberately excluded from `DELEGATION_TARGETS` because `routers/benchmarks.py` owns it.

Gaps:
- **No routing-precedence test exists.** `test_layer_delegation.py` tests URL construction and header filtering in isolation but never mounts the real app to prove `layer_proxy`/product routers win over the catch-all. A future router reordering in `main.py` would silently flip dispatch. Required before merge: an app-level test asserting `POST /v1/extract`, `GET /v1/truths`, `POST /v1/workflows` resolve to the typed routers, not the catch-all.
- **Runtime behavior cannot be fully determined from the diff alone** (explicit review finding): whether the owning layers' `GovernanceMiddleware` accepts the forwarded header set (`x-service-auth` verbatim + injected `X-Tenant-ID`) on every delegated subpath is only verifiable against a live stack. The Meridian suite (C3) is the intended vehicle for that proof; it is not yet run in CI evidence attached to this PR.

---

## 4. Generated-artifact provenance

Reviewer requirement: OpenAPI export, 2× TypeScript clients, and `config/ci/type_escape_baseline.json` must be regenerated, present, and drift-checked.

| Artifact | In PR? | State |
|---|---|---|
| `contracts/openapi/fabric-4l-api.json` | **Absent** | Stale relative to the PR's own code: still shows `AgentRun.status` enum **without** `interrupted`, and `OntologyMatchResponse` with `account_id: string` (verified by parsing the file at head SHA). |
| `apps/web/src/api/generated/fabric/index.ts` | **Absent** | Same drift: `OntologyMatchResponse` typed with `account_id: string` (line ~3052 at head SHA). |
| `packages/platform-contract/src/typescript/generated/fabric_4l_api.ts` | **Absent** | Not in diff; will drift identically. |
| `config/ci/type_escape_baseline.json` | **Present** | Regenerated in commit `e6b7ccec1` (556 diff lines, line-number churn on `llm_output_parser.py`, `agents.py`, etc.). The PR body's claim that it was held back is stale. Still must be re-verified after any rebase. |

**Secondary drift surface the PR body does not mention:** `config/ci/fabric_openapi_docs_baseline.json` line 764 references `OntologyMatchResponse.account_id`; regenerating the OpenAPI export after the schema change will invalidate that baseline entry too.

**Exact regeneration commands (from repo tooling, verified to exist):**

```bash
python scripts/export_openapi.py
pnpm run check:api-types        # runs generate:api + git diff --exit-code apps/web/src/api/generated
python scripts/ci/type_escape_ratchet.py            # check
python scripts/ci/type_escape_ratchet.py --update   # regenerate baseline
```

The platform-contract TS client is produced by the canonical client generators referenced from `packages/platform-contract` (same `generate:api` pipeline family); verify with `git diff --exit-code packages/platform-contract/src/typescript/generated` after running the generator.

**Blocking:** the drift is not just a missing-artifact nicety. Because `schemas.py` changes `OntologyMatchResponse` (F-2), landing this PR without regenerating the export + clients puts a false contract on `main`. Either revert the `OntologyMatchResponse` hunk (recommended — it is undocumented and breaks its own caller) or regenerate all four artifacts plus the docs baseline in the same PR.

---

## 5. Migration / rollback notes

- **DB migrations:** none. No alembic/migration path touched. `db.agent_runs` remains the same store; its role changes to "rebuildable projection refreshed on read" — a code-level semantics change, not a schema change. Existing rows remain readable.
- **Config/env changes:** adds `delegation_timeout_seconds` (default 30.0); `layer{1,2,3,5}_api_base_url` already existed with defaults. **Removes `layer{1,2,3,5}_timeout_seconds`** — see F-1; if those removals survive, any deployment setting `LAYER1_TIMEOUT_SECONDS` etc. silently loses effect (`extra="ignore"`), and worse, the typed clients crash (F-1).
- **Runtime behavior changes:**
  1. Gateway agent lifecycle now fails closed (503/502) when L4 is down, instead of returning record-only success. Intended, but changes observable behavior for operators — dashboards/alerts that treated "200 with local record" as healthy will flip.
  2. `POST /v1/agents/workflows/{id}/pause` now returns 409 for non-pausable states instead of a silent no-op 200.
  3. L4 `submit_truth` raises local `ValueError` on unmapped/falsy `claim_type` instead of defaulting or relying on a remote 422 (F-4).
  4. New 503 surface `owning_layer_unavailable` on all delegated segments.
- **Rollback strategy:** revert the merge commit. No migration down-sides. Caveats: (a) rollback restores the verifiably broken L4 integration (A-1) — the "old" state is a facade, so rollback should be paired with an incident note, not treated as a safe baseline; (b) any `agent_runs` projection rows written while delegated remain valid but stale until refreshed; (c) if F-1 is merged and later reverted, deployments that removed the `LAYER*_TIMEOUT_SECONDS` env vars in the interim are unaffected (defaults return).
- **Cannot be determined from the diff alone** (explicit finding): whether L4's `/v1/workflows` pause/resume semantics match the gateway's new 409 pre-checks under concurrent state changes (the gateway checks status, then calls L4 — a TOCTOU window exists; L4's own transition validation is the backstop, exercised only by live tests).

---

## 6. Decomposition recommendation

**Recommendation: split into 4 PRs. Do not land as one.** The components have independent acceptance criteria, different subsystems (gateway vs L4 vs test-infra vs contracts), and different risk profiles. The reviewer's TOO BROAD ruling is correct, and splitting also isolates the two blocking defects (both live in C1/C2-adjacent files) from the components that are clean (C3, C4).

### PR-1: Claim-type taxonomy (C4) — no dependencies
- Files: `services/layer4-agents/src/layer4_agents/integration/claim_types.py`, `integration/layer5_client.py`, `workflows/business_case.py`, `contracts/jsonschema/claim-types.v1.json`, `contracts/schema-index.json`, `tests/contract/test_claim_type_taxonomy.py`
- Acceptance: `pytest tests/contract/test_claim_type_taxonomy.py`; `make test-layer4`; explicit changelog note about the falsy-`claim_type` behavior change (F-4) with a test asserting the raise.

### PR-2: Gateway orchestration delegation (C1) — no dependencies, launch-critical
- Files: `services/api/app/services/agent_orchestrator.py`, `routers/agents.py`, `main.py` (exception handlers only), `models/schemas.py` (`interrupted` hunk **only** — revert the `OntologyMatchResponse` hunk), `tests/test_agent_orchestrator.py`, `tests/test_i03_durable_persistence_and_llm.py`
- **Must fix F-2** (drop or fully implement the `OntologyMatchResponse` change, including `routers/intelligence.py:150` and regenerated contracts).
- Acceptance: `pytest services/api/app/tests/`; `python scripts/export_openapi.py && pnpm run check:api-types` clean (regenerated artifacts committed in this PR, not deferred).

### PR-3: Layer-segment delegation router (C2) — depends on PR-2 (shares `main.py`, `config.py`)
- Files: `services/api/app/routers/layer_delegation.py`, `main.py` (registration), `core/config.py`, `tests/test_layer_delegation.py`, `docs/reference/service-routing-and-api-version-matrix.md`
- **Must fix F-1**: keep `layer{1,2,3,5}_timeout_seconds` in `Settings` (they are read by `app/clients/layer{1,2,3,5}_client.py`, unchanged in this PR) or update the clients in the same PR; add an app-level routing-precedence test (§3).
- Acceptance: gateway test suite + new precedence test; `make lint-layer*` / typecheck on `services/api`.

### PR-4: Meridian certification suite (C3) — depends on PR-2 + PR-3 for green signal
- Files: `tests/certification/**`, `tests/shared/live_harness.py`, `tests/backend_integrated/conftest.py`, `pytest.ini`, `Makefile`, `docs/architecture/{source-of-truth-ratification,production-path-execution-graph}.md`
- Acceptance: harness refactor is behavior-preserving (`make test-backend-integrated-validation` unaffected); `pytest tests/certification -m certification --collect-only` clean; suite executed against a live stack with the manifest artifact attached to the PR as evidence.
- `config/ci/type_escape_baseline.json` rides with whichever PR lands last touching Python lines, regenerated via `python scripts/ci/type_escape_ratchet.py --update`.

### Alternative considered (single PR + expanded checklist)
Rejected: even with a checklist, a single PR would (a) mix a launch-critical bug fix (C1) with a new routing capability (C2), an unrelated L4/L5 contract change (C4), and 1,100 lines of live-test infrastructure (C3); (b) force reviewers to verify tenant-isolation, contract drift, and routing precedence across three subsystems in one pass — exactly the failure mode that produced F-1 and F-2, both of which are the kind of cross-file drift a narrower diff would have caught in review.

---

## 7. Blocking findings

- **F-1 (blocking, runtime crash):** `services/api/app/core/config.py` deletes `layer1_timeout_seconds`, `layer2_timeout_seconds`, `layer3_timeout_seconds`, `layer5_timeout_seconds` from `Settings`, but `services/api/app/clients/layer{1,2,3,5}_client.py:22` (unchanged by this PR) still execute `settings.layerN_timeout_seconds` in `__init__`. Pydantic v2 `BaseSettings` raises `AttributeError` for undefined attributes, so every `layer_proxy` typed-client construction (`get_layer1_client()` etc., used by `POST /v1/extract`, `GET/POST /v1/truths`, `/v1/ingestion/*`, …) crashes on first use. Verified directly against the head tree (`git show origin/k3/V1-ROUTING-001:...` for both files).
- **F-2 (blocking, undocumented contract break + runtime 500):** `services/api/app/models/schemas.py` changes `OntologyMatchResponse.account_id: str` → `account: Account` (required field). The only constructor call site, `services/api/app/routers/intelligence.py:150`, still passes `account_id=...` (silently ignored under Pydantic v2 default `extra="ignore"`), so `GET /v1/accounts/{id}/ontology-match` raises `ValidationError` → 500. The change is nowhere in the PR body, and the OpenAPI export / TS clients / docs baseline all still describe `account_id`. This violates the repo's "never silently change a response shape" rule.
- **F-3 (non-blocking, process):** PR body is stale — claims 15 files / 13 commits (actual: 27 / 16) and claims `type_escape_baseline.json` was held back (it was committed in `e6b7ccec1`). Body must be refreshed before re-review.
- **F-4 (non-blocking, disclose):** `business_case.py`'s dedupe onto `claim_types.to_layer5_claim_type` changes falsy-`claim_type` handling from default-to-`value_driver_metric` to `ValueError`. Defensible fail-fast, but must be disclosed and tested.
- **F-5 (non-blocking, test gap):** no app-level routing-precedence test for `layer_proxy`/product routers vs the `layer_delegation` catch-all (§3).
- **F-6 (non-blocking, hygiene):** `contracts/jsonschema/claim-types.v1.json` lacks a trailing newline; `contracts/schema-index.json` includes unrelated `\u2014` normalization churn.

---

## 8. What could not be determined from the diff alone

Recorded as findings per instructions, not guesses:

1. Whether owning layers' governance middleware accepts the delegated header set on every subpath (requires live stack; Meridian suite is the intended proof, not yet evidenced in CI).
2. TOCTOU behavior between the gateway's status pre-check (409 logic in `routers/agents.py`) and L4's own transition validation.
3. Whether `db.agent_runs` projection refresh behaves correctly under L4 partial responses (e.g., missing fields in `WorkflowStatusResponse`) — the mapping code was read but not executed.
4. Whether the type-escape ratchet at head SHA is actually green in CI (author claims a local run: 7022 occurrences, exit 0; not independently reproduced here).
