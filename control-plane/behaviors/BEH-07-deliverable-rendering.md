# BEH-07: Deliverable rendering (CFO / Executive / Technical)

```yaml
id: BEH-07
name: deliverable-rendering
journey_stage: J-9            # audience views rendered from the reviewed version
stories: [VP-11, VP-12, VP-14]
closes_gaps: [GAP-07, GAP-08]
rules: [R-1, R-4, R-7, R-8]
boundary: web -> api -> L4
components:
  - CFOView
  - ExecutiveView
  - TechnicalView
  - DocumentAssembler          # assemble_document / generate_section / document_export manifests
  - ValueCasesRouter           # supplies the exact version to render
primary_gates: [AG-02, AG-03]
```

## Product

**One model, three audience views.** The CFO needs auditable cash flows, ROI/NPV/IRR/payback, sensitivity, assumptions, and confidence; the executive approver needs a concise outcome, investment, expected range, risks, evidence, and recommendation; the technical evaluator needs implementation and integration truth (personas §4; S2 stage 6: "the tell — stakeholder-tailored business cases").

Correct behavior, normatively:
- All three views render from the **same immutable value-case version** — same model version, same ROI snapshot, same evidence set. Views may select and emphasize; they MUST NOT present contradictory numbers, claims, field names, or version identities (domain-chain rule §5.1; R-7).
- View-specific framing never recomputes: numbers come from the deterministic snapshot (R-4). Any number differing between views is a defect.
- Source classification and fallback labels survive rendering: synthetic, benchmark-derived, fallback, and demo inputs remain visibly labeled in every view and export (R-5); unverified claims and defaults stay visible (§5.4).
- Every quantitative claim in every view exposes its provenance path (R-8): claim → calculation → formula → assumptions → driver → signal/evidence → original source.
- Audience selection is a rendering choice over one case record — not three separate documents with divergent lifecycle (closes GAP-07); each rendered view retains the typed identifier set of its source version (GAP-08).

## Architecture

```
                 one immutable value-case version
                 (model v + ROI snapshot + evidence IDs + approval)
                              │
        ┌─────────────────────┼──────────────────────┐
        ▼                     ▼                      ▼
 ┌──────────────┐     ┌────────────────┐     ┌──────────────────┐
 │ CFOView.tsx   │     │ ExecutiveView  │     │ TechnicalView.tsx │
 │ cash flows,   │     │ .tsx           │     │ architecture,     │
 │ ROI/NPV/IRR,  │     │ outcome, range │     │ integration,      │
 │ sensitivity,  │     │ risks, recom-  │     │ feasibility,      │
 │ assumptions   │     │ mendation      │     │ technical evidence│
 └──────────────┘     └────────────────┘     └──────────────────┘
        renderers only — no recomputation, no divergent records
 assembly/export contracts: contracts/tool-manifests/
   assemble_document.json, generate_section.json, document_export.json
```

Rendering is a pure function of the version + audience. Export (BEH-08) packages the exact rendered views of the approved version.

## Implementation

### Verified anchors

| Path | What it is | Role in this behavior |
|---|---|---|
| `apps/web/src/pages/deliverables/CFOView.tsx` | CFO deliverable view | Financial depth: cash flows, ROI/NPV/IRR/payback, sensitivity, assumptions, confidence |
| `apps/web/src/pages/deliverables/ExecutiveView.tsx` | Executive deliverable view | Decision summary: outcome, investment, range, risks, evidence, recommendation |
| `apps/web/src/pages/deliverables/TechnicalView.tsx` | Technical deliverable view | Technical credibility: architecture, integration, feasibility evidence |
| `services/api/app/routers/value_cases.py` | Value cases router | Serves the exact version + snapshot to all three views |
| `contracts/tool-manifests/assemble_document.json` | Tool manifest | Document assembly contract from a version |
| `contracts/tool-manifests/generate_section.json` | Tool manifest | Section generation contract (audience-scoped) |
| `contracts/tool-manifests/document_export.json` | Tool manifest | Export contract binding artifact to version |

Open anchor: which backend service executes document assembly is **not verified** (repo_map: only the tool manifests are confirmed; likely L4). Cards cite the manifests; the owning service anchor is filled when verified.

### Inputs / outputs
- **In**: immutable value-case version reference (model version + ROI snapshot + evidence/claim/assumption IDs), audience selection.
- **Out**: rendered view(s) with labeled sources, provenance links, and version identity displayed; render events traceable to the version.

### State transitions
- Views inherit the case version's Lifecycle state; a view of a `draft` is labeled draft; only `approved`/`published` versions are exportable (handoff to BEH-08).
- Content: `stale` upstream inputs mark all three views stale simultaneously — they share one version.
- Access: `denied`/`expired` renders nothing protected, in every view equally (R-6).

### Failure modes
- Missing version reference or unreadable snapshot → render fails closed; no partial deliverable from loose context (R-6).
- Numeric divergence between views → contract/consistency test failure; single snapshot is the only number source (R-4).
- Label stripping (a benchmark/default/AI-suggested value rendered as fact) → defect class blocked by tests (R-1, R-5).
- Assembly provider degradation → view renders deterministic sections and names the degraded enrichment; material degradation blocks publication (§7.3.5).

## Verification

**Tests**
- Unit/component: each view renders from the injected version fixture; provenance links present per material claim; label rendering for every source class.
- Cross-view consistency: property-style tests assert identical financial figures across CFO/Executive/Technical renders of one version (R-4).
- Contract: `assemble_document.json` / `generate_section.json` / `document_export.json` manifest conformance; version-binding fields mandatory (GAP-08).
- Browser: journey across all three views of one approved case; accessibility (chart summaries, data-table alternatives, no color-only semantics, WCAG 2.2 AA).

**Tenant-isolation assertions**
- Views render only after the case version passes tenant/account/case scope checks; foreign version IDs denied before any content load.
- Rendered artifacts and cached renders keyed by tenant; no cross-tenant cache reuse.

**Release gates**
- **AG-02 code-quality-and-tests** — component tests for the three views; cross-view consistency tests; accessibility checks in browser lane.
- **AG-03 contract-compliance** — assembly/export manifest conformance; version-binding schema enforcement.
- **AG-05 tenant-isolation-and-behavior** — fail-closed frontend authorization tests; cache isolation for rendered content.

**Required evidence**
- EV: junit-and-json test-run evidence for view and consistency suites.
- EV: Playwright traces + accessibility scan output for the three-view journey.
- EV: contract-test results for assembly/export manifests.
