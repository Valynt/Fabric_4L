# Incident Runbooks

This directory contains runbooks for every alert defined in `monitoring/alerting/rules.yml`.

## Policy links

- Severity matrix and escalation policy: [docs/operations/severity-escalation-policy.md](../../operations/severity-escalation-policy.md)
- MTTA/MTTR reporting process: [docs/operations/mtta-mttr-reporting.md](../../operations/mtta-mttr-reporting.md)
- Postmortem template and corrective actions: [docs/operations/postmortem-template.md](../../operations/postmortem-template.md)

## Runbook Index

| Alert | File | Severity | Status |
|---|---|---|---|
| **HighErrorRate** | [application/high-error-rate.md](application/high-error-rate.md) | critical | ✅ Expanded |
| **AgentWorkflowStall** | [application/agent-workflow-stall.md](application/agent-workflow-stall.md) | warning | ✅ New |
| **Neo4jUnreachable** | [infrastructure/neo4j-unreachable.md](infrastructure/neo4j-unreachable.md) | critical | ✅ New |
| **PostgresUnreachable** | [infrastructure/postgres-unreachable.md](infrastructure/postgres-unreachable.md) | critical | ✅ New |
| **RedisUnreachable** | [infrastructure/redis-unreachable.md](infrastructure/redis-unreachable.md) | warning | ✅ New |
| **LLMProviderOutage** | [application/llm-provider-outage.md](application/llm-provider-outage.md) | warning | ✅ New |
| DiskSpaceLow | [infrastructure/disk-space-low.md](infrastructure/disk-space-low.md) | warning | ✅ Complete |
| DiskSpaceCritical | [infrastructure/disk-space-critical.md](infrastructure/disk-space-critical.md) | critical | ✅ Complete |
| DiskInodeExhaustion | [infrastructure/disk-inode-exhaustion.md](infrastructure/disk-inode-exhaustion.md) | warning | ✅ Complete |
| SlowQueries | [application/slow-queries.md](application/slow-queries.md) | warning | ✅ Complete |
| Neo4jDown | [infrastructure/neo4j-down.md](infrastructure/neo4j-down.md) | critical | Legacy |
| PostgresDown | [infrastructure/postgres-down.md](infrastructure/postgres-down.md) | critical | Legacy |
| RedisDown | [infrastructure/redis-down.md](infrastructure/redis-down.md) | warning | Legacy |
| WorkflowStalled | [application/workflow-stalled.md](application/workflow-stalled.md) | warning | Legacy |
| HighMemoryUsage | [infrastructure/high-memory-usage.md](infrastructure/high-memory-usage.md) | warning | ✅ Complete |
| HighCPUUsage | [infrastructure/high-cpu-usage.md](infrastructure/high-cpu-usage.md) | warning | ✅ Complete |
| FormulaApprovalRequired | [application/formula-approval.md](application/formula-approval.md) | warning | |
| HighLLMCostRate | [application/high-llm-cost.md](application/high-llm-cost.md) | warning | |
| StaleGroundTruthObjects | [application/stale-ground-truth.md](application/stale-ground-truth.md) | warning | |
| ServiceDown | [infrastructure/service-down.md](infrastructure/service-down.md) | critical | ✅ Complete |

## Disaster Recovery Game Days

| Runbook | File | Cadence |
|---|---|---|
| Critical Service Failover | [incident/dr-gameday-service-failover.md](incident/dr-gameday-service-failover.md) | Monthly |
| Region/Account Loss Simulation | [incident/dr-gameday-region-loss.md](incident/dr-gameday-region-loss.md) | Quarterly |
| DR Evidence Logging Template | [incident/dr-evidence-log-template.md](incident/dr-evidence-log-template.md) | Every DR exercise or incident |
| DeploymentSignatureVerification | [infrastructure/deployment-signature-verification.md](infrastructure/deployment-signature-verification.md) | critical |
| ZeroTrustValidation | [application/zero-trust-validation.md](application/zero-trust-validation.md) | critical |
| BackupDRDrill | [incident/backup-disaster-recovery.md](incident/backup-disaster-recovery.md) | critical |
| DeploymentRollout | [infrastructure/deployment-rollout-and-rollback.md](infrastructure/deployment-rollout-and-rollback.md) | warning |

## Operations Runbooks

| Runbook | File | Purpose |
|---------|------|---------|
| Backup and Disaster Recovery | [incident/backup-disaster-recovery.md](incident/backup-disaster-recovery.md) | RTO/RPO targets, backup verification, PITR restore procedures |
| Deployment Rollout and Rollback | [infrastructure/deployment-rollout-and-rollback.md](infrastructure/deployment-rollout-and-rollback.md) | Rollout strategies, rollback procedures, canary/blue-green criteria |

## Incident Management Templates

| Template | File | Purpose |
|---|---|---|
| Severity Classification | [incident/severity-classification.md](incident/severity-classification.md) | SEV1-SEV4 definitions, response targets, and cadence |
| Communication Templates | [incident/communication-template.md](incident/communication-template.md) | Internal Slack, customer status page, and post-mortem templates |
| Data Breach Response | [incident/data-breach-response.md](incident/data-breach-response.md) | Suspected or confirmed unauthorized data access response |
| Tenant Isolation Failure | [incident/tenant-isolation-failure.md](incident/tenant-isolation-failure.md) | Cross-tenant data exposure containment and remediation |
| Ransomware Response | [incident/ransomware-response.md](incident/ransomware-response.md) | Encryption, destructive malware, and backup-protection response |
| Cloud Provider Outage | [incident/cloud-provider-outage.md](incident/cloud-provider-outage.md) | AWS/GCP/Azure regional or managed-service outage response |
| Incident Postmortem Template | [incident/incident-postmortem-template.md](incident/incident-postmortem-template.md) | Mandatory post-incident write-up with action-item tracking |
| SLOBreach | [application/slo-breach-response.md](application/slo-breach-response.md) | critical |
