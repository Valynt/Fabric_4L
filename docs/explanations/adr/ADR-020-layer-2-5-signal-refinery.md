---
title: "ADR-020: Layer 2.5 Signal Refinery"
category: "explanations"
audience: "advanced"
last-reviewed: "2026-05-22"
freshness: "current"
related: [
  "../../core-concepts/value-signals",
  "../../reference/layer2-extraction-api",
  "../../reference/layer3-knowledge-api",
  "../why-knowledge-graph"
]
---

# ADR-020: Layer 2.5 Signal Refinery

**Status:** ✅ Accepted

**Date:** 2026-05-22

**Deciders:** Architecture Team, ML Engineering, Platform Engineering

---

## Context

Layer 2 produces raw, ontology-guided extractions. Layer 3 stores them as graph nodes. Layer 4 agents consume them for hypothesis generation, ROI modeling, and business-case synthesis. The gap between these layers created three problems:

1. **Raw extraction inconsistency** — L2 outputs vary in schema, confidence calibration, and type taxonomy across different extractors and domains.
2. **No trust scoring** — Downstream agents had no principled way to decide whether a signal was reliable enough to build a business case on.
3. **Lifecycle blindness** — Once extracted, signals sat in the graph with no formal state machine for review, validation, promotion, or deprecation.

We needed an explicit bridge layer that could:
- Normalize raw L2 outputs into a canonical signal model
- Compute a composite trust score from evidence quality, provenance, and lifecycle state
- Advance signals through a formal lifecycle (draft → extracted → validated → promoted → superseded)
- Push refined signals to L3 as graph nodes without blocking on L3 availability
- Serve as the single source of truth for agents querying "what do we know about this account?"

## Decision

We introduce **Layer 2.5: Signal Refinery** — a dedicated service (`layer2-5-signal-refinery`, port 8007) positioned between L2 Extraction and L3 Knowledge Graph.

```
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Extraction        Raw ontology-guided entities  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2.5: Signal Refinery                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Type Classification  → canonical ValueSignalType   │ │
│  │  Trust Scoring        → composite 0–1 score         │ │
│  │  Lifecycle State      → draft → extracted → ...     │ │
│  │  Evidence Provenance  → structured audit trail        │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Knowledge Graph   Neo4j signal nodes + links    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Agents          Hypothesis / ROI / Business   │
└─────────────────────────────────────────────────────────┘
```

### Trust Score Formula

```
trust_score = (
    0.40 * confidence
  + 0.30 * evidence_quality_score
  + 0.20 * provenance_weight
  + 0.10 * lifecycle_bonus
)
```

| Component | Source | Range |
|-----------|--------|-------|
| confidence | L2 extractor output | 0–1 |
| evidence_quality_score | mean(confidence * relevance) across evidence items | 0–1 |
| provenance_weight | human=1.0, ai=0.7, system=0.5 | discrete |
| lifecycle_bonus | validated=1.0, extracted=0.5, draft=0.0 | discrete |

### Lifecycle States

| State | Meaning | Who transitions |
|-------|---------|-----------------|
| draft | Initial placeholder or fallback | system |
| extracted | Passed through refinery | L2.5 service |
| validated | Human-reviewed and approved | reviewer via API |
| promoted | Linked to a value driver/hypothesis | agent or analyst |
| rejected | Reviewed and discarded | reviewer via API |
| superseded | Replaced by a newer signal | agent or system |
| expired | Time-bounded signal past TTL | system (planned) |

### Signal Type Mapping

Raw L2 types are normalized to canonical `ValueSignalType` values:

| Raw L2 Type | Canonical Type |
|-------------|---------------|
| pain_point, pain | pain |
| opportunity | opportunity |
| risk | risk |
| churn_risk, renewal_risk | renewal |
| expansion, upsell | expansion |
| cost_reduction, cost_saving | cost_saving |
| revenue, revenue_uplift | revenue_uplift |
| efficiency | efficiency |
| compliance | compliance |
| strategic, strategic_priority | strategic_priority |

## Consequences

