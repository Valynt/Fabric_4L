# L1 — System Map

Level 1 of progressive disclosure. Read this once for orientation, then navigate by behavior —
do not expand into L2/L3 until a behavior card tells you to.

## The product in one paragraph

**ValuePilot** turns tenant-scoped account information, customer evidence, validated benchmarks,
explicit assumptions, and human judgment into a defensible, versioned, decision-ready financial
value case. A value engineer starts or resumes an account case, inspects source-to-signal
reasoning, validates hypotheses, builds a driver-based financial model, generates an
evidence-linked narrative from an immutable snapshot, obtains approval, exports the exact
approved version, and tracks realized value — without losing tenant scope, financial
traceability, human judgment, or provenance.

## Topology

Four-layer/layered services topology. All paths verified against the repository.

```
apps/web                         React/Vite frontend (the canonical user journey)
    |
services/api                     FastAPI gateway / BFF — the only public ingress;
                                 24 verified routers under services/api/app/routers/
    |
    +-- services/layer1-ingestion      L1 ingestion (sources, durable runs)
    +-- services/layer2-extraction     L2 extraction (facts from sources)
    +-- services/layer2-5-signal-refinery  L2.5 signal refinement
    +-- services/layer3-knowledge      L3 knowledge/graph + deterministic ROI authority
    +-- services/layer4-agents         L4 agent orchestration, workflows, human gates
    +-- services/layer5-ground-truth   L5 truth, value claims, governance
    +-- services/layer6-benchmarks     L6 governed benchmarks
    +-- services/layer7-billing        L7 billing
    +-- services/value-studio          TS domain service: value-case orchestration

packages/                        shared, platform-contract, feature-flags, config,
                                 eslint-plugin-fabric-contracts
contracts/                       openapi/, jsonschema/, tool-manifests/, agent-registry/,
                                 frontend/ — versioned cross-surface contracts
control-plane/                   product contract, architecture, behaviors, release model
handbook/                        this workspace
```

Layer authority (from the engineering contract, `control-plane/product-contract/07_engineering-contract.md`):
L1/L2 own ingestion and extraction; L3 owns tenant-scoped graph retrieval and the deterministic
calculation; L4 orchestrates workflows and human interrupts but never redefines L3 math; L5 owns
truth and claim governance; L6 owns benchmark identity and applicability; the gateway
(`services/api`) is the only ingress — direct layer access is denied.

## Canonical data flow

```
account -> hypothesis -> driver -> formula -> ROI -> business case
        -> deliverable -> realization
```

Full canonical domain chain (order is normative, per
`control-plane/product-contract/03_domain-lifecycle.md`):

```
Account -> Analysis Case -> Source -> Extracted Fact -> Pain Signal -> Value Hypothesis
-> Validated Value Driver -> Value Lever and Formula -> Evidence or Benchmark -> Scenario
-> ROI Snapshot -> Narrative -> Value Case Version -> Approval and Export -> Realization
```

Every screen and API operates on this shared chain. One canonical case ID spans Intelligence,
Studio, calculation, narrative, deliverables, and realization. Browser state is never
authoritative (R-2).

## Where to go next

- System architecture detail and allowed dependencies: `control-plane/architecture/README.md`
  and `control-plane/architecture/boundaries.md`.
- To change something: pick the behavior in `handbook/INDEX.md` and follow its card.
- Components: `handbook/L2-components/`.
