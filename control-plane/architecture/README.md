# Architecture — L1 System Map

One page. This is the highest disclosure level: what the system IS, before any component detail.

## What the system is

**ValuePilot** turns tenant-scoped account evidence into a defensible, versioned, decision-ready
value case. Custom code concentrates on the differentiating journey:

**hypothesis -> value driver -> formula/model -> business case -> deliverable -> realization**

Commodity capabilities (ingestion plumbing, identity, workflow durability, review tooling,
observability, structured LLM output, external GTM data) sit behind adapters rather than bespoke
implementations.

## Topology

```text
                         apps/web  (React frontend — the ValuePilot experience)
                              |
                       services/api  (FastAPI BFF — 24 routers, one public ingress surface)
                              |
        +---------------------+----------------------+---------------------+
        |                     |                      |                     |
  layer1-ingestion     layer2-extraction /     layer3-knowledge      layer4-agents
  (intake, workers)    layer2-5-signal-        (conformed knowledge)  (orchestrated
                       refinery                                       agent workflows)
                              |                      |                     |
        +---------------------+----------------------+---------------------+
        |                     |                      |
  layer5-ground-truth   layer6-benchmarks      layer7-billing + billing
  (human review,        (validated benchmarks, (monetization)
   provenance,           ROI reference data)
   claims governance)
                              |
                       value-studio (TS domain service: value_case_orchestrator)

  packages/          shared TS/Python libraries, platform contracts, feature flags
  contracts/         OpenAPI per layer, JSON schemas, tool manifests, agent registry
  infra/ k8s/ monitoring/    deployment topology, policy, observability
  compliance/ security/      audit contracts, threat model, evidence
```

## Canonical data flow

```text
Account evidence -> ingestion/extraction -> operational signal -> hypothesis
  -> human validation (L5 review) -> value driver -> deterministic formula
  -> ROI scenario -> evidence-linked narrative -> approval -> export/deliverable
  -> realized outcome
```

Every quantitative claim on that chain MUST expose a provenance path back to its original
source (product rule R-8). Financial math is deterministic (R-4). Approved versions are
immutable (R-7).

## Reading further

- Boundaries and allowed dependencies: `architecture/boundaries.md`
- The behaviors that traverse this map: `control-plane/behaviors/`
- Component-level detail: `handbook/L2-components/`
- Code anchors: `handbook/L3-implementation/`