### Positive
- ✅ **Canonical signal model** — All downstream layers consume `ValueSignal` from a single source of truth
- ✅ **Principled trust scoring** — Agents can threshold signals before building business cases
- ✅ **Auditability** — Every signal carries evidence items, provenance, and lifecycle history
- ✅ **Best-effort L3 integration** — L2.5 remains operational even if L3 is unavailable
- ✅ **Human-in-the-loop** — Formal review gate before signals are used for high-stakes recommendations

### Negative
- ❌ **Additional service** — Adds operational complexity (port 8007, separate DB, migrations)
- ❌ **Cross-service consistency** — Signal state can diverge between L2.5 PostgreSQL and L3 Neo4j
- ❌ **Latency** — Refinement step adds processing time before signals are queryable

### Neutral
- 🔄 **Schema evolution** — `ValueSignal` in `packages/shared` must remain backward-compatible
- 🔄 **Graph sync** — L3 signal nodes are eventually consistent, not transactional

## Implementation

### Service Structure

```
services/layer2-5-signal-refinery/
  src/layer2_5_signal_refinery/
    api/routes/signals.py      # REST API (port 8007)
    services/signal_refinery.py # Core scoring & classification
    clients/l3_graph_client.py  # Best-effort L3 push
    repositories/signal_repository.py # PostgreSQL persistence
    models/                      # SQLAlchemy models
    database.py                  # RLS-enabled session
    config.py                    # Settings (layer3_base_url, etc.)
  migrations/                    # Alembic migrations
  tests/                         # Unit & integration tests
```

### Key API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/signals` | Create a ValueSignal |
| GET | `/api/v1/signals` | List signals for account |
| GET | `/api/v1/signals/{signal_id}` | Get single signal |
| PATCH | `/api/v1/signals/{signal_id}` | Partial update |
| DELETE | `/api/v1/signals/{signal_id}` | Soft-delete |
| POST | `/api/v1/signals/{signal_id}/review` | Human review |
| POST | `/api/v1/signals/{signal_id}/promote` | Promote to hypothesis |
| POST | `/api/v1/signals/refine` | Batch refinement from L2 output |

### L3 Push Behavior

- After create/refine, L2.5 pushes the signal to L3 via `POST /api/v1/graph/signals`
- Push is **best-effort, non-blocking** — created via `asyncio.create_task()`
- L2.5 remains fully operational if L3 is down
- L3 persists signals as Neo4j nodes with `MERGE` on `(id, tenant_id)` for idempotency

### Layer 4 Integration

Agents access signals via `signal_tools.py` in Layer 4:
- `get_account_signals()` — Query validated/promoted signals for an account
- `create_signal()` — Emit agent-discovered signals with evidence and provenance

Both tools enforce tenant isolation via `X-Tenant-ID` headers and emit audit events.

## Validation

```bash
# Run L2.5 tests
make test-layer2-5

# Verify trust score computation
python -m pytest services/layer2-5-signal-refinery/tests/test_signal_refinery.py -v

# Verify L3 push resilience (L2.5 should survive L3 being down)
python -m pytest services/layer2-5-signal-refinery/tests/test_l3_client.py -v
```

## Alternatives Considered

### Inline refinement in L2
- **Pros:** Fewer services, simpler pipeline
- **Cons:** Would couple extraction scoring to extractor-specific code; L2 shouldn't know about lifecycle or trust thresholds
- **Why rejected:** Separation of concerns — L2 extracts, L2.5 scores and governs

### Store raw signals directly in L3 and refine on read
- **Pros:** No extra persistence layer
- **Cons:** Trust scores would be recomputed on every read; no place to store lifecycle state or review history
- **Why rejected:** Need durable state machine and human review queue

### Add scoring to L4 agents
- **Pros:** Close to consumer
- **Cons:** Every agent would reimplement scoring; no shared lifecycle or review pipeline
- **Why rejected:** Centralize governance, not distribute it

## Related

- [Value Signal Model](../../../packages/shared/src/value_fabric/shared/models/value_signal.py) — Canonical Pydantic model
- [L2 Extraction API](../../reference/layer2-extraction-api.md) — Raw extraction output format
- [L3 Knowledge Graph API](../../reference/layer3-knowledge-api.md) — Signal persistence endpoint
- [Signal Tools](../../../services/layer4-agents/src/layer4_agents/tools/signal_tools.py) — Layer 4 consumption

---

*Last updated: 2026-05-22 | Status: Accepted*
