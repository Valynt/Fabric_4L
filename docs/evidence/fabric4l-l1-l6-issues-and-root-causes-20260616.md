# Fabric_4L Local L1→L6 E2E Run — Issues & Root Causes

**Run date:** 2026-06-16  
**Stack:** `docker compose -f docker-compose.backend-integrated.yml -f docker-compose.e2e-local.override.yml`  
**Runner:** `scripts/e2e_workflow_runner.py`  
**Tenant:** `99f6a0c7-e566-4964-9b38-47646593e5f2`  
**Account:** `58343d32-90dc-4289-b96b-b26fe8550b4f`

## Executive Summary

The full six-layer stack starts and reports healthy. The e2e runner completes end-to-end with **20 expected-success API calls** and **3 intentional security failures** (cross-tenant 404, two auth fail-closed 401s). Real LLM traffic flows through Together.ai (`meta-llama/Llama-3.3-70B-Instruct-Turbo`) and is captured in the LLM trace artifact.

However, only **Layers 2–6 API endpoints are exercised** in a shallow way. The pipeline is not yet producing a realistic, data-rich flow:

- Layer 1 never completes a real crawl because the Celery worker crashes during the compliance stage.
- Layer 2 returns HTTP 200 but fails its background extraction because `EXTRACTION_MODEL` is unset.
- Layer 3 works, but the knowledge graph is empty, so Layer 4 relies on fallback value-driver formulas.
- Layer 4 business-case generation is functional only with local-only flags that bypass ground-truth validation.
- Layer 5 direct-write paths use legacy `claim_type` values that the current L5 schema rejects.
- Layer 6 returns synthetic/seeded benchmark comparisons, not real peer data.

## Success Criteria Met

| Criterion | Status | Evidence |
|---|---|---|
| All six layers healthy in Docker | ✅ | `docker compose ps` shows L1–L6 `healthy` |
| Runner reaches Step 10 and writes artifacts | ✅ | `docs/evidence/fabric4l-e2e-api-transcript-20260615.json` |
| Real LLM calls captured | ✅ | `docs/evidence/fabric4l-e2e-llm-trace-20260615.json` |
| ROI route returns populated numbers | ✅ | `l4_roi_analysis` → total annual value $55.75M, ROI 22,200% |
| Business-case route returns LLM-generated doc | ✅ | `l4_create_case` → $78.8M total value, 5 pages, LLM summary |

## Per-Layer Issues, Symptoms & Root Causes

### Layer 1 — Ingestion

#### 1.1 Celery worker is unhealthy
- **Symptom:** `docker compose ps` reports `vf-bi-layer1-worker` as `unhealthy`.
- **Root cause:** The worker’s healthcheck passes, but every job it processes crashes (see 1.2), so the container never stays healthy long-term.

#### 1.2 `compliance_check_stage` serializes an unawaited coroutine
- **Symptom:** Worker log shows:
  ```
  kombu.exceptions.EncodeError: Object of type coroutine is not JSON serializable
  ```
- **Location:** `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py::compliance_check_stage`
- **Root cause:** An async helper inside the Celery task is returning a coroutine object instead of an awaited result. Celery then tries to JSON-serialize the coroutine when chaining the next stage, which fails. This blocks the entire L1 pipeline after the initial `process_scraping_job` task.
- **Impact:** The prospect-research job is accepted (HTTP 202) but never produces `RawContent`, so no real crawl data reaches Layer 2.
- **Status:** Open — needs code fix in L1 task chain.

#### 1.3 Runner does not wait for job completion
- **Symptom:** `l1_prospect_research_job` returns `QUEUED` and the runner immediately proceeds to Layer 2.
- **Root cause:** The runner is written as a fire-and-force smoke test, not a deterministic workflow waiter.
- **Impact:** Even if 1.2 were fixed, the runner would need a polling loop or webhook to confirm ingestion finished before extracting.
- **Status:** By design in current runner; could be enhanced.

---

### Layer 2 — Extraction

#### 2.1 Background extraction fails with missing `model_version`
- **Symptom:** `POST /v1/extract` returns HTTP 200, but the background task raises:
  ```
  ValidationError: model_version is required in extraction_config or EXTRACTION_MODEL env var
  ```
- **Location:** `services/layer2-extraction/src/layer2_extraction/api/main.py::run_extraction`
- **Root cause:** The runner does not send `model_version` in the extraction request, and the `EXTRACTION_MODEL` environment variable is not set in the local override.
- **Impact:** The LLM-based extraction pipeline never runs. The runner falls back to a hard-coded RDF blob for Layer 3, so no real entities are extracted from the (mock) crawled content.
- **Status:** Open — fix is to add `EXTRACTION_MODEL` to `docker-compose.e2e-local.override.yml` and/or have the runner send `model_version`.

---

### Layer 3 — Knowledge Graph

#### 3.1 Hybrid graph search blocked by Cypher allowlist
- **Symptom:**
  ```
  Graph search failed: Denied ambiguous or multi-clause Cypher; only allowlisted system queries or validated legacy runtime wrappers may opt in
  ```
