# Graph Storage Encryption Control (Layer 3 / Neo4j)

## Current deployment posture (as of May 26, 2026)

- **Graph datastore**: Neo4j for self-hosted deployments via `k8s/neo4j.yml` and `k8s/base/neo4j.yml` PVCs (`neo4j-data-pvc`, `neo4j-logs-pvc`).
- **Production default**: `k8s/envs/prod/neo4j-aura-patch.yml` removes the in-cluster Neo4j deployment/PVCs, so production should use managed Neo4j Aura (provider-managed encryption at rest).
- **Legacy gap that existed before this control**: self-hosted Neo4j PVCs had no explicit encrypted `storageClassName` requirement.

## Control implementation

1. **Explicit encrypted-at-rest storage class requirement**
   - Neo4j PVCs now require `storageClassName: encrypted-rwo`.
   - PVCs are annotated with:
     - `security.valuefabric.io/encryption-at-rest: "required"`
     - `security.valuefabric.io/kms-provider: "external"`

2. **Externalized key management**
   - Encryption keys must be supplied by the cloud/Kubernetes storage provider through a managed KMS/HSM-backed encrypted storage class.
   - No static encryption keys are stored in repository files or plaintext `.env` templates.

3. **Policy/CI verification**
   - `scripts/ci/check_graph_storage_encryption.py` validates graph PVC encryption policy.
   - Policy source: `config/ci/graph-storage-encryption-policy.yaml`.
   - CI integration: `structural-preflight` job in `.github/workflows/pr-checks.yml`.

4. **Audit evidence hooks**
   - Declarative evidence in manifests (required annotations + storage class).
   - CI proof point emitted by `check_graph_storage_encryption.py` pass/fail output.
   - Runtime evidence can be collected using:
     - `kubectl get pvc neo4j-data-pvc neo4j-logs-pvc -n value-fabric -o yaml`
     - `kubectl get storageclass encrypted-rwo -o yaml`

## Scope

- Applies to self-hosted Neo4j graph storage in local/shared clusters and any non-Aura environment.
- In production, Aura mode remains the preferred path; if in-cluster Neo4j is re-enabled, encrypted storage class policy remains mandatory.

## Verification procedure

1. CI gate must pass: `python3 scripts/ci/check_graph_storage_encryption.py`.
2. Confirm manifests include required `storageClassName` and annotations.
3. Confirm selected storage class maps to provider encryption (CMEK/KMS policy in cluster infra).
4. For production cluster attestation, record `kubectl` outputs above in quarterly control evidence.
