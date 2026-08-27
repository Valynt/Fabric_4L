# BEH-05: Evidence & cost binding

```yaml
id: BEH-05
name: evidence-and-cost-binding
journey_stage: J-6            # Define variables, evidence, and scenarios
stories: [VP-08, VP-09, VP-14]
closes_gaps: [GAP-08, GAP-10]
rules: [R-1, R-5, R-8]
boundary: web -> api -> L5 (+ L6 benchmarks)
components:
  - SolutionCostTab
  - AlternativesTab
  - GovernanceEvidencePage
  - TargetsAdmin
  - EvidenceRouter
  - ValueClaimService          # L5 claims + corroboration policy
  - BenchmarkService           # L6 governed benchmarks
primary_gates: [AG-02, AG-05]
```

## Product

A governance reviewer links evidence and benchmarks to specific claims, assumptions, and drivers so model support can be independently evaluated — and publication cannot happen without enforced evidence policy (VP-08; jobs 3; journey exit: "required inputs and evidence gates resolved or explicitly blocked").

Correct behavior, normatively:
- Every customer-facing statement and number is classified: verified fact, human-approved inference, external benchmark, explicit assumption, or deterministic calculation (R-1). Source classes — customer-provided, observed, benchmark, derived, AI-suggested, default, mock, seeded — stay distinct across the full lifecycle (§7.3.3).
- Evidence requirements are **explicit, mandatory policy**, not caller-supplied custom input; required source count, confidence, freshness, applicability, and dispute status participate in the actual pass expression — corroboration counts are enforced, not just reported (closes GAP-10).
- Semantic search results are candidates, not truth; promotion requires the configured validation policy and preserves source passages (§7.3.2).
- Typed upstream identifiers (evidence IDs, claim IDs, assumption IDs, ROI snapshot ID) persist through narrative, approval, publication, export, and provenance (closes GAP-08; R-8).
- Evidence sits beside the claim it supports, with source, applicability, freshness, and decision history visible; every quantitative claim exposes the full path **claim → calculation → formula → assumptions → driver → signal or evidence → original source** (R-8).
- Solution cost and alternatives/comparison are bound to the case as first-class evidence, not free text.

## Architecture

```
 apps/web                        services/api               layer services
 ┌────────────────────────┐      ┌────────────────────┐
 │ evidence/               │      │ routers/evidence.py │──▶ L5 ground truth:
 │  SolutionCostTab.tsx    │─────▶│ routers/benchmarks  │    value_claim_routes.py
 │  AlternativesTab.tsx    │      │     .py            │    (claims, corroboration,
 │ GovernanceEvidence.tsx  │◀─────└────────────────────┘    human decision, freshness)
 │ TargetsAdmin.tsx        │   evidence records                 │
 └────────────────────────┘                                    ▼
                                  claim ─▶ evidence ─▶ source  L6 benchmarks:
                                  (typed IDs preserved          identity, applicability,
                                   end to end, R-8)              date, geography, sample
```

L5 owns validated/disputed truth state, source references, corroboration policy, and publication readiness. L6 owns benchmark identity and applicability. The gateway enforces scope on every evidence read/write.

## Implementation

### Verified anchors