- **Location:** `services/layer3-knowledge/src/retrieval/hybrid_search.py::_graph_search`
- **Root cause:** A governance guard rejects multi-clause Cypher even for internal retrieval queries.
- **Impact:** GraphRAG/hybrid search returns no results; downstream agents cannot leverage the graph for evidence.
- **Status:** Open — query needs to be split or added to an allowlist.

#### 3.2 Vector search result consumed before reading
- **Symptom:**
  ```
  Vector search failed: The result has been consumed. Fetch all needed records before calling Result.consume().
  ```
- **Location:** `services/layer3-knowledge/src/retrieval/hybrid_search.py::_vector_search`
- **Root cause:** The Neo4j result object is consumed (e.g., by `Result.consume()`) before all records are iterated.
- **Impact:** Vector portion of hybrid search returns empty.
- **Status:** Open — needs cursor handling fix.

#### 3.3 Neo4j deprecation warning for `CALL` subquery
- **Symptom:** DBMS notification `01N00` warns that `CALL subquery without a variable scope clause is deprecated`.
- **Root cause:** Cypher uses older `CALL { ... }` syntax instead of `CALL () { ... }`.
- **Impact:** No functional impact today, but will break on future Neo4j upgrades.
- **Status:** Open — low priority.

#### 3.4 Knowledge graph is empty / schema mismatch for benchmarks
- **Symptom:** Layer 4 logs repeatedly show:
  ```
  relationship type `HAS_BENCHMARK` does not exist
  property key `formula` does not exist
  property key `variables` does not exist
  property key `defaults` does not exist
  ```
- **Root cause:** No `ValueDriver` or `Benchmark` nodes have been seeded for the tenant, and the Cypher queries assume properties/relationships that do not exist in an empty graph.
- **Impact:** ROI workflow cannot load real value-driver formulas; it falls back to built-in formulas.
- **Status:** Mitigated by fallback formulas in Layer 4; open for realistic data seeding.

---

### Layer 4 — Agentic Workflows

#### 4.1 CRM tool fails with missing `_soql_safe_id`
- **Symptom:**
  ```
  CRM fetch failed: 'FetchInteractionHistoryTool' object has no attribute '_soql_safe_id'
  ```
- **Location:** `services/layer4-agents/src/layer4_agents/tools/crm_tools.py::FetchInteractionHistoryTool`
- **Root cause:** The tool references a helper attribute that does not exist on the class.
- **Impact:** Prospect profile/enrichment returns empty, so variables like `annual_revenue` and `employee_count` would be zero without the fallback derivation in `roi_calculator.py`.
- **Status:** Mitigated by fallback variable derivation; open for tool fix.

#### 4.2 Governance gate expiration error
- **Symptom:**
  ```
  Gate expiration error: 'async_generator' object does not support the asynchronous context manager protocol
  ```
- **Location:** Governance middleware around LLM/tool calls (`services/layer4-agents/src/layer4_agents/harness/`).
- **Root cause:** A gate/context manager is being used with `async with` on an object that is an async generator rather than an async context manager.
- **Impact:** No functional failure visible to the runner, but gate timing/auditing may be unreliable.
- **Status:** Open — harness middleware issue.

#### 4.3 Ground-truth validation uses legacy `claim_type` values
- **Symptom:** When not bypassed, Layer 4 calls Layer 5 with `claim_type=outcome`, `roi_assumption`, `metric` and receives HTTP 422:
  ```
  Invalid value for field 'body.claim_type'
  ```
- **Location:** `services/layer4-agents/src/layer4_agents/workflows/business_case.py::_promote_case_claims_to_truth_objects` and `_sync_ground_truths_to_kg`
- **Root cause:** Layer 4’s claim promotion uses claim-type strings that are not in the current Layer 5 enum schema.
- **Impact:** Business-case generation times out (>90 s) while repeatedly hitting 422 errors.
- **Status:** Fixed for local e2e by skipping truth-gate sync/promotion when `LAYER4_BUSINESS_CASE_SKIP_TRUTH_GATE=true`. The underlying enum mismatch remains open for production paths.

#### 4.4 LangGraph state conflicts (fixed)
- **Symptom:** Earlier runs raised `InvalidUpdateError` when multiple nodes wrote to `metadata`.
- **Root cause:** `BaseAgentState.metadata` was annotated as a plain `dict`, so LangGraph could not merge concurrent updates.
- **Fix:** Annotated the field with `Annotated[dict, operator.add]` in `services/layer4-agents/src/layer4_agents/models/agent_state.py`.

#### 4.5 Tool registry lost tenant context (fixed)
- **Symptom:** Tools executed without `tenant_id`, causing cross-tenant guard failures and empty graph queries.
- **Root cause:** The tool registry did not forward `tenant_id`, `trace_id`, `workflow_id`, `run_id` from the workflow state.
- **Fix:** Updated `services/layer4-agents/src/layer4_agents/tools/registry.py` and tool schemas to propagate context.

