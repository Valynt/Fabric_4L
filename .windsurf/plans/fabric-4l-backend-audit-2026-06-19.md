# Fabric_4L Backend Audit & Implementation Plan

## Goal

Audit the current `Fabric_4L` backend against the durable, asynchronous pipeline described in `docs/_SOURCE OF TRUTH/fabric_4_l_layer_design_brief.md`, and begin implementation of the highest-priority remediation.

The user has selected **pipeline orchestration** as the first priority and asked for a **hybrid first pass**:

- PostgreSQL-backed ingestion-run state machine
- Celery workers / chains per stage
- Transactional outbox table in the same transaction as state changes
- LangGraph used only inside the L4 synthesis step
- Temporal and Kafka deferred until integration contracts are proven

## 1. Audit Findings

### 1.1 Layer 1 — Ingestion (mostly aligned)

- `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` implements the canonical source-intake boundary: `POST /api/v1/ingestion/sources`.
- `SourceIntakeRequest` accepts `notes`, `url`, `audio`, `crm`, `pdf`, `meeting` via `SourceType` enum.
- `IngestedSource` + `SourceVersion` + `SourceIngestionRun` + `NormalizedDocument` models exist and enforce tenant isolation, immutable versions, and content-hash fingerprinting.
- `IngestionRunStatus` defines the full state vocabulary from the brief.
- **Gap:** `source_routes.create_source` only persists the run and emits an outbox event; it does **not** advance the run through the full pipeline. The run is left in `ACCEPTED` / `READY_FOR_EXTRACTION` without downstream orchestration.

### 1.2 Transactional Outbox (partially aligned)

- `EventOutbox` table and `dispatch_outbox_event` Celery task exist and are tested.
- **Gap:** The outbox is used for L1-specific scraping jobs (`SourceCorpus`), not for the canonical source-ingestion handoff to L2. There is no stage-by-stage outbox relay.

### 1.3 Orchestration (major gap)

- No durable orchestrator advances a source ingestion run through:
  `NORMALIZING → CHUNKING → READY_FOR_EXTRACTION → EXTRACTING → REFINING → GRAPH_COMMITTING → SYNTHESIZING → VALIDATING_CLAIMS → APPLYING_POLICY → READY`.
- No `ingestion_run_steps` table for per-stage attempts, errors, and artifact IDs.
- No idempotency or resume semantics for stage execution.
- `BaseWorkflow` / `StateMachine` in `services/layer4-agents/src/layer4_agents/harness/` is a generic agent harness, not the FabricFoundSummary pipeline orchestrator.

### 1.4 L2.5 / Signal Refinery (boundary issue)

- `services/layer2-5-signal-refinery/` is a separate public service with its own `openapi.yaml`.
- The brief positions signal refinement as L2 post-processing, not a separate layer/service.
- The trust-score formula in `signal_refinery.py` is deterministic and matches the brief's weights.

### 1.5 L3 Knowledge Graph (partially aligned)

- L3 exposes entity, evidence, graph, and benchmark routes.
- **Gap:** `benchmarks.py` exists in L3; the brief reserves benchmark policy for L6.

### 1.6 L4 Agent Synthesis (partially aligned)

- `BaseWorkflow` supports checkpointing, tool execution, and LLM/agent nodes.
- **Gap:** There is no dedicated LangGraph workflow for the FabricFoundSummary synthesis graph with the states in the brief:
  `RESOLVE_CONTEXT → LOAD_ACCOUNT_GRAPH → LOAD_VALUE_PACK → RETRIEVE_EVIDENCE → BUILD_FIRMOGRAPHICS → BUILD_STAKEHOLDER_MAP → SYNTHESIZE_PAIN_POINTS → MATCH_VALUE_LEVERS → FORM_QUANTITATIVE_HYPOTHESES → REQUEST_VALIDATION → APPLY_BENCHMARK_POLICY → BUILD_SUMMARY_PROJECTION → HUMAN_GATE_IF_REQUIRED → READY`.

