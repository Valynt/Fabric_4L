# Neo4j Backup and Restore Runbook

> **Related ticket:** P1-018 — Neo4j Community Edition Has No HA  
> **Scope:** In-cluster Neo4j Community (dev / non-production)  
> **Last updated:** 2026-05-27

---

## Overview

This runbook covers backup and restore procedures for the **in-cluster Neo4j Community** instance deployed via `k8s/base/neo4j.yml`. Production and staging environments use **Neo4j Aura**, which provides managed backups; this runbook does not apply to Aura.

---

## Backup Strategy

### Option 1: Kubernetes Volume Snapshot (Recommended for Community)

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

### Option 2: Neo4j Admin Dump

Run `neo4j-admin database dump` inside the Neo4j pod and stream the dump to object storage.

```bash
# One-off backup
kubectl exec -it deploy/neo4j -- neo4j-admin database dump neo4j --to-path=/backups

# Copy to S3
kubectl cp default/neo4j:/backups/neo4j.dump ./neo4j-$(date +%Y%m%d).dump
aws s3 cp ./neo4j-$(date +%Y%m%d).dump s3://fabric-backups/neo4j/
```

---

## Restore Procedure

### From Volume Snapshot

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

### From Neo4j Admin Dump

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

## RTO / RPO Targets (Community)

| Metric | Target | Notes |
|---|---|---|
| RTO | 15–30 min | Manual restore from snapshot or dump |
| RPO | 24 h | Daily snapshots; more frequent snapshots reduce RPO |

For production workloads requiring RTO < 60 s and RPO near-zero, use **Neo4j Aura** instead of Community.
