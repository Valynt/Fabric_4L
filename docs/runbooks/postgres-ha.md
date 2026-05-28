# PostgreSQL High Availability Runbook

> **Ticket:** P1-017 — PostgreSQL Single Replica = Single Point of Failure  
> **Status:** Documented strategy; pending implementation in staging  
> **Owner:** Platform Engineering  
> **Last updated:** 2026-05-27

---

## Current State

| Component | Configuration | Risk |
|---|---|---|
| PostgreSQL Deployment | `replicas: 1` | Single point of failure |
| PVC | `postgres-pvc`, 10 GiB, `ReadWriteOnce` | Cannot be shared across replicas |
| Connection Pooling | PgBouncer (2 replicas) | Provides pooling, **not** HA |
| Replication | None | No failover on primary loss |

PgBouncer improves connection efficiency but does **not** provide automatic failover or data redundancy. If the single PostgreSQL pod fails, all layers lose durable state until manual recovery.

---

## Recommended Solution: CloudNativePG

**Option A — CloudNativePG (recommended)** replaces the in-cluster `Deployment`-based PostgreSQL with a Kubernetes-native operator-managed cluster.

### Why CloudNativePG over Patroni + StatefulSet

| Concern | CloudNativePG | Patroni + StatefulSet |
|---|---|---|
| Failover | Automatic via operator | Manual/etcd-dependent |
| Backup | Built-in PgBackRest | Requires separate setup |
| Operational burden | Low (operator-managed) | High (custom scripts) |
| Recovery Time Objective (RTO) | < 60 s | 2–5 min (typical) |
| Recovery Point Objective (RPO) | Near-zero (synchronous) | Configurable |

### Target Architecture

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

### Proposed Manifest (`k8s/base/postgres.yml`)

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

### Connection String Updates

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

### Rollout Plan

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

## Alternative: Patroni + StatefulSet

If CloudNativePG is not approved, a custom Patroni stack on StatefulSet provides equivalent functionality with higher operational overhead. See [Patroni Kubernetes documentation](https://patroni.readthedocs.io/en/latest/kubernetes.html) for bootstrap instructions.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Migration downtime during cutover | Use logical replication or pg_dump/pg_restore during low-traffic window |
| Backup strategy conflict with P0-005 | CloudNativePG PgBackRest replaces existing backup; coordinate with DR team |
| Connection string drift | Update all `k8s/base/configmap-*.yml` and `.env.example` simultaneously |
| Operator dependency | Pin CloudNativePG operator version; test upgrade path in staging |
