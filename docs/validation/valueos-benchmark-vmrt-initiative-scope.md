# ValueOS Benchmark and VMRT Initiative Scope

## Purpose

Implement the ValueOS ground-truth benchmark layer and Value Modeling Reasoning Trace
(VMRT) schema on top of the existing Layer 6 benchmark service without weakening
tenant isolation, contract governance, or Layer 4 provider-agnostic orchestration.

This initiative converts the current Layer 6 benchmark capability from a small
dataset comparison service into a governed data-product surface for:

- 100+ curated benchmark metrics across the initial ValueOS industries.
- Distribution-first statistical profiles using p10, p25, p50, p75, p90, mean,
  sample size, standard deviation, and distribution shape where available.
- Complete provenance, confidence, recency, source licensing, and vintage history.
- VMRT traces that connect pain -> capability -> outcome -> KPI -> financial impact.
- GroundTruthAPI validation methods used by Layer 4 agents and generation pipelines.

## Current Repository Anchors

Use these files as the implementation source of truth:

- Layer 6 runtime: `services/layer6-benchmarks/src/layer6_benchmarks/`
- Layer 6 model: `services/layer6-benchmarks/src/layer6_benchmarks/models/benchmark_dataset.py`
- Layer 6 API schemas/routes: `services/layer6-benchmarks/src/layer6_benchmarks/api/`
- Layer 6 repository: `services/layer6-benchmarks/src/layer6_benchmarks/repositories/benchmark_repository.py`
- OpenAPI contract: `contracts/openapi/layer6-benchmarks.json`
- Generated frontend types: `apps/web/src/api/generated/l6/index.ts`
- Layer 4 benchmark consumer boundary: `services/layer4-agents/src/layer4_agents/interfaces/benchmark_client.py`
- Tenant predicate guard: `tests/ci/test_layer6_repository_tenant_predicates.py`
- Layer 6 unit/API tests: `services/layer6-benchmarks/tests/`
- Frontend contract tests: `apps/web/src/api/__tests__/contract/benchmarks.contract.test.ts`

The current model already supports basic p10-p90 statistical profiles and
tenant/global dataset ownership. It does not yet model full ValueOS metric
taxonomy, provenance source arrays, confidence scoring, benchmark vintages,
distribution-shape metadata, VMRT trace schemas, coverage matrix governance, or
GroundTruthAPI methods beyond basic compare/validate.

## Product Scope

### Benchmark Library

Build a governed Ground Truth Benchmark Library (GTBL) with records organized by:

- Metric identity: stable metric id, slug, display name, description, unit.
- Taxonomy: value pillar, functional domain, category, lifecycle stage, value type.
- Segmentation: industry, company size band, geography, maturity band, revenue band.
- Distribution: p10, p25, p50, p75, p90, mean, std_dev, sample_size, shape.
- Provenance: source name, source type, publication year, URL, license class,
  ingestion date, extraction method, caveats, confidence score.
- Governance: version, vintage, status, owner, reviewer, review timestamp,
  stale-after policy, deprecation reason.

Initial coverage target:

- Five industries: technology, financial services, healthcare, manufacturing, retail.
- 100+ curated baseline metrics.
- Minimum p10-p90 distribution for every production metric.
- No production metric without at least one provenance source and confidence score.

### GroundTruthAPI

Extend Layer 6 with contract-first APIs for:

- `recommendRange`: return the applicable percentile envelope for metric context.
- `compareAgainstDistribution`: position a company value against the peer distribution.
- `validateValue`: validate a quantitative claim against p10-p90 and confidence policy.
- `listMetricCatalog`: query metric definitions independent from dataset storage.
- `getMetricProvenance`: return source and confidence metadata for cited benchmarks.
- `getCoverageStatus`: return industry/persona/value/lifecycle matrix coverage.

Do not let Layer 4 agents query raw benchmark storage directly. All agent and
trace-generation access should go through the governed Layer 6 contract.

### VMRT Schema

Add a versioned VMRT JSON Schema under `contracts/jsonschema/` and mirrored
Pydantic models under the canonical runtime path. The schema must encode:

- Trace metadata: trace id, schema version, industry, persona, value type,
  lifecycle stage, product category, tenant/global scope.
