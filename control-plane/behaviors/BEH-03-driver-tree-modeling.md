# BEH-03: Driver tree modeling

```yaml
id: BEH-03
name: driver-tree-modeling
journey_stage: J-5            # Materialize the driver tree
stories: [VP-07, VP-14]
closes_gaps: [GAP-03, GAP-05]
rules: [R-2, R-8]
boundary: web -> api -> L3
components:
  - DriverTreePage
  - ValueTreeExplorer
  - GraphExplorer
  - DriversRouter
  - DriverGraphService         # L3 graph authority
  - ModelSchema                # canonical model schema (one schema, no valueLines fork)
primary_gates: [AG-03, AG-05]
```

## Product

Accepted hypotheses become one persistent, navigable driver tree: outcomes → drivers → levers → variables, with evidence links and confidence, forming a single coherent model (VP-07; journey exit: "every financial lever has a governed formula or explicit non-financial classification").

Correct behavior, normatively:
- The persistent driver/lever/variable/formula/evidence graph **is** the canonical model; a UI value line is a view model, not a second domain model (convergence decision 2; closes the `value_models` vs `valueLines` divergence in GAP-03).
- Graph and API return the **same stable IDs and version** (VP-07 eng).
- Every Value Driver is a persistent graph object linked to its source hypothesis, signal, evidence, confidence, and model version (domain lifecycle §5.2) — provenance path intact (R-8).
- Every financial driver carries an executable formula and variables, or is explicitly classified non-financial, **before** calculation can consume it (closes GAP-05).
- The tree is server-persisted, tenant/account/case-scoped, versioned, recoverable (R-2); the UI shows a synchronized details panel and downstream-impact preview.

## Architecture

```
 apps/web                        services/api              layer3-knowledge
 ┌───────────────────────┐       ┌───────────────────┐     ┌──────────────────────┐
 │ drivers/               │       │ routers/drivers.py │     │ src/graph/            │
 │  DriverTreePage.tsx    │──────▶│  (tree CRUD,       │────▶│  tenant-scoped graph: │
 │ ValueTreeExplorer.tsx  │       │   stable IDs,      │     │  nodes = outcome/     │
 │ GraphExplorer.tsx      │◀──────│   version)         │     │  driver/lever/variable│
 └───────────────────────┘       └───────────────────┘     │  edges = lineage to   │
        same IDs, same version ───────────────▶           │  hypothesis/signal/   │
        (contract-tested)                                 │  evidence             │
                                                          └──────────────────────┘
```

L3 owns graph persistence and traversal; `services/api` is the typed boundary; the frontend renders domain view models, not raw DTOs. Tool contract `contracts/tool-manifests/graph_traverse.json` governs agent-side traversal.

## Implementation

### Verified anchors

| Path | What it is | Role in this behavior |
|---|---|---|
| `apps/web/src/pages/drivers/DriverTreePage.tsx` | Driver tree page (+ its test) | Primary modeling surface: tree navigation, details panel, financial vs strategic distinction |
| `apps/web/src/pages/ValueTreeExplorer.tsx` | Value tree explorer | Alternate navigable view of the same canonical tree |
| `apps/web/src/pages/GraphExplorer.tsx` | Graph explorer | Inspection of underlying graph objects and lineage |
| `services/api/app/routers/drivers.py` | Drivers router | Tree/lever CRUD; stable IDs; version; scope enforcement |
| `services/layer3-knowledge/src/graph/` | L3 graph package | Canonical model persistence, tenant-scoped traversal, constraints |
| `services/layer3-knowledge/src/api/main.py` | L3 API entry | Graph/retrieval routes consumed via the gateway |
| `contracts/tool-manifests/graph_traverse.json` | Tool manifest | Governed agent traversal contract over the same graph |
| `contracts/openapi/layer3-knowledge.json` | Per-layer OpenAPI spec | L3 contract surface for schema/conformance tests |
| `contracts/jsonschema/layer3-entity-resolution-contract.json` | JSON Schema | Entity identity semantics for graph objects |

### Inputs / outputs
- **In**: promoted hypotheses (BEH-02) with lineage; driver/lever/variable edits with units, time basis, bounds.
- **Out**: persistent tree + model IDs, model version, evidence links; per-lever classification: governed formula **or** explicit non-financial (J-5 exit gate).

### State transitions
- Model: `draft` lineage from promoted hypotheses; each structural edit produces a new model version (never mutates versions referenced downstream).
- Lever classification: `unclassified -> financial (formula valid) | non-financial (explicit)`; calculation eligibility only from a resolved classification.
- Synchronization: `synced | dirty | conflict`; concurrent tree edits use optimistic version checks.
- Content: `loading | empty | ready | degraded | stale | error`; a material upstream change marks the tree `stale` for dependent drafts.

### Failure modes
- Calculation requested with a financial driver lacking a valid formula → blocked with direct fix (GAP-05 fail-closed; not a silent estimate).
- Schema divergence (`valueLines`-style payload) → rejected at the adapter boundary; one canonical schema only.
- Concurrent structural edit → conflict with both version identities; offer compare / reload / save-as-new-version; never silent overwrite.
- Graph write partially fails → reconciliation path; no half-linked driver visible as ready.
- Cross-tenant node reference → rejected before business logic (R-6).

## Verification

**Tests**
- Unit: tree invariants (single root per case, acyclicity, classification gate), version increments, conflict handling.
- Contract: graph-vs-API ID/version parity; `graph_traverse.json` manifest conformance; L3 OpenAPI conformance (controls under AG-03).
- Integration (real Neo4j + PostgreSQL): persistence round-trip, duplicate-relationship and replay handling, reconciliation after partial write failure (S2 L3 coverage areas).
- Browser: build/edit tree, downstream-impact preview, financial-vs-strategic labeling, keyboard navigation.

**Tenant-isolation assertions**
- Tenant-scoped Cypher on every traversal; hostile tests with foreign graph nodes confirm zero cross-tenant reads/writes/inference (Neo4j isolation under AG-05).
- Foreign driver/lever IDs in API calls denied; existence not leaked via errors or caches.

**Release gates**
- **AG-03 contract-compliance** — canonical model schema; L1–L6 cross-layer contract tests; database schema contract validation.
- **AG-05 tenant-isolation-and-behavior** — Neo4j tenant isolation, cache isolation for tree reads, account-scope enforcement.
- **AG-02 code-quality-and-tests** — unit/integration coverage of tree invariants and classification gate.

**Required evidence**
- EV: junit-and-json test-run evidence for tree invariant and integration suites.
- EV: contract-test results proving graph/API ID and version parity.
- EV: hostile-tenancy suite output (two seeded tenants, foreign graph nodes) bound to candidate SHA.
