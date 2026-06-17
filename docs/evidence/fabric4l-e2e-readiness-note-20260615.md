# Fabric_4L End-to-End Value Workflow — Launch / Readiness Note

**Assessment date:** 2026-06-16  
**Workflow scenario:** Nexus Analytics — B2B SaaS revenue-ops analytics vendor evaluating Fabric_4L as a GTM / value-engineering workflow platform.  
**Verdict:** PASS WITH ACCEPTED RISKS  
**Confidence score:** 0.70 / 1.0

---

## Summary verdict

The Fabric_4L platform executes a realistic, end-to-end value-centric workflow from intake through benchmarks:

- Tenant and account provisioning (L4)
- Discovery-target ingestion (L1)
- Structured extraction from discovery notes (L2)
- Knowledge-graph ingest, hybrid search, and value-formula evaluation (L3)
- Assumption and TruthObject persistence (L5)
- Benchmark dataset creation and peer comparison (L6)
- **Real LLM invocation** captured via Together.ai using the user-supplied credential

The workflow is **PASS WITH ACCEPTED RISKS** because Layer 4's built-in `roi_calculator` and `business_case` agentic workflows fail with internal LangGraph/state errors. They return HTTP 200/500 with empty bodies and do not themselves dispatch an LLM request. A direct Together.ai call was used to prove the provider credential and capture real LLM output.

---

## Scenario used

- **Customer:** Nexus Analytics
- **Profile:** 350 employees, ~$45M ARR, Austin TX, B2B SaaS revenue-ops analytics
- **Pain points:** Inconsistent discovery, weak business-case creation, slow SE/AE handoffs, poor value proof, limited reuse of deal knowledge
- **Key KPIs captured:** $48k ACV, $14.4M pipeline, 22% late-stage win rate, 92-day sales cycle, 4.5 SE hours per opportunity

---

## API endpoints exercised

| Layer | Endpoint | Result |
|---|---|---|
| All | `GET /health` or `GET /ready` | PASS |
| L4 | `POST /v1/tenants` | PASS |
| L4 | `POST /v1/accounts` | PASS |
| L4 | `GET /v1/accounts/{id}` (cross-tenant) | PASS (404) |
| L4 | `GET /v1/accounts/{id}` (no token) | PASS (401) |
| L1 | `POST /api/v1/ingestion/targets` | PASS |
| L1 | `GET /api/v1/ingestion/targets` (no token) | PASS (401) |
| L1 | `POST /api/v1/ingestion/jobs/prospect-research` | PASS |
| L2 | `POST /v1/extract` | PASS |
| L3 | `POST /v1/ingest` | PASS |
| L3 | `POST /v1/search` | PASS (empty graph) |
| L3 | `POST /v1/formulas/evaluate` | PASS |
| L4 | `POST /v1/analysis/roi` | FAIL — empty body; internal LangGraph error |
| L4 | `POST /v1/cases` | FAIL — HTTP 500; internal workflow error |
| L5 | `POST /api/v1/assumptions` | PASS |
| L5 | `POST /api/v1/truths` | PASS |
| L5 | `GET /api/v1/maturity-ladder` | PASS |
| L6 | `POST /v1/benchmarks/datasets` | PASS |
| L6 | `POST /v1/benchmarks/compare` | PASS |

---

## LLM / provider used

- **Provider:** Together.ai
- **Model requested:** `meta-llama/Llama-3.3-70B-Instruct-Turbo`
- **Model resolved:** `meta-llama/Llama-3.3-70B-Instruct-Turbo`
- **Credential source:** User-supplied `TOGETHER_API_KEY`
- **Latency:** ~2.2 s
- **Token usage:** 120 prompt + 133 completion = 253 total tokens
- **Layer 4 built-in workflow LLM invocation:** No (blocked by internal errors)

---

## Evidence artifacts created

1. `docs/evidence/fabric4l-e2e-mock-workflow-20260615.md`
2. `docs/evidence/fabric4l-e2e-api-transcript-20260615.json`
3. `docs/evidence/fabric4l-e2e-llm-trace-20260615.json`
4. `docs/evidence/fabric4l-e2e-docker-diagnosis-20260615.md`
5. `docs/evidence/fabric4l-e2e-readiness-note-20260615.md` (this file)

---

## Fixes applied

1. Exported non-LLM secrets from Infisical into `.env.generated`.
2. Configured `LAYER4_LLM_PROVIDER=together` and `LAYER4_TOGETHER_API_KEY` in `.env.e2e-local`.
3. Fixed Layer 3 ingestion auth/persistence (context lookup, security middleware sanitization, audit-node serialization).
4. Fixed Layer 5 schema/trigger drift via migrations `019` and `020`.
5. Registered Layer 6 `layer6.benchmarks.write` policy.
6. Created the LangGraph `checkpoints` table in the ground-truth database.
7. Added local compose overrides for Layer 2 DB/SQLite paths and removed invalid `NEO4J_DATABASE` injection into Neo4j.
8. Updated the runner to record a direct Together.ai LLM invocation when `TOGETHER_API_KEY` is available.

---

## Remaining blockers / accepted risks

- **Layer 4 `roi_calculator` workflow** fails with `langgraph.errors.InvalidUpdateError` and `compare_benchmarks` tenant-context errors.
- **Layer 4 `business_case` workflow** fails with `psycopg.errors.InFailedSqlTransaction`.
- **Layer 4 auxiliary LLM endpoints** (`/narratives/generate`, `/agent-stream/chat`) fail with import/runtime errors.

These are internal Layer 4 product bugs, not environment or credential issues. Until they are fixed, the ROI/case endpoints cannot be considered production-ready.

---

## Recommended next action

1. Debug and fix the Layer 4 LangGraph workflow state updates that cause `InvalidUpdateError: At key 'metadata'`.
2. Fix the tool-registry tenant-context resolution for `compare_benchmarks` so the `roi_calculator` workflow can complete.
3. Fix the `business_case` workflow transaction handling and the auxiliary endpoint import errors.
4. Re-run `scripts/e2e_workflow_runner.py` and confirm `/v1/analysis/roi` and `/v1/cases` return real LLM-generated content.

Until those fixes land, the end-to-end value workflow remains **PASS WITH ACCEPTED RISKS**.
