---
title: "ADR-025: Layer 2.5 Signal Refinery as Official Architecture Extension"
category: "explanations"
audience: "advanced"
last-reviewed: "2026-06-10"
freshness: "current"
related: [
  "./ADR-020-layer-2-5-signal-refinery",
  "./ADR-002-six-layer-architecture",
  "./ADR-005-ontology-guided-llm-extraction",
  "./ADR-021-layer-3-canonical-runtime-path"
]
---

# ADR-025: Layer 2.5 Signal Refinery as Official Architecture Extension

**Status:** ✅ Accepted — Architecture Extension Ratified

**Date:** 2026-06-10

**Deciders:** Architecture Team, Platform Engineering, ML Engineering, Product Engineering

**Supersedes:** ADR-020 (Layer 2.5 Signal Refinery) — ADR-020 introduced the concept; ADR-025 ratifies L2.5 as a permanent, governed architecture layer.

---

## Context

ADR-020 introduced Layer 2.5 (Signal Refinery) as an experimental bridge between L2 Extraction and L3 Knowledge Graph. After two sprints of production operation, the results are conclusive:

- **Signal quality** improved 34% (measured by downstream agent confidence scores).
- **Lifecycle coverage** reached 91% of active signals (up from 0%).
- **Human review throughput** increased 2.3x due to structured review queues.
- **Zero critical incidents** during L3 unavailability events (best-effort L3 push works as designed).

The Fabric_4L six-layer architecture (ADR-002) defines the macro stack, but L2.5 has proven essential enough to warrant formal recognition as an **architecture extension** — a service layer that sits between two canonical layers without violating the six-layer taxonomy.

## Decision

We ratify **Layer 2.5: Signal Refinery** as an official architecture extension, permanently positioned between Layer 2 (Extraction) and Layer 3 (Knowledge Graph).

### Architecture Extension Model

```
┌─────────────────────────────────────────────────────────────────┐
│  Canonical Layer 2: Extraction  (port 8002)                       │
│  Ontology-guided entity extraction, raw signal generation          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ★ Architecture Extension: Layer 2.5 — Signal Refinery          │
│  (port 8007)                                                      │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Type Normalization    → canonical ValueSignalType        │   │
│  │  Trust Score Engine    → composite 0–1 score              │   │
│  │  Lifecycle State Machine → draft → extracted → validated   │   │
│  │                           → promoted → superseded → expired│   │
│  │  Evidence Provenance   → structured audit trail           │   │
│  │  Cross-Layer Push      → best-effort L3 graph sync        │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Canonical Layer 3: Knowledge Graph  (port 8003)                  │
│  Neo4j signal nodes, relationships, graph queries                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Canonical Layer 4: Agents  (port 8004)                           │
│  Hypothesis generation, ROI modeling, business-case synthesis      │
└─────────────────────────────────────────────────────────────────┘
```

### Governance Rules for Architecture Extensions

1. **Extension, not replacement** — L2.5 does not replace L2 or L3; it refines the handoff between them.
2. **Best-effort downstream** — L2.5 must survive L3 unavailability (no hard dependency on downstream layers).
3. **Backward-compatible schema** — The `ValueSignal` model in `packages/shared` must maintain backward compatibility.
4. **Observable boundaries** — All cross-layer calls must emit structured telemetry (span, metric, audit log).
5. **Formal lifecycle** — Architecture extensions require ADR ratification (like this one) and bi-annual review.

### Canonical Runtime Path Update

Per ADR-021 (Layer 3 Canonical Runtime Path), the L2→L3 path now officially includes the L2.5 refinement step:

```
L2 raw output  →  L2.5 Signal Refinery  →  L3 Knowledge Graph  →  L4 Agents
      │                   │                       │                   │
   (port 8002)       (port 8007)             (port 8003)       (port 8004)
```

L4 agents querying "what do we know about this account?" receive `ValueSignal` objects from L2.5, not raw L2 extractions. This is the canonical data path.

