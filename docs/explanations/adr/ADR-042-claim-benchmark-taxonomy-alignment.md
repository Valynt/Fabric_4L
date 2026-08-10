<!-- ADR-042: Claim Type and Benchmark Taxonomy Alignment -->

# ADR-042: Claim Type and Benchmark Taxonomy Alignment

**Status:** Accepted
**Date:** 2026-07-29
**Deciders:** Platform Architecture Committee, Layer 4 Engineering, Layer 5 Engineering, Layer 6 Engineering
**Reviewers:** Agent Engineering, Value Engineering

---

## Context

The Fabric_4L platform has **three divergent claim/benchmark taxonomies** (A-09, A-10, High):

| Layer / Component | Taxonomy Source | Values |
|-------------------|-----------------|--------|
| **Layer 4 Ground Truth Client** (`layer5_client.py:283`) | Docstring / API contract | `capability`, `outcome`, `metric`, `benchmark`, `roi_assumption`, `competitive` |
| **Layer 5 TruthObject** (`truth_object.py:101-114`) | `ClaimType` enum (DB + API) | `cost_savings_baseline`, `revenue_impact`, `efficiency_gain`, `risk_reduction`, `compliance_requirement`, `customer_outcome`, `technical_capability`, `market_benchmark`, `persona_pain_point`, `value_driver_metric`, `other` |
| **Layer 6 Benchmark Datasets** (`layer6_benchmarks/models/benchmark_dataset.py`) | Seed datasets + `BenchmarkMetric` | Industry-specific metrics (e.g., Manufacturing: `oee`, `defect_rate`; SaaS: `arr_growth`, `net_dollar_retention`) |

**Consequences of divergence:**
- L4 `submit_truth(claim_type="outcome")` → L5 returns **422 validation error** (unknown claim type)
- L4 workflows that promote claims to Ground Truth **fail silently** (L5 client catches all exceptions, returns error dict — business case continues "ungrounded")
- L4 → L6 benchmark comparison uses L6 metric names; no mapping to L4 claim types or L5 `ClaimType`
- A committed June 2026 runtime report independently recorded **422 responses for L4 claim types** and a local bypass of the truth gate
- Without alignment, **evidence integrity is optional** — business cases can "succeed" without validated Ground Truth

---

## Decision

### 1. Single Canonical Claim Taxonomy

**Layer 5 `ClaimType` enum is the system of record.** All layers must use these values:

```python
# Canonical claim types (from Layer 5 ClaimType enum)
CLAIM_TYPES = [
    "cost_savings_baseline",     # Baseline cost reduction claim
    "revenue_impact",            # Revenue increase / uplift claim
    "efficiency_gain",           # Time / resource efficiency improvement
    "risk_reduction",            # Risk mitigation / compliance risk reduction
    "compliance_requirement",    # Regulatory / compliance-driven claim
    "customer_outcome",          # Customer-facing outcome / satisfaction
    "technical_capability",      # Technical capability / feature delivery
    "market_benchmark",          # Peer / market comparison claim
    "persona_pain_point",        # Persona-specific pain / friction
    "value_driver_metric",       # KPI / metric that drives value
    "other",                     # Fallback for unclassified claims
]
```

**Layer 4 MUST map its internal claim types to canonical types** before calling L5.

### 2. L4 → L5 Claim Type Mapping

| L4 Internal (Legacy) | Canonical L5 ClaimType | Rationale |
|----------------------|------------------------|-----------|
| `capability` | `technical_capability` | Direct semantic match |
| `outcome` | `customer_outcome` | Business outcome → customer outcome |
| `metric` | `value_driver_metric` | Metric that drives value |
| `benchmark` | `market_benchmark` | Peer/market comparison |
| `roi_assumption` | `cost_savings_baseline` OR `revenue_impact` | ROI assumption maps to primary value lever; default to cost savings |
| `competitive` | `market_benchmark` | Competitive intel = market benchmark |

**Implementation:** Add `_map_claim_type_to_l5()` in `Layer5GroundTruthClient.submit_truth()`.

### 3. Benchmark Metric ↔ Claim Type Linkage

Layer 6 benchmark comparisons must be **traceable to the claim types they validate**.

**Rule:** Every `ComparisonResult` returned by L6 must include the `claim_type` it supports.

```python
# Extended ComparisonResult (add claim_type field)
class ComparisonResult(BaseModel):
    percentile: float
    peer_median: Decimal
    peer_range: tuple[Decimal, Decimal]
    sample_size: int
    confidence: float
    claim_type: str  # NEW — canonical L5 ClaimType this benchmark validates
```

**Seed Dataset Tagging:** All 4 seed datasets (Manufacturing, SaaS, Healthcare, Financial Services) must tag each `BenchmarkMetric` with applicable `claim_type(s)`:

```python
# Example: Manufacturing seed dataset
BenchmarkMetric(
    name="oee",
    display_name="Overall Equipment Effectiveness",
    unit="percentage",
    claim_types=["efficiency_gain", "cost_savings_baseline"],  # NEW
    ...
)
BenchmarkMetric(
    name="defect_rate",
    display_name="Defect Rate",
    unit="ppm",
    claim_types=["risk_reduction", "efficiency_gain"],  # NEW
    ...
)
```

### 4. L4 Workflow → Benchmark Integration (Wiring A-10)

The `HTTPBenchmarkClient` adapter exists but is **not injected into any workflow**. 

