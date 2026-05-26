# Neo4j Storage Encryption & Key Rotation Runbook

## Purpose
Operational runbook for graph datastore encryption-at-rest verification, key rotation, and recovery evidence.

## Verify encryption posture
- `python3 scripts/ci/check_graph_storage_encryption.py`
- `kubectl get pvc neo4j-data-pvc neo4j-logs-pvc -n value-fabric -o yaml`
- `kubectl get storageclass encrypted-rwo -o yaml`

## Key rotation (managed KMS/HSM)
1. Rotate provider key via managed KMS/HSM flow.
2. Confirm encrypted storage class mapping still references managed key alias/version.
3. If provider requires re-encryption/rebind, snapshot first, then recreate/rebind volume and restart Neo4j.
4. Record evidence: KMS rotation event ID, storage class metadata, PVC metadata, health checks.

## Recovery
- Restore Neo4j from latest backup if post-rotation boot fails.
- Emergency rollback of key alias mapping requires security approval.
- Validate workload and graph health after recovery.

## Audit evidence hooks
- Record only non-secret metadata (storage class, key alias reference, rotation timestamp, CI pass output).
- Do not log plaintext keys, tokens, or secret values.

## Non-prod caveat
Dev/local clusters may use simplified encrypted storage class implementations, but must still satisfy the `encrypted-rwo` encryption policy and must not introduce static key material into repository files.
