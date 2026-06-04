# Neo4j Backup and Restore Runbook

## Purpose

Create, validate, and restore Neo4j backups for the knowledge graph using snapshots or Neo4j dump artifacts. Layer 3 semantic retrieval stores embeddings as Neo4j node properties and uses Neo4j-native `VECTOR` indexes, so graph backup/restore validation must include vector index state.

## Trigger

Scheduled backup, restore drill, failed checksum, graph data corruption, storage incident, or disaster-recovery declaration.

## Severity

SEV-1 for unrecoverable production graph data loss or restore failure; SEV-2 for stale backup chain or failed drill; SEV-3 for non-production backup issues.

## Preconditions

Backup destination, snapshot class or dump tooling, encryption/checksum metadata, restore namespace, and graph service owner approval are ready.

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

Backup/restore readiness gates: snapshot/dump completion, checksum verification, restore drill evidence, `pnpm db:extensions:check`, Layer 3 readiness checks, migration readiness checks for schema compatibility, and deployment gates before cutover.

## Related Runbooks

- [Backup and Disaster Recovery Runbook](backup-disaster-recovery.md)
- [Neo4j High Availability Runbook](neo4j-ha.md)
- [Neo4j Authentication Rate-Limit Recovery Runbook](neo4j-auth-rate-limit-recovery.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

> **Related ticket:** P1-018 — Neo4j Community Edition Has No HA  
> **Scope:** In-cluster Neo4j Community (dev / non-production)  
> **Last updated:** 2026-05-27

---

### Overview

This runbook covers backup and restore procedures for the **in-cluster Neo4j Community** instance deployed via `k8s/base/neo4j.yml`. Production and staging environments use **Neo4j Aura**, which provides managed backups; this runbook does not apply to Aura.

---

### Backup Strategy

#### Option 1: Kubernetes Volume Snapshot (Recommended for Community)

Create a snapshot of the Neo4j data PersistentVolume on a schedule.

```yaml
# k8s/base/neo4j-snapshot-cronjob.yml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: neo4j-volume-snapshot
spec:
  schedule: "0 3 * * *"  # daily at 03:00
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: snapshotter
              image: bitnami/kubectl:latest
              command:
                - /bin/sh
                - -c
                - |
                  TIMESTAMP=$(date +%Y%m%d-%H%M%S)
                  kubectl create -f - <<EOF
                  apiVersion: snapshot.storage.k8s.io/v1
                  kind: VolumeSnapshot
                  metadata:
                    name: neo4j-data-snapshot-${TIMESTAMP}
                    namespace: default
                  spec:
                    volumeSnapshotClassName: csi-snapclass
                    source:
                      persistentVolumeClaimName: neo4j-pvc
                  EOF
          restartPolicy: OnFailure
          serviceAccountName: snapshot-creator
```

> **Note:** Requires a CSI driver that supports VolumeSnapshots (e.g., AWS EBS CSI, GCP PD CSI).

#### Option 2: Neo4j Admin Dump

Run `neo4j-admin database dump` inside the Neo4j pod and stream the dump to object storage.

```bash
# One-off backup
kubectl exec -it deploy/neo4j -- neo4j-admin database dump neo4j --to-path=/backups

# Copy to S3
kubectl cp default/neo4j:/backups/neo4j.dump ./neo4j-$(date +%Y%m%d).dump
aws s3 cp ./neo4j-$(date +%Y%m%d).dump s3://fabric-backups/neo4j/
```

---

### Restore Procedure

#### From Volume Snapshot

1. Scale down Neo4j:
   ```bash
   kubectl scale deployment neo4j --replicas=0
   ```

2. Restore the PVC from snapshot:
   ```bash
   kubectl delete pvc neo4j-pvc
   kubectl apply -f - <<EOF
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: neo4j-pvc
   spec:
     dataSource:
       name: neo4j-data-snapshot-20260527-030000
       kind: VolumeSnapshot
       apiGroup: snapshot.storage.k8s.io
     accessModes:
       - ReadWriteOnce
     resources:
       requests:
         storage: 10Gi
   EOF
   ```

3. Scale Neo4j back up:
   ```bash
   kubectl scale deployment neo4j --replicas=1
   ```

#### From Neo4j Admin Dump

1. Scale down Neo4j:
   ```bash
   kubectl scale deployment neo4j --replicas=0
   ```

2. Clear existing data (caution — destructive):
   ```bash
   kubectl exec -it deploy/neo4j -- rm -rf /data/databases/neo4j /data/transactions/neo4j
   ```

3. Load the dump:
   ```bash
   kubectl cp ./neo4j-20260527.dump default/neo4j:/tmp/neo4j.dump
   kubectl exec -it deploy/neo4j -- neo4j-admin database load neo4j --from-path=/tmp
   ```

4. Scale Neo4j back up:
   ```bash
   kubectl scale deployment neo4j --replicas=1
   ```

---

### RTO / RPO Targets (Community)

| Metric | Target | Notes |
|---|---|---|
| RTO | 15–30 min | Manual restore from snapshot or dump |
| RPO | 24 h | Daily snapshots; more frequent snapshots reduce RPO |

For production workloads requiring RTO < 60 s and RPO near-zero, use **Neo4j Aura** instead of Community.
