# Architecture Boundaries

Allowed dependencies, adapter policy, and boundary enforcement. Normative: MUST/SHOULD/MAY.

## Dependency rules

1. **One public ingress.** `apps/web` and external clients reach the system only through
   `services/api` (the BFF/gateway surface). Internal layer services MUST reject unauthorized
   direct access.
2. **Layered flow.** Requests flow DOWN the layer stack (api -> L4 agents -> L3 knowledge ->
   L2 extraction/refinery -> L1 ingestion) and read UP through governed contracts
   (L5 ground truth, L6 benchmarks). A layer MUST NOT reach sideways into another layer's
   persistence store.
3. **Contracts at every boundary.** Cross-layer interaction uses versioned contracts from
   `contracts/` (OpenAPI per layer, JSON schemas, tool manifests, event envelopes). No
   undocumented route or event enters production (gate AG-03).
4. **Shared code only via `packages/`.** Copy-paste between services is a boundary violation.

## Adapter policy — commodity capabilities

Custom code concentrates on the value-engineering journey. Commodity capabilities sit behind
narrow provider interfaces owned by Fabric, so vendors remain replaceable infrastructure:

```text
                 Fabric Capability (interface owned here)
                           |
                    Provider Router
                           |
        +------------------+------------------+
        |                  |                  |
   External vendor    Open-source pipes    Native/direct
   (e.g. Cargo)       (connectors, sync)    integrations
```

Rules:

5. **Vendor SDKs MUST NOT leak across boundaries.** Calls to an external platform (e.g. a GTM
   data provider) appear only inside its adapter module — never scattered through L2/L4.
6. **Provenance attaches at the adapter edge.** Every externally-derived fact enters with
   source provider, upstream provider, retrieval time, confidence, tenant, evidence ID, and
   usage policy. L5 decides whether it can support a customer-facing claim.
7. **Fail closed on provider absence.** The ValuePilot journey degrades to visibly-labeled
   fallback behavior; it MUST NOT silently depend on one vendor (product rule R-5).

## Enforcement

- Boundary fitness tests run under gate **AG-01** (repository integrity: architecture-boundary
  fitness tests) and **AG-03** (contract compliance).
- Dependency rules are checked mechanically (dependency-cruiser or equivalent) — see
  `control-plane/release/test_strategy.md` (static quality row).
- A change that needs a new cross-layer dependency updates this file in the same PR.

## What is deliberately NOT here

Production workflow orchestration (durable execution, tenant isolation in queues, retries,
review gates at runtime) is a runtime concern owned by the services and their deployment
manifests — this document governs **static structure and navigation**, and
`control-plane/release/` governs **release proof**. Keep those three concerns separate.
