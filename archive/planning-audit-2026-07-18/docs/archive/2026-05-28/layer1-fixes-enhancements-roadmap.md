# Layer 1 (Ingestion) — Fixes & Enhancements Roadmap

## Purpose

This roadmap defines a contract-first, tenant-safe plan to harden and improve **Layer 1 ingestion** across runtime code, service wrappers, contracts, and operations.

Canonical scopes:

- Runtime package: `value_fabric/layer1/`
- Deployable service: `services/layer1-ingestion/`
- Layer 1 contracts: `contracts/openapi/layer1-ingestion.json` and related schemas

## Goals

1. Eliminate ingestion reliability and lifecycle drift.
2. Strengthen tenant isolation and governance paths.
3. Improve observability and operational recovery.
4. Lock contract compatibility between Layer 1 APIs and consumers.
5. Improve throughput and cost efficiency without changing layer responsibilities.

## Workstreams

## WS1 — Tenant Isolation & Security Hardening (P0)

### Scope

- Validate tenant context extraction from authenticated context only.
- Verify repository/query tenant filters on every read/write path for jobs, sources, crawl artifacts, and compliance records.
- Add hostile tests for cross-tenant read/write attempts.

### Deliverables

- Tenant-context propagation audit for all Layer 1 routes and service methods.
- Cross-tenant isolation test suite updates.
- Structured error responses for unauthorized tenant access paths.

### Exit Criteria

- All Layer 1 data access methods enforce `tenant_id` filters.
- Hostile tests pass for "Tenant A cannot read/mutate Tenant B data".

## WS2 — Job Lifecycle Correctness & Queue Reliability (P0)

### Scope

- Normalize ingestion job state transitions (`queued -> running -> completed/failed/cancelled`) and fail-closed behavior.
- Validate Celery retry, backoff, idempotency keys, and dead-letter behavior.
- Harden restart/recovery semantics for in-flight jobs.

### Deliverables

- Job lifecycle state-machine invariants documented and asserted in tests.
- Regression tests for duplicate dispatch, retry storms, and worker restarts.
- Recovery runbook updates for backlog drain and replay.

### Exit Criteria

- No invalid state transitions in integration tests.
- Restart-safe recovery scenario covered in CI-gated tests.

## WS3 — Compliance & Provenance Integrity (P0)

### Scope

- Ensure robots/compliance checks cannot be bypassed by edge routing paths.
- Ensure provenance metadata completeness for downstream Layer 2/Layer 3 traceability.
- Validate source policy capture and evidence persistence.

### Deliverables

- Compliance gate coverage matrix for all crawler/adapters.
- Provenance schema validation tests for emitted ingestion artifacts.
- Alerting for compliance gate failures and policy denials.

### Exit Criteria

- Compliance decisions are auditable and attached to ingestion records.
- Provenance fields required by downstream contracts are always present.

## WS4 — API & Contract Alignment (P1)

### Scope

- Reconcile route handlers vs OpenAPI for all `/api/sources*` and ingestion control endpoints.
- Validate compatibility behavior and deprecation paths.
- Update frontend/service clients only when contract changes are intentional.

### Deliverables

- Contract drift report (route response/request shape vs OpenAPI).
- Contract tests for success/error envelopes and edge cases.
- Versioned deprecation notes where compatibility shims still exist.

### Exit Criteria

- Contract tests pass against current handlers.
- No undocumented response-shape drift.

## WS5 — Observability & Operability (P1)

### Scope

- Improve metrics for queue depth, job latency, retry rate, compliance denials, crawl quality-gate failures.
- Standardize structured logging with request IDs / job IDs / tenant IDs.
- Ensure runbooks align with actual failure modes.

### Deliverables

- Metrics gap closure list implemented in Layer 1 service.
- Correlation-ID propagation checks.
- Updated runbooks for SEV triage and queue incidents.

### Exit Criteria

- Dashboards and alerts cover top Layer 1 failure classes.
- Operators can trace a failed ingestion run end-to-end.

## WS6 — Performance & Cost Efficiency (P2)

### Scope

- Improve scheduler prioritization and crawl routing efficiency.
- Tune concurrency and backpressure across Playwright/Celery/Redis boundaries.
- Reduce duplicate fetch and post-processing overhead.

### Deliverables

- Baseline benchmark profile and target SLO deltas.
- Safe optimizations behind configuration flags where needed.
- Performance regression tests for representative workloads.

### Exit Criteria

- Measured throughput/latency improvement with no contract or tenant regression.

## Suggested Delivery Sequence (90-day view)

### Phase 1 (Weeks 1–3): Stabilize P0 Security + Lifecycle

- WS1 and WS2 fail-first tests.
- Tenant and state-transition audits completed.
- Critical bug fixes for job correctness and isolation.

### Phase 2 (Weeks 4–6): Compliance + Provenance Assurance

- WS3 contract and traceability hardening.
- Compliance observability baseline.

### Phase 3 (Weeks 7–9): Contract & Ops Reliability

- WS4 and WS5 completion.
- OpenAPI parity lock + improved runbooks/alerts.

### Phase 4 (Weeks 10–12): Controlled Performance Enhancements

- WS6 profiling-driven optimization.
- Rollout through flags with rollback guardrails.

## Validation Plan

Use narrow-to-broad verification per change:

1. `pytest services/layer1-ingestion/tests/unit`
2. `pytest services/layer1-ingestion/tests/integration`
3. Layer 1 contract tests (including compatibility/deprecation suites)
4. `make test-layer1`
5. `make verify` before merge

## Risk Register (Top Items)

- **R1: Hidden contract drift** between route handlers and generated/openapi specs.
- **R2: Cross-tenant leakage risk** in less-used repository/query paths.
- **R3: Job duplication/retry amplification** under worker restarts.
- **R4: Compliance/provenance gaps** causing downstream evidence integrity issues.
- **R5: Optimization regressions** that improve speed but weaken crawl quality or auditability.

## Ownership Model

- **Layer 1 Ingestion Team**: runtime correctness, queueing, crawler/compliance.
- **Platform Contracts WG**: OpenAPI/contract drift prevention and CI gates.
- **SRE/Platform Ops**: observability, incident readiness, rollback posture.
- **Security/Governance**: tenant isolation and compliance assurance sign-off.

## Definition of Done (Roadmap Level)

Roadmap execution is complete when:

- P0 workstreams are fully delivered and covered by hostile + regression tests.
- Contract tests enforce Layer 1 API shape stability.
- Operational dashboards and runbooks cover critical ingestion incidents.
- Performance improvements are measured, reversible, and contract-safe.
