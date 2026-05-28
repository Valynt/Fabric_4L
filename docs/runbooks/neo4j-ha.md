# Neo4j High Availability Runbook

> **Ticket:** P1-018 — Neo4j Community Edition Has No HA  
> **Status:** Documented strategy; production already uses Aura  
> **Owner:** Platform Engineering  
> **Last updated:** 2026-05-27

---

## Current State

| Environment | Neo4j Configuration | HA Status |
|---|---|---|
| Production | Neo4j Aura (managed SaaS) | ✅ HA via Aura clustering |
| Staging / Pre-prod | Neo4j Aura staging instance | ✅ HA via Aura clustering |
| K8s base manifests | Single Neo4j Community pod | ❌ No clustering |
| Local / Dev | Single Neo4j Community container | ❌ No clustering (acceptable) |

The in-cluster Neo4j Community Deployment (`k8s/base/neo4j.yml`) is patched out in production via `k8s/envs/prod/neo4j-aura-patch.yml`. The base manifest remains for local development and non-production self-hosted deployments.

---

## Neo4j Community Limitation

Neo4j Community Edition **does not support causal clustering** (the HA mechanism used by Neo4j Enterprise). Core limitations:

- No multi-node causal cluster
- No automatic failover
- No read replicas
- Single write capability only

Upgrading the in-cluster image to `neo4j:5-enterprise` requires a Neo4j Enterprise license, which is not currently held.

---

## Production Architecture

```
┌─────────────────────────────────────────────┐
│              Neo4j Aura                     │
│  ┌─────────┐ ┌─────────┐ ┌────────┐        │
│  │  Core 1 │ │  Core 2 │ │ Core 3 │        │
│  │  (RW)   │ │  (RW)   │ │ (RW)   │        │
│  └────┬────┘ └────┬────┘ └───┬────┘        │
│       └───────────┴──────────┘              │
│         Causal Clustering                   │
│         Automatic Failover                  │
└─────────────────────────────────────────────┘
              ▲
              │ bolt+s://
┌─────────────┴───────────────────────────────┐
│         Value Fabric K8s Cluster            │
│  (Neo4j Community pod is NOT deployed)      │
│  k8s/envs/prod/neo4j-aura-patch.yml         │
│  removes the in-cluster Deployment           │
└─────────────────────────────────────────────┘
```

---

## Non-Production Resilience

For staging and pre-production environments that do **not** use Aura:

1. **Preferred:** Continue using Neo4j Aura staging instances (same HA guarantees as production).
2. **Fallback:** If Aura is unavailable, the single Community instance in `k8s/base/neo4j.yml` is acceptable with documented snapshot/restore procedures (see `docs/runbooks/neo4j-backup-restore.md`).

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2024-Q3 | Adopt Neo4j Aura for production | Eliminates operational burden of self-hosted clustering; provides managed HA, backups, and patching |
| 2025-Q1 | Retain Community in-cluster for dev | Licensing cost avoidance for non-production; dev data is ephemeral |
| 2026-05 | Document HA gap (P1-018) | Ensure staging/pre-prod teams understand the Aura dependency and do not rely on in-cluster Community for HA |

---

## Action Items

- [ ] **Platform:** Verify all staging/pre-prod namespaces use Aura endpoints (not in-cluster Community).
- [ ] **SRE:** Add Neo4j Aura connection health to staging environment readiness gates.
- [ ] **Docs:** Keep `k8s/base/neo4j.yml` annotated with a warning comment that Community is not HA.