### 1.7 L5 Ground Truth / L6 Benchmarks (partially aligned)

- L5 exposes truth objects, validation, and maturity-ladder APIs.
- L6 exposes benchmark datasets and comparison APIs.
- **Gap:** Neither is explicitly invoked from the ingestion pipeline.

### 1.8 FabricFoundSummary Read Model (missing)

- No dedicated projection or read-model store for the FabricFoundSummary.
- The frontend `ValueNarrativeHome` page does client-side parsing of `notes` and source URL into a `ValueCaseDraft` and never calls the canonical L1 intake endpoint.

### 1.9 Frontend / Source Intake Boundary (major gap)

- `apps/web/src/pages/ValueNarrativeHome.tsx` and `valueNarrativeHomeParser.ts` implement local state and regex-based parsing.
- `handleLaunch` calls `prospectSetup.createSetup` instead of `POST /api/v1/ingestion/sources`.
- This directly violates the brief: "The frontend submits sources and renders a revisioned FabricFoundSummary; it does not orchestrate L1–L6."

### 1.10 Infrastructure (deferred)

- Temporal and Kafka are not present in the codebase. Per user direction, they are intentionally deferred.

## 2. Implementation Plan

### Phase 1 — Data model for durable pipeline state

**Files to modify:**
- `services/layer1-ingestion/src/layer1_ingestion/shared/models.py`

**Changes:**
- Add `IngestionRunStep` model with fields: `id`, `run_id`, `stage_name`, `attempt`, `status`, `input_artifact_ids`, `output_artifact_ids`, `error`, `started_at`, `completed_at`, `tenant_id`.
- Ensure `SourceIngestionRun` has `current_step_id`, `last_step_name`, and `error`.
- Add `OutboxEvent` table (or reuse `EventOutbox`) with explicit `stage_name` and `topic` columns.
- Add Alembic migration.

### Phase 2 — Orchestrator engine

**New files:**
- `services/layer1-ingestion/src/layer1_ingestion/orchestrator/__init__.py`
- `services/layer1-ingestion/src/layer1_ingestion/orchestrator/state_machine.py`
- `services/layer1-ingestion/src/layer1_ingestion/orchestrator/step_executor.py`
- `services/layer1-ingestion/src/layer1_ingestion/orchestrator/outbox_relay.py`
- `services/layer1-ingestion/src/layer1_ingestion/orchestrator/run_coordinator.py`

**Behavior:**
- `StateMachine` defines valid transitions from the brief and raises `TransitionError` on invalid moves.
- `RunCoordinator` provides `start_run`, `advance_stage`, `mark_stage_complete`, `mark_stage_failed`, `retry_run`.
- Each state change writes the run row, the step row, and an outbox event in a single transaction.
- `OutboxRelay` polls and dispatches pending events to Celery tasks per stage.

### Phase 3 — Stage workers (Celery)

**New/modified files:**
- `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` — add per-stage Celery tasks.
- `services/layer1-ingestion/src/layer1_ingestion/orchestrator/stage_handlers/`
  - `normalize.py`
  - `chunk.py`
  - `extract.py`
  - `refine.py`
  - `graph_commit.py`
  - `synthesize.py`
  - `validate_claims.py`
  - `apply_benchmark_policy.py`
  - `build_summary.py`

**Behavior:**
- Each worker receives `(run_id, tenant_id)`.
- It loads the run, verifies the run is in the expected state, checks idempotency via `IngestionRunStep`, performs the stage, writes outputs, and calls the coordinator to advance.
- Errors are caught, recorded on the step, and the run moves to `FAILED_RETRYABLE` or `FAILED_PERMANENT` based on retry count.

### Phase 4 — L4 FabricFoundSummary synthesis workflow

**New files:**
- `services/layer4-agents/src/layer4_agents/workflows/fabric_found_summary.py`
- `services/layer4-agents/src/layer4_agents/workflows/fabric_found_summary_state.py`