- Pains: 2-4 pains with persona ownership and severity.
- Capabilities: 2-4 capabilities mapped to pains.
- Outcomes: 2-3 outcomes mapped to capabilities.
- KPIs: 2-4 KPIs with baseline, target, unit, timeframe, benchmark reference.
- Financial impacts: 2-4 impacts with formula, inputs, currency, time horizon,
  sensitivity bounds, and KPI linkage.
- Reasoning: 6-12 natural-language reasoning steps with explicit references.
- Assumptions: typed assumptions with source, confidence, and approval state.
- Quality scores: logical coherence, benchmark alignment or numeric plausibility,
  financial rigor, story clarity, overall score, reviewer metadata.

The schema should fail closed when financial impacts cannot be traced back to a
KPI, outcome, capability, and pain.

## Technical Workstreams

### 1. Contract and Schema Baseline

Deliverables:

- `contracts/jsonschema/valueos-vmrt.schema.json`
- `contracts/jsonschema/valueos-benchmark-metric.schema.json`
- OpenAPI additions in `contracts/openapi/layer6-benchmarks.json`
- Generated TypeScript updates for `apps/web/src/api/generated/l6/index.ts`
- Static contract tests for new request and response shapes

Acceptance:

- Invalid VMRT traces fail schema validation.
- Every financial impact requires a KPI reference.
- Every KPI benchmark reference resolves to a valid benchmark metric id shape.
- OpenAPI drift tests pass.

### 2. Layer 6 Domain Model and Repository

Deliverables:

- Expanded benchmark metric dataclasses/Pydantic models.
- Provenance and source confidence value objects.
- Distribution shape and benchmark vintage metadata.
- Neo4j migration for metric source/provenance nodes and versioned benchmark records.
- Repository methods that remain tenant-scoped and preserve global-system baseline rules.

Acceptance:

- `tests/ci/test_layer6_repository_tenant_predicates.py` continues to pass.
- Tenant users cannot create or mutate global baselines.
- Global-system benchmark reads remain visible across tenants without exposing
  tenant-owned data.
- Missing tenant context fails closed.

### 3. Benchmark Data Pack Ingestion

Deliverables:

- Canonical benchmark pack format under `packs/` or a Layer 6 seed directory,
  depending on ownership decision.
- Loader replacing the current `load_default_benchmark_packs` placeholder.
- Validation CLI for 100+ metric files.
- Import report with metric count, source count, confidence distribution, stale items,
  and rejected records.

Acceptance:

- Loader ingests at least 100 production-eligible metrics across the initial
  five industries.
- Every metric has p10-p90, sample size, source provenance, and confidence score.
- Records with missing provenance, invalid percentile ordering, stale vintage,
  or unsupported license class are rejected.

### 4. GroundTruthAPI Implementation

Deliverables:

- Layer 6 handlers/routes for range recommendation, distribution comparison,
  value validation, metric catalog, provenance lookup, and coverage status.
- Stable error codes for missing metric, unsupported segment, stale benchmark,
  low confidence, and invalid value.
- Observability metrics for validation outcomes, rejected low-confidence claims,
  stale benchmark usage, and metric lookup misses.

Acceptance:

- Compare/validate returns confidence and provenance-safe details.
- Values outside p10-p90 produce structured warning/error responses.
- Stale or low-confidence benchmarks are visible to consumers without leaking
  internal source caveats beyond the contract.

### 5. VMRT Validation and Trace Store

Deliverables:

- VMRT Pydantic models and validators.
- Schema compliance checker for CI and generation pipeline use.
- Optional trace repository for gold-standard and generated traces, tenant scoped
  unless explicitly global-system.
- Quality scoring payloads and repair status.

Acceptance:

- The 10 VOS-PT-1 gold traces can be represented without one-off fields.
- Invalid linkage graphs are rejected.
- Trace quality scores below configured thresholds cannot be promoted to
  production-ready status.
- Trace provenance includes benchmark metric ids used by KPIs and formulas.

### 6. Layer 4 Agent Integration

Deliverables:

- Extend `IBenchmarkClient` with GroundTruthAPI operations.
- Update Layer 4 ROI/business-case generation to request benchmark ranges and
  validation results through the interface.
- Add an Integrity Agent or validation step that blocks unsupported quantitative claims.
- Preserve provider-agnostic orchestration; model/vendor-specific logic stays in adapters.

