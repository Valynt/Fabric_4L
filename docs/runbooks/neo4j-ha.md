# Neo4j High Availability Runbook

## Purpose

Operate the Neo4j high-availability posture and decision path for production graph resilience.

## Trigger

Production resilience review, Neo4j downtime, capacity or quorum concerns, failover planning, or HA architecture approval.

## Severity

SEV-1 for production graph outage without healthy failover; SEV-2 for degraded redundancy or restore-only exposure; SEV-3 for architecture documentation drift.

## Preconditions

Current cluster/deployment topology, backup status, service SLOs, license constraints, and dependency impact assessment are known.

## Immediate Actions

1. Declare or confirm the incident owner and severity.
2. Freeze risky automated changes affecting the impacted service or control.
3. Capture initial timestamps, tenant/customer scope, deployment version, and active alerts.
4. Use the diagnosis steps below before applying destructive or irreversible changes.

## Diagnosis Steps

1. Confirm the trigger condition and affected environment.
2. Review the relevant dashboards, logs, audit records, and CI/readiness gate output.
3. Identify whether the issue is isolated to one tenant, service, dependency, or deployment version.
4. Preserve evidence before restarting services, rotating credentials, restoring data, or changing routing.

## Resolution Steps

1. Apply the least-risk corrective action that addresses the confirmed failure mode.
2. Keep tenant isolation, contract compatibility, and fail-closed security behavior intact.
3. Escalate to the service owner or incident commander before any destructive operation.
4. Record each operator action, command, and configuration change in the incident record.

## Validation

- Re-run the relevant health checks, smoke tests, contract checks, or readiness gates listed below.
- Confirm impacted tenants/customers can complete the critical path that failed.
- Confirm logs, metrics, and audit records show recovery and no new cross-tenant or security errors.

## Rollback / Fallback

- Prefer rollback to the last known-good deployment, configuration, registry record, backup, or credential set.
- If rollback is unsafe, isolate the impacted component, drain traffic where supported, and use the documented fallback path in the procedure details.
- Do not delete evidence or failed artifacts until the incident commander approves cleanup.

## Customer / Stakeholder Communication

- Notify the incident channel and accountable product/support stakeholders when customer impact is confirmed or likely.
- Provide scope, severity, current mitigation, expected next update time, and known customer-facing symptoms.
- Avoid sharing secrets, raw tenant data, provider tokens, or unreviewed root-cause speculation.

## Evidence to Preserve

- Alert names, timestamps, dashboard snapshots or links, and runbook version.
- Deployment SHAs, configuration diffs, migration IDs, registry versions, or backup artifact IDs.
- Sanitized logs, audit events, gate outputs, validation commands, and operator action timeline.

## Related Gates

Deployment and readiness gates: Layer 3 readiness probes, backup/restore readiness gates, observability alert gates for graph availability, migration readiness gates, and deployment gates for topology changes.

## Related Runbooks

- [Neo4j Backup and Restore Runbook](neo4j-backup-restore.md)
- [Neo4j Authentication Rate-Limit Recovery Runbook](neo4j-auth-rate-limit-recovery.md)
- [Backup and Disaster Recovery Runbook](backup-disaster-recovery.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

> **Ticket:** P1-018 — Neo4j Community Edition Has No HA  
> **Status:** Documented strategy; production already uses Aura  
> **Owner:** Platform Engineering  
> **Last updated:** 2026-05-27

---

### Current State

| Environment | Neo4j Configuration | HA Status |
|---|---|---|
| Production | Neo4j Aura (managed SaaS) | ✅ HA via Aura clustering |
| Staging / Pre-prod | Neo4j Aura staging instance | ✅ HA via Aura clustering |
| K8s base manifests | Single Neo4j Community pod | ❌ No clustering |
| Local / Dev | Single Neo4j Community container | ❌ No clustering (acceptable) |

The in-cluster Neo4j Community Deployment (`k8s/base/neo4j.yml`) is patched out in production via `k8s/envs/prod/neo4j-aura-patch.yml`. The base manifest remains for local development and non-production self-hosted deployments.

---

### Neo4j Community Limitation

Neo4j Community Edition **does not support causal clustering** (the HA mechanism used by Neo4j Enterprise). Core limitations:

- No multi-node causal cluster
- No automatic failover
- No read replicas
- Single write capability only

Upgrading the in-cluster image to `neo4j:5-enterprise` requires a Neo4j Enterprise license, which is not currently held.

---

### Production Architecture

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

### Non-Production Resilience

For staging and pre-production environments that do **not** use Aura:

1. **Preferred:** Continue using Neo4j Aura staging instances (same HA guarantees as production).
2. **Fallback:** If Aura is unavailable, the single Community instance in `k8s/base/neo4j.yml` is acceptable with documented snapshot/restore procedures (see `docs/runbooks/neo4j-backup-restore.md`).

---

### Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2024-Q3 | Adopt Neo4j Aura for production | Eliminates operational burden of self-hosted clustering; provides managed HA, backups, and patching |
| 2025-Q1 | Retain Community in-cluster for dev | Licensing cost avoidance for non-production; dev data is ephemeral |
| 2026-05 | Document HA gap (P1-018) | Ensure staging/pre-prod teams understand the Aura dependency and do not rely on in-cluster Community for HA |

---

### Action Items

- [ ] **Platform:** Verify all staging/pre-prod namespaces use Aura endpoints (not in-cluster Community).
- [ ] **SRE:** Add Neo4j Aura connection health to staging environment readiness gates.
- [ ] **Docs:** Keep `k8s/base/neo4j.yml` annotated with a warning comment that Community is not HA.
