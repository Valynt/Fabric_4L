# 07 — Engineering, Governance, and Data Contract

Source: Master Product Intent §7, §10 (S1).

## Canonical service responsibility

| Capability | Required authority | Contract boundary |
|---|---|---|
| Authorization | Backend authorization snapshot and authenticated request context | Frontend claims bootstrap identity only; backend scope authoritative and fail-closed (R-6) |
| Ingestion and extraction | L1 and L2 workflows | Persist source, extraction, provenance, run status, tenant scope before downstream use |
| Knowledge graph and evidence search | L3 | Own tenant-scoped graph retrieval, deterministic ROI calculation, evidence search, calculation persistence |
| Workflow orchestration | L4 | Coordinate durable jobs, human interrupts, retries, truth gates, narrative generation, assembly; do not redefine L3 math (R-4) |
| Truth and claim governance | L5 | Own validated and disputed truth state, source references, corroboration policy, publication readiness |
| Benchmarks | L6 | Own benchmark identity, definition, applicability, date, geography, sample, source provenance |
| Value-case lifecycle | One canonical case service and record identity | Unify Studio, narrative, governed business case, approval, publication, export, deliverables |
| Frontend | Typed domain view models over canonical APIs | Present, edit, disposition server state; browser storage is not authoritative domain persistence (R-2) |

## Version and provenance invariants

1. A model version identifies the complete tree, variables, formulas, units, assumptions, evidence links, benchmark links, and source freshness used for calculation.
2. A calculation version identifies the exact model version, selected scenario, cash-flow policy, engine version, substituted formulas, request, outputs, warnings, and trace.
3. A narrative version identifies the exact model, calculation, evidence, stakeholder, source-freshness, and prompt or generation configuration snapshot.
4. An approval identifies the exact narrative and all upstream versions plus actor, role, rationale, timestamp, and content hash.
5. A published or exported artifact references the approval, immutable case version, object-storage identity, provenance manifest, and audit event.
6. A change to any upstream material input marks dependent drafts stale and requires the applicable recalculation or re-review. It never mutates approved history (R-7).

## Evidence and fallback policy

1. Evidence requirements are explicit policy, not optional custom input. Required source count, confidence, freshness, applicability, and dispute status participate in the actual pass expression.
2. Semantic search results are candidates, not truth. Promotion to truth requires the configured human or automated validation policy and preserves source passages.
3. Customer-provided, observed, benchmark, derived, AI-suggested, default, mock, and seeded data remain distinct source classes across the full lifecycle (R-1, R-5).
4. Production may use a default only through an explicit, authorized assumption workflow (user sees the default, reason, downstream impact, publication rule).
5. An LLM or provider failure may degrade narrative enrichment but cannot change deterministic financial outputs (R-4); degradation is visible and may require human review or block publication (R-5).
6. Best-effort synchronization cannot be the only persistence path for evidence, truth, model, calculation, approval, or publication state (R-2).

## API and persistence requirements

1. One versioned schema per command and result; frontend types generated from or contract-tested against the service schema.
2. Generate endpoints run the promised workflow or are renamed to Create or Persist; a route never accepts a completed object while implying it generated it.
3. All material commands are idempotent and return stable case, run, model, artifact, and version IDs.
4. All object reads/writes verify authenticated tenant, permitted account scope, parent-case ownership; tenant scope participates in relational keys and uniqueness where needed (R-6).
5. Server persistence authoritative for cases, workspace state, decisions, scenarios, models, calculations, narratives, reviews, approvals, publication; browser persistence limited to safe caches and presentation preferences (R-2).
6. Concurrent edits use optimistic version checks; a conflict returns both version identities and never overwrites silently.
7. Exports created only from approved immutable versions, stored under tenant-prefixed object paths with provenance and audit records (R-7, R-8).

## Nonfunctional requirements

| Area | Release requirement |
|---|---|
| Security and tenancy | Fail closed on absent/malformed/expired/conflicting/mismatched authorization; prove tenant, account, case, graph, cache, database, object-storage isolation with hostile tests (R-6) |
| Reliability | Durable background workflows resume after interruption, avoid duplicate side effects, preserve last valid version |
| Performance | Workspace reads, saves, deterministic calculations target p95 < 2s; async generation acknowledged < 1s with visible stage progress |
| Availability and durability | Persisted case read/write/deterministic-calculation paths target 99.9% monthly availability; models and cases survive reload, deployment, restart |
| Determinism | Financial calculations reproducible from stored inputs, formulas, policies, engine version; time, randomness, provider behavior do not change deterministic assertions (R-4) |
| Observability | Metrics, logs, traces, audit events, job state, fallback tier, error classification, customer-facing eligibility correlated by tenant-safe identifiers |
| Accessibility | WCAG 2.2 AA, keyboard-complete operation, meaningful focus, accessible status announcements, chart summaries, no color-only meaning |
| Privacy | Protected account content minimized, role-scoped, auditable, omitted from denied/expired/cross-tenant/support surfaces unless explicitly authorized |
| Compatibility | Canonical routes preserve tenant and account context; supported browsers and responsive layouts retain all security, review, and gate semantics |

## Engineering source anchors

Named anchors (§10 of source; "engineering anchors, not alternate product requirements"). Resolved paths live in `control-plane/behaviors/` cards and the repo map.

1. Pinned repository baseline (commit `76f21bdc2fc277d0fdddf546c32ac75a5ded7e42`, repo `bmsull560/Fabric_4L`)
2. Frontend tenant and account route spine
3. Prospect setup adapter
4. Workspace case and tab persistence hooks
5. Layer 4 workspace generation
6. Hypothesis generation, ranking, promotion, and conversion
7. Value Model UI calculation handoff
8. Frontend ROI contract
9. Layer 3 ROI route contract
10. Layer 3 deterministic ROI calculations
11. Layer 4 governed ROI workflow
12. Modern web value-case journey
13. Governed business-case workflow
14. Canonical workflow configuration
15. Release golden-path manifest

## Change governance

1. A change to the master intent requires a decision record naming the user outcome, affected story IDs, data and API impact, design-state impact, security and evidence impact, migration plan, and release-proof impact.
2. A code change that exposes an unresolved deviation must reference a gap ID (GAP-xx), owner, severity, containment, and target disposition.
3. A story (VP-xx) may be split for delivery, but no slice may weaken tenant isolation, provenance, deterministic calculation, human approval, immutability, or publication gates.
4. The repository's candidate-build certification and generated product documentation must reference the same version of this contract.