**Decision:** Wire benchmark validation into the **Business Case Generator** workflow:

1. **Hypothesis Generation** → produces candidate claims with `claim_type`
2. **Claim Promotion** → for each claim with numeric `value`, call L6 `validate_range()` using dataset/metric mapped from `claim_type`
3. **Benchmark Comparison** → call L6 `compare()` for peer percentile
4. **Truth Submission** → `submit_truth()` with `claim_type` + `benchmark_evidence` (comparison result)
5. **Business Case Assembly** → includes `grounding_status` per claim: `grounded` | `partially_grounded` | `ungrounded` | `benchmark_failed`

### 5. Grounding Status — Mandatory on All Value Artifacts

Every final value artifact (Business Case, ROI Calculation, Value Case) **must expose**:

```python
class GroundingStatus(str, Enum):
    GROUNDED = "grounded"                    # All claims VALIDATED + benchmarked
    PARTIALLY_GROUNDED = "partially_grounded"  # Some claims validated, some pending
    UNGROUNDED = "ungrounded"                # No claims validated
    VALIDATION_FAILED = "validation_failed"    # L5 validation returned error
    BENCHMARK_FAILED = "benchmark_failed"      # L6 comparison failed
    EVIDENCE_SERVICE_UNAVAILABLE = "evidence_service_unavailable"  # L5/L6 down
```

**Gateway read models** and **frontend hooks** must render this status prominently. A business case with `UNGROUNDED` or `VALIDATION_FAILED` must **not** be presentable as "certified" or "evidence-backed".

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Make L4 claim types canonical; extend L5 enum | L5 enum is more granular (11 vs 6), business-aligned, and already in DB/migrations |
| Deprecate L5 enum; use free-text claim_type | Loses validation, analytics, maturity ladder per type, UI filtering |
| Keep both; translate at gateway | Gateway shouldn't own domain taxonomy; L4→L5 is the natural boundary |
| Add L4 claim types to L5 enum (bidirectional) | L4 types are vague (`metric`, `outcome`); L5 types are precise and auditable |

---

## Consequences

### Positive
- **Zero 422s on truth submission** — L4 maps to valid L5 enum
- **Traceable evidence chain** — claim → truth object → benchmark → business case
- **Mandatory grounding status** — no silent "success" without evidence
- **Benchmark participation auditable** — every value case shows which benchmarks validated which claims
- **Industry extensibility** — packs can add `claim_type` tags to benchmark metrics

### Negative
- **L4 migration** — all workflows calling `submit_truth()` must pass mapped `claim_type`
- **L6 seed dataset update** — 4 datasets × ~10 metrics each need `claim_types` tagging
- **Workflow wiring** — Business Case Generator must be updated to call L6 and include results

---

## Compliance and Migration

### Migration Owner
Layer 4 Engineering + Layer 5 Engineering + Layer 6 Engineering

### Phased Plan

| Phase | Action | Target |
|-------|--------|--------|
| **0** | Add `claim_type` to `ComparisonResult`; tag L6 seed metrics | 2026-08-05 |
| **1** | Implement `_map_claim_type_to_l5()` in `Layer5GroundTruthClient` | 2026-08-05 |
| **2** | Wire `HTTPBenchmarkClient` into Business Case Generator workflow | 2026-08-12 |
| **3** | Add `grounding_status` to Business Case / Value Case / ROI response models | 2026-08-12 |
| **4** | Update golden path test: submit claim → L5 VALIDATED → L6 benchmarked → case.grounded | 2026-08-19 |
| **5** | Remove L4 legacy claim type docstrings; add deprecation warnings | 2026-08-26 |

### Enforcement Mechanism
- **Contract test:** `test_l4_l5_claim_type_mapping` — every L4 internal type maps to valid L5 enum
- **Contract test:** `test_l6_metrics_have_claim_types` — every seed `BenchmarkMetric` has `claim_types` list
- **Integration test:** Business Case Generator produces `grounding_status` for each claim
- **CI gate:** `mandatory-security-regression` includes grounding status verification

### Rollback Strategy
- L4 mapping is pure function — feature flag `USE_CANONICAL_CLAIM_TYPES` toggles it
- L6 `claim_type` field is additive — ignored by older clients
- Grounding status is new field — optional in response, default `UNGROUNDED`

---

## Related Decisions
- ADR-039: Canonical Public API Shape (gateway delegates to L4/L5/L6)
- ADR-040: Data Ownership and System of Record (L5 owns TruthObject)
- ADR-041: Canonical Layer 1 Ingestion Path (source → extraction → truth)
- ADR-019: Replayability, Event Envelope (claim promotion events)
- ADR-031: Agent Output Ratification (structured outputs with grounding)

---

## Evidence Required to Transition to Accepted
- [x] ADR authored and reviewed
- [ ] Phase 0: L6 `ComparisonResult.claim_type` + seed metric tagging (PR merged)
- [ ] Phase 1: L4→L5 claim type mapping in `Layer5GroundTruthClient` (PR merged)
- [ ] Phase 2: Benchmark client wired in Business Case Generator (PR merged)
- [ ] Phase 3: `grounding_status` on all value artifact responses (PR merged)
- [ ] Phase 4: Golden path test passes end-to-end (CI green)
- [ ] Phase 5: Legacy claim type docstrings deprecated (PR merged)

---

**Last Updated:** 2026-07-29