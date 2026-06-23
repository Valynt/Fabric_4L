# ADR: Neo4j Hosting Strategy for Fabric_4L Production

## Status

Accepted — 2026-06-23

## Context

Fabric_4L requires a graph database for Layer 3 (Knowledge Graph) and Layer 2.5 (Signal Refinery). The current production-readiness audit identifies Neo4j clustering as a P0-002 item, but the default path for PostgreSQL and Redis has been revised to AWS-managed services (RDS/Aurora and ElastiCache). Neo4j requires a similar architectural decision.

## Decision

### Production Path: Managed Neo4j Aura

**Rationale:**
- Lowest operational burden: automated backups, patching, scaling, and monitoring
- Built-in HA and clustering without custom Kubernetes StatefulSet management
- Professional support and SLAs
- Compliance certifications (SOC 2, encryption at rest/transit)

**Operational requirements:**
1. **Pricing model:** Per-GB or per-instance; must fit projected data volumes (entity graph, relationship graph, provenance)
2. **Region availability:** Must be available in the same AWS region as EKS workloads (us-east-1) or support low-latency VPC peering
3. **VPC connectivity:** PrivateLink, VPC peering, or IP allowlisting for EKS → Neo4j traffic
4. **Backup SLAs:** Point-in-time recovery, snapshot frequency, export portability
5. **Compliance:** SOC 2 Type II, encryption standards, audit logging

**Production implementation:**
- Connection details stored in Vault and synced via ExternalSecrets
- Production overlays delete the in-cluster Neo4j Deployment, Service, and PVCs via `k8s/envs/prod/neo4j-aura-patch.yml`
- Layer 3 and Layer 4 settings reject in-cluster or insecure Neo4j targets in staging/production
- Network policy for egress to Aura endpoints
- Backup validation per Aura SLA

### Fallback Path: Self-Hosted Neo4j on EKS via Helm

**Rationale:**
- Allowed only with explicit architecture/security exception if managed Neo4j is not feasible due to cost, compliance, or data sovereignty constraints
- Full control over deployment, backups, and networking

**Implementation:**
- Use the official Neo4j Helm chart (neo4j/helm-charts)
- Deploy as a 3-core causal cluster
- Persistent volumes with `Retain` reclaim policy
- Backup sidecar or CronJob using `neo4j-admin database dump`
- Network policies for intra-cluster (5000) and Bolt (7687) traffic

**Avoid:**
- Hand-rolled raw Neo4j cluster YAML unless Helm is not viable for a specific technical constraint

## Consequences

### Positive
- Managed path reduces Day-2 operational overhead significantly
- Helm fallback provides portability and avoids vendor lock-in
- Clear decision criteria prevent analysis paralysis

### Negative
- Managed Neo4j Aura may have higher per-GB costs than self-hosted EBS
- VPC peering or PrivateLink may add network complexity and latency
- Helm path requires ongoing maintenance of backup/restore runbooks

## Action Items

1. **Platform:** Keep `k8s/envs/prod/neo4j-aura-patch.yml` in the production overlay so in-cluster Neo4j is not deployed for production traffic.
2. **SRE:** Validate Aura endpoint connectivity, backup SLA evidence, and restore/export procedures as release evidence.
3. **Security:** Keep production/staging startup validation fail-closed for non-Aura or insecure Neo4j targets.
4. **Architecture:** Prepare Helm fallback only as an exception path, not as the default production deployment.

## Related

- P0-002 Production Readiness Audit: HA Database Deployment
- `k8s/ha/neo4j/helm-values.yaml` (fallback implementation, created if needed)
- `k8s/external-secrets/neo4j-secrets.yaml` (already exists for connection credentials)