**Behavior:**
- Subclass `BaseWorkflow` and build a LangGraph state machine with the FabricFoundSummary states from the brief.
- Nodes call L3 knowledge retrieval, value-pack loading, and L5/L6 clients.
- Outputs a `FabricFoundSummary` object.
- Exposes `POST /v1/accounts/{account_id}/fabric-briefs/{brief_id}/synthesize`.

### Phase 5 — L5 validation and L6 benchmark policy integration

**New files:**
- `services/layer1-ingestion/src/layer1_ingestion/orchestrator/clients/l5_client.py`
- `services/layer1-ingestion/src/layer1_ingestion/orchestrator/clients/l6_client.py`

**Behavior:**
- `validate_claims` stage calls L5 to validate quantified claims and returns `ValidationSummary`.
- `apply_benchmark_policy` stage calls L6 for permitted/prohibited use and benchmark bounds.
- Gate to `NEEDS_REVIEW` or `READY`.

### Phase 6 — FabricFoundSummary read-model projection

**New files:**
- `services/layer1-ingestion/src/layer1_ingestion/projections/fabric_found_summary.py`
- `services/layer1-ingestion/src/layer1_ingestion/api/fabric_brief_routes.py`

**Endpoints:**
- `GET /api/v1/accounts/{account_id}/fabric-briefs/{brief_id}`
- `GET /api/v1/accounts/{account_id}/fabric-briefs/{brief_id}/versions/{version_id}`
- `GET /api/v1/ingestion/runs/{run_id}/stream` (SSE)

### Phase 7 — Frontend intake wiring

**Files to modify:**
- `apps/web/src/pages/ValueNarrativeHome.tsx`
- `apps/web/src/pages/valueNarrativeHomeParser.ts`
- Add a new hook `useSourceIntake` and `useIngestionRun`.

**Behavior:**
- Submit source artifacts via `POST /api/v1/ingestion/sources`.
- Render pending/processed states from the run status.
- Subscribe to the SSE stream for the run.
- Display the FabricFoundSummary returned by the backend projection.

### Phase 8 — Acme acceptance test

**New files:**
- `tests/backend_integrated/test_acme_acceptance.py`
- `services/layer1-ingestion/tests/integration/test_acme_pipeline.py`

**Scenario:**
- Submit Acme notes (support triage, cost $120K, decision by EOQ, Sarah/John).
- Assert one logical source, one immutable version.
- Assert run advances through the pipeline states.
- Assert FabricFoundSummary contains firmographics, stakeholders, pain points, value levers, and a quantified business case.

### Phase 9 — Temporal/Kafka migration document

**New file:**
- `docs/architecture/fabric-4l-pipeline-orchestrator-roadmap.md`

**Contents:**
- When to replace the Celery chain with Temporal.
- How to swap the outbox relay for Kafka.
- Stage-by-stage migration risks.

## 3. Tests and Verification

- `make verify` (contract, type, lint, tests) must pass.
- `make contract-tests` must pass.
- `pytest services/layer1-ingestion/tests/integration/test_acme_pipeline.py` as the primary acceptance test.
- Per-stage unit tests for each Celery worker.
- State-machine transition tests for invalid moves.
- Outbox integration tests for at-least-once delivery.
- Tenant-isolation tests for run steps and projections.

## 4. Risks and Open Questions

- **Risk:** L2 extraction and L3 graph APIs are large and may have idempotency gaps. Each stage worker must be written defensively.
- **Risk:** The current `IngestionRunStatus` enum has many states; some may need to be split or removed once the pipeline is implemented.
- **Open:** Should the FabricFoundSummary projection live in the L1 database, or should it be a separate read-model store?
- **Open:** Does the L2.5 signal refinery service need to be merged into L2, or can it be treated as a library and consumed by the L2 extraction stage worker?

## 5. First Step

After approval, begin with Phase 1 (extend the L1 data model) and Phase 2 (orchestrator skeleton). No code changes will be made before explicit approval.
