# Incident Runbooks

This directory contains runbooks for every alert defined in `monitoring/alerting/rules.yml`.

## Standard Production Runbook Template

New production runbooks must start from [`_template.md`](_template.md) and keep these sections in order:

1. Purpose
2. Trigger
3. Severity
4. Preconditions
5. Immediate Actions
6. Diagnosis Steps
7. Resolution Steps
8. Validation
9. Rollback / Fallback
10. Customer / Stakeholder Communication
11. Evidence to Preserve
12. Related Gates
13. Related Runbooks
14. Post-Incident Follow-Up

`Related Gates` must name the applicable readiness or CI gates, such as deployment gates, migration readiness gates, tenant-isolation gates, backup/restore readiness gates, agent evaluation gates, and observability alert gates.

## Runbook Index

| Alert | File | Severity |
|---|---|---|
| HighErrorRate | [high-error-rate.md](high-error-rate.md) | critical |
| DiskSpaceLow | [disk-space-low.md](disk-space-low.md) | warning |
| DiskSpaceCritical | [disk-space-critical.md](disk-space-critical.md) | critical |
| DiskInodeExhaustion | [disk-inode-exhaustion.md](disk-inode-exhaustion.md) | warning |
| SlowQueries | [slow-queries.md](slow-queries.md) | warning |
| Neo4jDown | [neo4j-down.md](neo4j-down.md) | critical |
| PostgresDown | [postgres-down.md](postgres-down.md) | critical |
| RedisDown | [redis-down.md](redis-down.md) | warning |
| WorkflowStalled | [workflow-stalled.md](workflow-stalled.md) | warning |
| HighMemoryUsage | [high-memory-usage.md](high-memory-usage.md) | warning |
| HighCPUUsage | [high-cpu-usage.md](high-cpu-usage.md) | warning |
| FormulaApprovalRequired | [formula-approval.md](formula-approval.md) | warning |

## Deployment Operations

- [deployment-rollout-and-rollback.md](deployment-rollout-and-rollback.md): CI/CD rollout policy, canary vs blue-green selection, and rollback steps.
