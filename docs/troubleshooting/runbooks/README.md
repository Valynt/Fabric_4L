# Incident Runbooks

This directory contains runbooks for every alert defined in `monitoring/alerting/rules.yml`.

## Policy links

- Severity matrix and escalation policy: [docs/operations/severity-escalation-policy.md](../../operations/severity-escalation-policy.md)
- MTTA/MTTR reporting process: [docs/operations/mtta-mttr-reporting.md](../../operations/mtta-mttr-reporting.md)
- Postmortem template and corrective actions: [docs/operations/postmortem-template.md](../../operations/postmortem-template.md)

## Runbook Index

| Alert | File | Severity | Status |
|---|---|---|---|
| **HighErrorRate** | [high-error-rate.md](high-error-rate.md) | critical | ✅ Expanded |
| **AgentWorkflowStall** | [agent-workflow-stall.md](agent-workflow-stall.md) | warning | ✅ New |
| **Neo4jUnreachable** | [neo4j-unreachable.md](neo4j-unreachable.md) | critical | ✅ New |
| **PostgresUnreachable** | [postgres-unreachable.md](postgres-unreachable.md) | critical | ✅ New |
| **RedisUnreachable** | [redis-unreachable.md](redis-unreachable.md) | warning | ✅ New |
| **LLMProviderOutage** | [llm-provider-outage.md](llm-provider-outage.md) | warning | ✅ New |
| DiskSpaceLow | [disk-space-low.md](disk-space-low.md) | warning | ✅ Complete |
| DiskSpaceCritical | [disk-space-critical.md](disk-space-critical.md) | critical | ✅ Complete |
| DiskInodeExhaustion | [disk-inode-exhaustion.md](disk-inode-exhaustion.md) | warning | ✅ Complete |
| SlowQueries | [slow-queries.md](slow-queries.md) | warning | ✅ Complete |
| Neo4jDown | [neo4j-down.md](neo4j-down.md) | critical | Legacy |
| PostgresDown | [postgres-down.md](postgres-down.md) | critical | Legacy |
| RedisDown | [redis-down.md](redis-down.md) | warning | Legacy |
| WorkflowStalled | [workflow-stalled.md](workflow-stalled.md) | warning | Legacy |
| HighMemoryUsage | [high-memory-usage.md](high-memory-usage.md) | warning | ✅ Complete |
| HighCPUUsage | [high-cpu-usage.md](high-cpu-usage.md) | warning | ✅ Complete |
| FormulaApprovalRequired | [formula-approval.md](formula-approval.md) | warning | |
| HighLLMCostRate | [high-llm-cost.md](high-llm-cost.md) | warning | |
| StaleGroundTruthObjects | [stale-ground-truth.md](stale-ground-truth.md) | warning | |
| ServiceDown | [service-down.md](service-down.md) | critical | ✅ Complete |

## Disaster Recovery Game Days

| Runbook | File | Cadence |
|---|---|---|
| Critical Service Failover | [dr-gameday-service-failover.md](dr-gameday-service-failover.md) | Monthly |
| Region/Account Loss Simulation | [dr-gameday-region-loss.md](dr-gameday-region-loss.md) | Quarterly |
| DR Evidence Logging Template | [dr-evidence-log-template.md](dr-evidence-log-template.md) | Every DR exercise or incident |
| DeploymentSignatureVerification | [deployment-signature-verification.md](deployment-signature-verification.md) | critical |
| ZeroTrustValidation | [zero-trust-validation.md](zero-trust-validation.md) | critical |
| BackupDRDrill | [backup-disaster-recovery.md](backup-disaster-recovery.md) | critical |
| DeploymentRollout | [deployment-rollout-and-rollback.md](deployment-rollout-and-rollback.md) | warning |

## Operations Runbooks

| Runbook | File | Purpose |
|---------|------|---------|
| Backup and Disaster Recovery | [backup-disaster-recovery.md](backup-disaster-recovery.md) | RTO/RPO targets, backup verification, PITR restore procedures |
| Deployment Rollout and Rollback | [deployment-rollout-and-rollback.md](deployment-rollout-and-rollback.md) | Rollout strategies, rollback procedures, canary/blue-green criteria |

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