Acceptance:

- Agent-generated quantitative claims must cite evidence, benchmark, or explicit
  assumption.
- Unsupported ROI claims are refused or downgraded to assumptions.
- L4 tests prove benchmark-service-unavailable behavior blocks policy-dependent
  approval rather than silently continuing.

### 7. Coverage Matrix and Readiness Gates

Deliverables:

- Coverage matrix model for industry x persona x value type x lifecycle stage.
- CLI/report emitting empty, underpopulated, partial, complete status per cell.
- Regression checks for vintage-to-vintage row count deltas and distribution drift.
- Readiness artifact under `artifacts/readiness/` for benchmark/VMRT status.

Acceptance:

- Coverage reports identify gaps before generation starts.
- Distribution shifts beyond policy thresholds require reviewer approval.
- Production readiness does not pass when required benchmark/VMRT coverage is red.

## Suggested Milestones

### Milestone 1: Schema Lock and Data Contract

Scope:

- VMRT schema v1.
- Benchmark metric schema v1.
- OpenAPI additions for GroundTruthAPI methods.
- Static schema and contract tests.

Exit criteria:

- Contract tests pass.
- No runtime behavior change yet.
- Schema examples cover at least one CFO cost-savings and one CRO revenue-uplift trace.

### Milestone 2: GTBL Runtime Foundation

Scope:

- Layer 6 model/repository/migration changes.
- Provenance/confidence/vintage fields.
- Pack ingestion validation.
- 100+ curated metric files staged.

Exit criteria:

- Layer 6 targeted tests pass.
- Tenant predicate guard passes.
- Loader rejects malformed or unprovenanced benchmark records.

### Milestone 3: GroundTruthAPI Runtime

Scope:

- API handlers for range recommendation, distribution comparison, validation,
  catalog, provenance, and coverage.
- OpenAPI/generated type refresh.
- Layer 4 interface extension with fake/test adapter.

Exit criteria:

- Layer 6 API tests pass.
- Frontend contract tests pass.
- Layer 4 unit tests prove all benchmark calls go through `IBenchmarkClient`.

### Milestone 4: VMRT Trace Validation

Scope:

- VMRT Pydantic models.
- CI schema compliance checker.
- 10 gold traces encoded.
- Quality scoring and promotion gates.

Exit criteria:

- Gold traces validate.
- Invalid trace linkages fail.
- Low-scoring traces cannot be marked production-ready.

### Milestone 5: Agent and Readiness Integration

Scope:

- Integrity Agent or equivalent validation step in Layer 4.
- Claim traceability enforcement.
- Coverage matrix and benchmark readiness artifact.
- Backend-integrated tests for benchmark-backed formulas and unavailable L6 behavior.

Exit criteria:

- Agent outputs distinguish fact, benchmark, assumption, and inference.
- Policy-dependent approval blocks when benchmark service is unavailable.
- Production readiness includes benchmark/VMRT status.

## Validation Plan

Use narrow validation first:

- `python -m pytest services/layer6-benchmarks/tests -q`
- `python -m pytest tests/ci/test_layer6_repository_tenant_predicates.py -q`
- `pnpm --dir apps/web run test:contracts`
- `python -m pytest services/layer4-agents/tests -k benchmark -q`

Then broaden:

- `make test-layer6`
- `make contract-tests`
- `make verify`

For generated TypeScript/OpenAPI changes, regenerate using the repo's existing
API type workflow rather than hand-editing generated files.

## Risks and Guardrails

- Do not treat benchmark seed data as tenant data unless explicitly scoped.
- Do not let tenant users mutate global-system benchmark baselines.
- Do not expose licensed source details beyond the allowed provenance contract.
- Do not let Layer 4 bypass Layer 6 validation by loading benchmark files directly.
- Do not hardcode pack-specific value drivers into core orchestration.
- Do not claim production readiness from schema validation alone; runtime behavior,
  tenant isolation, and coverage gates must execute.

## Out of Scope for First Implementation

- Fine-tuning a model on the VMRT corpus.
- Building a full frontend benchmark administration UI beyond contract consumers.
- Closed-loop customer outcome ingestion into benchmark distributions.
- Paid/licensed third-party data acquisition workflows.
- Multi-industry expansion beyond the initial five industries and 100+ metrics.

