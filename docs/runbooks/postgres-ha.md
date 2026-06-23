# PostgreSQL High Availability Runbook

## Purpose

Operate and evolve the PostgreSQL high-availability architecture for platform relational state.

## Trigger

PostgreSQL outage, failover planning, HA readiness review, data durability risk, migration-readiness concern, or production architecture approval.

## Severity

SEV-1 for production database outage or data loss risk; SEV-2 for degraded redundancy or failed failover drill; SEV-3 for architecture documentation drift.

## Preconditions

Current database topology, backup/PITR status, migration state, connection string inventory, operator access, and affected service list are known.

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

Migration and database readiness gates: `make check-migration-heads`, migration dry-run/readiness checks, backup/restore readiness gates, deployment gates for connection changes, tenant-isolation tests for data access, and observability alert gates for database health.

## Related Runbooks

- [Backup and Disaster Recovery Runbook](backup-disaster-recovery.md)
- [Deployment Rollout, Canary/Blue-Green Criteria, and Rollback](deployment-rollout-and-rollback.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

> **Ticket:** P1-017 — PostgreSQL Single Replica = Single Point of Failure  
> **Status:** Documented strategy; pending implementation in staging  
> **Owner:** Platform Engineering  
> **Last updated:** 2026-05-27

---

### Current State

| Component | Configuration | Risk |
|---|---|---|
| PostgreSQL Deployment | `replicas: 1` | Single point of failure |
| PVC | `postgres-pvc`, 10 GiB, `ReadWriteOnce` | Cannot be shared across replicas |
| Connection Pooling | PgBouncer (2 replicas) | Provides pooling, **not** HA |
| Replication | None | No failover on primary loss |

PgBouncer improves connection efficiency but does **not** provide automatic failover or data redundancy. If the single PostgreSQL pod fails, all layers lose durable state until manual recovery.

---

### Recommended Solution: CloudNativePG

**Option A — CloudNativePG (recommended)** replaces the in-cluster `Deployment`-based PostgreSQL with a Kubernetes-native operator-managed cluster.

#### Why CloudNativePG over Patroni + StatefulSet

| Concern | CloudNativePG | Patroni + StatefulSet |
|---|---|---|
| Failover | Automatic via operator | Manual/etcd-dependent |
| Backup | Built-in PgBackRest | Requires separate setup |
| Operational burden | Low (operator-managed) | High (custom scripts) |
| Recovery Time Objective (RTO) | < 60 s | 2–5 min (typical) |
| Recovery Point Objective (RPO) | Near-zero (synchronous) | Configurable |

#### Target Architecture

```
┌─────────────────────────────────────────────┐
│           Kubernetes Cluster                │
│  ┌─────────────────────────────────────┐    │
│  │      CloudNativePG Cluster          │    │
│  │  ┌─────────┐ ┌─────────┐ ┌────────┐│    │
│  │  │ Primary │ │ Replica │ │Replica ││    │
│  │  │  (rw)   │ │  (ro)   │ │ (ro)   ││    │
│  │  └────┬────┘ └─────────┘ └────────┘│    │
│  │       │ synchronous replication     │    │
│  │       └─────────────────────────────┘    │
│  └─────────────────────────────────────┘    │
│              │                              │
│  ┌───────────┴───────────┐                  │
│  │    PgBouncer Pool     │                  │
│  │  (connection routing) │                  │
│  └───────────────────────┘                  │
└─────────────────────────────────────────────┘
```

#### Proposed Manifest (`k8s/base/postgres.yml`)

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: fabric-pg
  namespace: default
spec:
  instances: 3
  imageName: ghcr.io/cloudnative-pg/postgresql:15.6

  storage:
    size: 10Gi
    storageClass: standard

  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"

  # Synchronous replication: at least 1 replica must acknowledge
  minSyncReplicas: 1
  maxSyncReplicas: 2

  # Built-in backup via PgBackRest
  backup:
    enabled: true
    retentionPolicy: "30d"
    schedule: "0 2 * * *"  # daily at 02:00
    barmanObjectStore:
      destinationPath: "s3://fabric-backups/postgres"
      s3Credentials:
        accessKeyId:
          name: backup-s3-secret
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: backup-s3-secret
          key: ACCESS_SECRET_KEY

  # Monitoring sidecar for Prometheus
  monitoring:
    enabled: true
    customQueriesConfigMap:
      name: cnpg-custom-queries
      key: queries.yaml
```

#### Connection String Updates

All services currently target `postgres.default.svc.cluster.local:5432`. After migration, point to the CloudNativePG read-write service:

```
# Before
DATABASE_URL=postgresql://user:pass@postgres:5432/db

# After
DATABASE_URL=postgresql://user:pass@fabric-pg-rw:5432/db
```

PgBouncer configuration (`k8s/base/pgbouncer.yml`) must update its `databases` section:

```ini
[databases]
* = host=fabric-pg-rw port=5432
```

#### Rollout Plan

1. **Staging**
   - Install CloudNativePG operator in staging cluster.
   - Deploy `Cluster` manifest alongside existing PostgreSQL.
   - Run `pg_dump` from old instance → restore into new cluster.
   - Update PgBouncer target, verify all layers connect.
   - Run `make test-backend-integrated-validation`.

2. **Production**
   - Schedule maintenance window (RTO target: < 5 min).
   - Repeat staging procedure with live data migration.
   - Decommission old `postgres.yml` Deployment and PVC.

3. **Validation**
   - Trigger primary failover: `kubectl cnpg failover fabric-pg`.
   - Confirm connections resume via PgBouncer within 60 s.
   - Verify backups exist in S3 destination.

---

### Alternative: Patroni + StatefulSet

If CloudNativePG is not approved, a custom Patroni stack on StatefulSet provides equivalent functionality with higher operational overhead. See [Patroni Kubernetes documentation](https://patroni.readthedocs.io/en/latest/kubernetes.html) for bootstrap instructions.

---

### Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Migration downtime during cutover | Use logical replication or pg_dump/pg_restore during low-traffic window |
| Backup strategy conflict with P0-005 | CloudNativePG PgBackRest replaces existing backup; coordinate with DR team |
| Connection string drift | Update all `k8s/base/configmap-*.yml` and `.env.example` simultaneously |
| Operator dependency | Pin CloudNativePG operator version; test upgrade path in staging |
