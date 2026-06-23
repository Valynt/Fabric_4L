# Ransomware Response Runbook

Use this runbook when file encryption, ransom notes, destructive malware, abnormal mass writes/deletes, unauthorized backup deletion, or endpoint security ransomware alerts are detected. Treat as **SEV1** until Security downgrades it.

## Triggers

- Ransom note or unexpected encrypted files in workloads, volumes, object storage, CI runners, or administrator workstations.
- Sudden spike in file renames, writes, deletes, or object version changes.
- Endpoint detection or cloud security alert for ransomware behavior.
- Backup deletion, snapshot tampering, or retention policy changes.
- Production services failing due to unreadable configuration, data files, or mounted volumes.

## Immediate response

1. **Declare SEV1** and open a restricted security war room.
2. **Isolate before rebooting:** quarantine affected hosts, pods, runners, and credentials. Do not power off systems unless Security directs it.
3. **Stop spread:** disable compromised accounts, revoke sessions, rotate credentials, block suspicious network paths, and pause automation that writes to shared storage.
4. **Protect backups:** lock backup buckets, disable lifecycle deletion changes, verify immutable backup retention, and restrict backup-admin credentials.
5. **Preserve evidence:** collect ransom notes, process lists, container images, pod specs, logs, file samples, hashes, and access logs.
6. **Notify Security, Legal, Executive sponsor, and cloud/provider support** if production or customer data may be impacted.

## Diagnosis

```bash
# Identify pods with restart loops or storage errors.
kubectl get pods -A
kubectl describe pod -n <namespace> <pod-name>

# Search logs for encryption/ransomware indicators.
kubectl logs -n value-fabric --all-containers --since=2h | rg -i "ransom|encrypt|decrypt|bitcoin|monero|locked|extension|permission denied|input/output error"

# Review recent Kubernetes events and suspicious changes.
kubectl get events -A --sort-by=.lastTimestamp | tail -200
kubectl get rolebindings,clusterrolebindings -A

# Review object-storage or backup deletion events in the cloud provider console/CLI.
# Export results to the incident evidence log before making changes.
```

## Containment actions

| Area | Action |
|---|---|
| Kubernetes workloads | Network-isolate affected namespaces, scale down infected workloads after evidence capture, redeploy only from trusted images. |
| Databases | Stop non-essential writers, preserve WAL/binlogs, snapshot current state, verify PITR backups. |
| Object storage | Enable object lock/legal hold where available, suspend lifecycle deletions, rotate storage credentials. |
| CI/CD | Disable affected runners, rotate deploy keys and signing credentials, review recent pipeline executions. |
| Identity | Disable suspicious users/service accounts, revoke sessions, rotate tokens, require MFA revalidation for privileged accounts. |

## Recovery procedure

1. Confirm attacker access is contained before restoring.
2. Determine clean restore point using logs, file timestamps, hashes, and backup metadata.
3. Restore into an isolated environment first and scan restored artifacts.
4. Validate database integrity, tenant isolation, application checksums, and service health.
5. Rotate all credentials that could have touched affected hosts or backups.
6. Redeploy production from trusted images and infrastructure-as-code state.
7. Monitor for encryption indicators and suspicious access for at least 14 days.

## Do not

- Do not pay or negotiate without executive, Legal, Security, and insurer approval.
- Do not delete encrypted files, ransom notes, pods, or volumes before evidence capture.
- Do not restore over infected systems until persistence and access paths are removed.
- Do not trust backups until integrity, age, and access logs are verified.

## Closure criteria

- No active encryption or attacker access remains.
- Backups are verified clean and protected from deletion.
- Production services are restored from trusted artifacts.
- Customer/data impact assessment is approved by Security and Legal.
- Credentials are rotated and privileged access reviewed.
- Post-mortem, corrective actions, and security monitoring updates are complete.