### Service Registry Entry

| Property | Value |
|----------|-------|
| Service name | `layer2-5-signal-refinery` |
| Port | 8007 |
| Database | PostgreSQL (tenant-scoped, RLS-enabled) |
| Upstream | L2 Extraction (port 8002) |
| Downstream | L3 Knowledge Graph (port 8003) |
| Consumers | L4 Agents (port 8004) |
| OpenAPI spec | `contracts/openapi/layer2-5-signal-refinery.json` (exported from the live service) |
| CI gate | `contracts/openapi/layer2-5-signal-refinery.json` |

## Consequences

### Positive
- ✅ **Formal architecture status** — L2.5 is no longer experimental; it is a governed extension with SLAs and operational runbooks.
- ✅ **Investment confidence** — Teams can build on L2.5 APIs without fear of deprecation.
- ✅ **Extension pattern established** — Other layers (e.g., L5.5 for benchmark preprocessing) can follow this ratification model.
- ✅ **Contract consolidation** — The `layer2-5-signal-refinery` OpenAPI spec is now tracked in `contracts/openapi/` and validated by CI gates.

### Negative
- ❌ **Operational complexity** — One more service to deploy, monitor, and upgrade.
- ❌ **Cross-layer consistency risk** — Signal state can diverge between L2.5 PostgreSQL and L3 Neo4j (mitigated by automated reconciliation jobs).

### Neutral
- 🔄 **Bi-annual review** — The Architecture Team will review L2.5 necessity every 6 months (next review: 2026-12-10).
- 🔄 **Schema evolution** — `ValueSignal` remains in `packages/shared` with backward-compatibility guarantees.

## Implementation

### OpenAPI Spec Ingestion
The canonical L2.5 OpenAPI spec is generated from the live service by the platform exporter. There is no hand-maintained YAML source.
1. `scripts/export_openapi.py` runs the L2.5 app (`services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/api/main.py`) and writes the spec to `contracts/openapi/layer2-5-signal-refinery.json`
2. The committed spec is tracked by the CI drift gate (`.github/workflows/openapi-drift-check.yml`) — a `git diff` failure aborts the build
3. Kept in sync with code changes (enforced by CI diff check)
4. Regenerate with: `python scripts/export_openapi.py --single layer2-5-signal-refinery.json`

### CI Gate Update
The contract enforcement CI workflow must validate:
- `layer2-5-signal-refinery.json` exists and is valid OpenAPI 3.1.0
- All `required` arrays are present on request/response body schemas
- No breaking changes are introduced without version bump

## Validation

```bash
# Verify L2.5 spec is tracked in contracts
ls -la contracts/openapi/layer2-5-signal-refinery.json

# Regenerate the spec from the live app (canonical source)
python scripts/export_openapi.py --single layer2-5-signal-refinery.json

# Validate the committed spec is current (no drift)
git diff --exit-code -- contracts/openapi/layer2-5-signal-refinery.json

# Verify L2.5 service health
curl http://localhost:8007/ready

# Verify end-to-end signal flow
python -m pytest services/layer2-5-signal-refinery/tests/test_e2e_signal_flow.py -v
```

## Related

- [ADR-020: Layer 2.5 Signal Refinery (Original Concept)](./ADR-020-layer-2-5-signal-refinery.md) — Original introduction
- [ADR-002: Six-Layer Architecture](./ADR-002-six-layer-architecture.md) — Macro stack definition
- [ADR-005: Ontology-Guided LLM Extraction](./ADR-005-ontology-guided-llm-extraction.md) — L2 output format
- [ADR-021: Layer 3 Canonical Runtime Path](./ADR-021-layer-3-canonical-runtime-path.md) — L3 consumption contract
- [Value Signal Model](../../../packages/shared/src/value_fabric/shared/models/value_signal.py) — Canonical Pydantic model

---

*Last updated: 2026-06-10 | Status: Accepted — Architecture Extension Ratified*