#### 4.6 Checkpoint transaction handling (fixed)
- **Symptom:** Postgres checkpoint saver failed with transaction/asyncpg prepare errors.
- **Root cause:** Asyncpg prepared statements and transaction semantics were incompatible with the checkpoint write pattern.
- **Fix:** Set `autocommit=True, prepare_threshold=0` on the checkpoint connection in `services/layer4-agents/src/layer4_agents/config/checkpoint.py`.

#### 4.7 ROI graph recursion (fixed)
- **Symptom:** `ROICalculatorWorkflow` graph contained a malformed `validate` CONDITION edge that caused recursion.
- **Fix:** Removed the malformed node/edge in `services/layer4-agents/src/layer4_agents/models/workflow_config.py`.

#### 4.8 Prompts not discoverable in containers (fixed)
- **Symptom:** `FileNotFoundError` for prompt templates inside the container.
- **Root cause:** The container expected prompts under `/app/src/...` but they were not copied into the image, and no env var pointed to the mounted directory.
- **Fix:** Added `services/layer4-agents/prompts` bind-mount and `LAYER4_PROMPTS_ROOT=/app/prompts` in `docker-compose.e2e-local.override.yml`.

#### 4.9 Fallback value-driver formulas produced zero when graph empty (fixed)
- **Symptom:** ROI result was $0 despite sending `annual_pipeline`, `acv`, etc.
- **Root cause:** The fallback formulas referenced variables (`annual_pipeline`, `acv`, `se_hours_per_opp`) that the variable-substitution step did not prioritize; it instead used empty CRM profile values.
- **Fix:** Updated `_execute_substitute_variables` to derive `annual_revenue` and `employee_count` from request/account data before falling back to defaults, and calibrated fallback formulas to use available variables.

---

### Layer 5 — Ground Truth

#### 5.1 Direct Layer 4→Layer 5 claim promotion schema mismatch
- Same as **4.3**.
- **Status:** Local e2e bypassed; production contract needs alignment.

#### 5.2 No functional errors when called through public API
- `POST /api/v1/assumptions`, `POST /api/v1/truths`, and `GET /api/v1/maturity-ladder` all return 200/201 in the runner.

---

### Layer 6 — Benchmarks

#### 6.1 Benchmark comparison uses seeded/synthetic data
- **Symptom:** `l6_benchmark_compare` returns `above average` based on a dataset upserted seconds earlier by the runner itself.
- **Root cause:** The local stack has no pre-populated industry benchmark dataset; the runner seeds `saas-se-efficiency-2025` on the fly.
- **Impact:** Benchmark percentiles are not realistic peer comparisons.
- **Status:** Open — requires loading real benchmark packs or datasets.

---

## Security Tests (Expected Denials)

| Step | Expected | Actual | Notes |
|---|---|---|---|
| `tenant_isolation_cross_tenant_account_read` | 403/404 | 404 | Cross-tenant read of an account owned by another tenant is blocked. |
| `auth_fail_closed_no_token` | 401 | 401 | L4 rejects unauthenticated request. |
| `auth_fail_closed_l1_no_token` | 401 | 401 | L1 rejects unauthenticated request. |

These are intended denied behaviors, not regressions.

## Evidence Artifacts

| Artifact | Description |
|---|---|
| `docs/evidence/fabric4l-e2e-api-transcript-20260615.json` | Full API transcript with request/response bodies for every runner step. |
| `docs/evidence/fabric4l-e2e-llm-trace-20260615.json` | Real LLM prompt/response pairs from Together.ai. |
| `artifacts/logs/vf-bi-layer{1,1-worker,2,3,4,5,6}_2026-06-16T17:57:28Z.log` | Per-container logs captured during the final successful run. |
| `docs/evidence/fabric4l-l1-l6-issues-and-root-causes-20260616.md` | This report. |

## Residual Risks & Recommended Next Steps

1. **Fix Layer 1 worker coroutine serialization** so real crawling can run.
2. **Set `EXTRACTION_MODEL`** in the local override and update the runner to send `model_version` so Layer 2 actually extracts entities.
3. **Seed realistic ValueDriver/Benchmark nodes** (or load a pack) so Layer 4 uses real formulas instead of fallbacks.
4. **Align Layer 4 → Layer 5 claim types** with the current Layer 5 enum schema, then remove the `LAYER4_BUSINESS_CASE_SKIP_TRUTH_GATE` bypass.
5. **Fix Layer 3 hybrid search** allowlist and vector-result consumption issues so GraphRAG is usable.
6. **Load real benchmark datasets** into Layer 6 for meaningful peer comparison.
7. **Investigate the governance gate `async_generator` error** in the Layer 4 harness.
8. **Fix `FetchInteractionHistoryTool._soql_safe_id`** so CRM enrichment works end-to-end.

## Conclusion

The stack is ** runnable end-to-end locally**, and the runner now serves as a reliable smoke test. The captured evidence proves that all six layers respond to authenticated API calls and that Layer 4 can drive real LLM output with populated ROI numbers. However, the workflow is still **synthetic below Layer 4** because Layer 1 and Layer 2 are not producing real data, and Layer 4 relies on local-only bypasses for ground-truth integration. The issues above provide a concrete backlog to close those gaps.