| Path | What it is | Role in this behavior |
|---|---|---|
| `apps/web/src/pages/evidence/SolutionCostTab.tsx` | Solution cost tab | Cost-of-solution inputs bound to the case as classified evidence |
| `apps/web/src/pages/evidence/AlternativesTab.tsx` | Alternatives tab | Competitive/alternative comparison evidence |
| `apps/web/src/pages/GovernanceEvidence.tsx` | Governance evidence page | Reviewer surface: evidence state, provenance, freshness, decisions |
| `apps/web/src/pages/TargetsAdmin.tsx` | Targets/benchmarks admin (+ form/detail) | Benchmark definition and applicability administration |
| `services/api/app/routers/evidence.py` | Evidence router | Evidence search/link/decision commands; typed identifiers |
| `services/api/app/routers/benchmarks.py` | Benchmarks router | Benchmark retrieval with applicability and provenance |
| `services/layer5-ground-truth/src/layer5_ground_truth/api/value_claim_routes.py` | Value claim API | Claims, corroboration policy, truth promotion, dispute state |
| `services/layer5-ground-truth/src/layer5_ground_truth/api/governance_router.py` | Governance API | Publication-readiness evaluation against evidence policy |
| `services/layer5-ground-truth/src/layer5_ground_truth/api/router.py` | L5 API entry | Ground-truth route composition |
| `contracts/openapi/layer5-ground-truth.json` | L5 OpenAPI spec | Claim/evidence contract surface |
| `contracts/openapi/layer6-benchmarks.json` | L6 OpenAPI spec | Benchmark contract surface |
| `contracts/jsonschema/claim-types.v1.json` | Claim types schema | Canonical claim classification (R-1) |

### Inputs / outputs
- **In**: claims/assumptions/drivers needing support; candidate evidence from search; benchmark selections; human decisions; solution-cost and alternatives inputs.
- **Out**: versioned evidence records (status, freshness, relevance, scope, source reference, human decision); claim states (validated/disputed); deterministic policy evaluation result feeding publication gating; persisted typed identifier set (evidence/claim/assumption/snapshot IDs).

### State transitions
- Evidence: `candidate -> accepted | rejected | disputed`; freshness ages records to `stale` independent of acceptance (independent state dimensions §5.4).
- Claim: `unverified -> validated | disputed`; promotion only via configured policy with preserved passages.
- Policy gate: `unresolved -> passed | blocked`; pass expression is deterministic and configuration-controlled.
- Content: degraded sources named explicitly with publication impact (R-5).

### Failure modes
- Absent caller-supplied truth requirements → **policy applies anyway**; auto-pass on absence is prohibited (GAP-10 fail-closed).
- Insufficient corroboration → claim remains unvalidated; publication blocked with named blocker and direct fix.
- Stale or contradicted evidence → freshness state surfaced; dependent claims re-flagged; material degradation blocks publication (R-5).
- LLM/provider failure in evidence search → degraded visibly; candidates never auto-promoted to truth (R-3 handoff).
- Unlabeled default/benchmark input reaching a claim → rejected; source class is mandatory (R-1, R-5).

## Verification

**Tests**
- Unit: policy pass expression (source count, confidence, freshness, applicability, dispute status) incl. **negative tests** proving absent/weak inputs cannot pass (GAP-10).
- Contract: claim/evidence schemas (`claim-types.v1.json`, L5/L6 OpenAPI); typed identifier persistence round-trip (GAP-08).
- Integration (real persistence): evidence versioning, freshness aging, dispute propagation, human-decision audit history; best-effort sync is never the only persistence path (§7.3.6).
- Browser: evidence drawer beside claim; label visibility for benchmark/default/AI-suggested classes; blocked-publication checklist navigation.

**Tenant-isolation assertions**
- Evidence, claims, and benchmarks scoped to tenant + account + case; foreign evidence IDs cannot be linked or read (hostile suite under AG-05).
- Object-storage and retrieval isolation for source documents and passages; no existence leak via search results or errors.
- Truth-promotion decisions auditable per tenant; audit events never leak foreign data.

**Release gates**
- **AG-02 code-quality-and-tests** — unit/negative/integration coverage of the evidence policy engine.
- **AG-05 tenant-isolation-and-behavior** — vector/retrieval isolation, object-storage prefix isolation, export isolation on evidence surfaces.
- **AG-03 contract-compliance** — L5/L6 schema conformance; claim-type versioning.

**Required evidence**
- EV: junit-and-json test-run evidence for policy-engine suites including negative cases.
- EV: contract-test results for claim/evidence/benchmark schemas.
- EV: hostile-tenancy suite output for evidence and retrieval surfaces.
- EV: audit-event samples showing source class, decision, freshness per claim (runtime_observation, environment-bound).
