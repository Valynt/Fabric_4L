# Production Runbook Index

This is the canonical index for production procedures under `docs/runbooks/`. Existing alert-specific runbooks are preserved in their current locations and linked here so responders can distinguish broad production procedures from tactical alert responses.

For the concise incident-response workflow, severity matrix, escalation policy,
customer communications templates, postmortem template, and top failure-mode
runbooks, start with [`ops/incident/README.md`](../../ops/incident/README.md).

## Canonical directory structure

| Directory | Purpose |
|---|---|
| [`deployment/`](deployment/) | Release, rollout, rollback, provenance, and deploy safety procedures. |
| [`database/`](database/) | PostgreSQL, Neo4j, Redis, backup, restore, HA, and data-store recovery procedures. |
| [`security/`](security/) | Data breach, abuse, tenant isolation, ransomware, and security-control incidents. |
| [`auth/`](auth/) | OIDC, SSO, Infisical/OIDC, Keycloak, and authentication anomaly procedures. |
| [`reliability/`](reliability/) | SLO breaches, service outages, cloud-provider outages, and readiness procedures. |
| [`agents/`](agents/) | Agent workflow stalls, LLM provider failures, model registry governance, and agent-cost incidents. |
| [`observability/`](observability/) | Alerting, Alertmanager, logging, dashboards, and telemetry procedures. |
| [`data-governance/`](data-governance/) | Ground-truth, audit evidence, formula approval, control attestation, and data-governance workflows. |
| [`customer-operations/`](customer-operations/) | Customer communications, postmortems, support coordination, and customer-facing incident operations. |

## Production procedure runbooks

| Production runbook | Owner | Severity default | Lifecycle phase | Related gate / validation | Existing equivalent runbooks |
|---|---|---:|---|---|---|
| [Incident command](01-incident-command.md) | Incident Commander / SRE on-call | SEV2 | Detect → review | `make verify` after code/config remediation; postmortem required for SEV1/SEV2 | [Severity classification](../troubleshooting/runbooks/incident/severity-classification.md), [Communication templates](../troubleshooting/runbooks/incident/communication-template.md), [Incident postmortem template](../troubleshooting/runbooks/incident/incident-postmortem-template.md) |
| Deployment rollout and rollback | Release Engineering / SRE | SEV2 | Deploy → recover | `make verify`; deployment smoke; signature/provenance checks | [docs/runbooks/deployment-rollout-and-rollback.md](deployment-rollout-and-rollback.md), [troubleshooting deployment rollout](../troubleshooting/runbooks/infrastructure/deployment-rollout-and-rollback.md), [troubleshooting rollback](../troubleshooting/runbooks/infrastructure/deployment-rollback.md), [operations ingress profile rollback](../operations/runbooks/ingress-profile-operations.md) |
| Release readiness checklist | Release Engineering | SEV3 | Deploy readiness | `make verify`; release smoke; contract checks | [Release checklist](../troubleshooting/runbooks/infrastructure/release-checklist.md), [Launch ops sign-off](operational/launch-ops-signoff-checklist.md) |
| Deployment signature and provenance verification | Release Engineering / Security | SEV2 | Deploy verify | Deployment signature/provenance verification gate | [Deployment signature verification](../troubleshooting/runbooks/infrastructure/deployment-signature-verification.md) |
| Backup and disaster recovery | SRE / Database Reliability | SEV1 | Recover | DR drill; restore validation; RTO/RPO evidence | [docs/runbooks/backup-disaster-recovery.md](backup-disaster-recovery.md), [troubleshooting backup DR](../troubleshooting/runbooks/incident/backup-disaster-recovery.md), [DR evidence log template](../troubleshooting/runbooks/incident/dr-evidence-log-template.md), [DR region loss game day](../troubleshooting/runbooks/incident/dr-gameday-region-loss.md), [DR service failover game day](../troubleshooting/runbooks/incident/dr-gameday-service-failover.md) |
| PostgreSQL HA and restore | Database Reliability | SEV1 | Contain → recover | Migration-head check; restore verification; tenant-boundary regression where data access changed | [PostgreSQL HA](postgres-ha.md), [PostgreSQL backup/restore](../troubleshooting/runbooks/infrastructure/postgres-backup-restore.md) |
| Neo4j HA, backup, restore, and auth recovery | Knowledge Graph / Database Reliability | SEV1 | Contain → recover | Graph health checks; restore validation; tenant-scoped graph query verification | [Neo4j HA](neo4j-ha.md), [Neo4j backup/restore](neo4j-backup-restore.md), [Neo4j auth rate-limit recovery](neo4j-auth-rate-limit-recovery.md), [Neo4j encryption key rotation](../troubleshooting/runbooks/infrastructure/neo4j-encryption-key-rotation.md) |
| Tenant isolation failure | Security / Platform Governance | SEV1 | Detect → contain | Tenant-boundary tests; audit evidence review; security review | [troubleshooting tenant isolation failure](../troubleshooting/runbooks/incident/tenant-isolation-failure.md), [operations tenant isolation failure alert](../operations/runbooks/tenant-isolation-failure.md) |
| Data breach response | Security / Legal / Incident Commander | SEV1 | Detect → review | Security incident checklist; audit-log integrity checks; customer notification workflow | [Data breach response](../troubleshooting/runbooks/incident/data-breach-response.md), [Ransomware response](../troubleshooting/runbooks/incident/ransomware-response.md) |
| Abuse emergency controls | Security / SRE | SEV1 | Contain | Rate-limit and abuse-control validation; audit event review | [Abuse emergency controls](operational/abuse-emergency-controls.md), [Zero-trust validation](../troubleshooting/runbooks/application/zero-trust-validation.md) |
| Enterprise OIDC / SSO incident | Identity Platform / Security | SEV2 | Detect → recover | Auth integration tests; customer SSO smoke; audit-log review | [Enterprise OIDC / SSO incident](operational/enterprise-oidc-sso-incident.md), [Auth anomaly alert](../operations/runbooks/auth-anomaly.md) |
| CI Infisical OIDC recovery and secret rotation | Platform Engineering / Security | SEV2 | Contain → recover | CI secret injection validation; GitHub OIDC verification | [CI Infisical OIDC recovery](operational/ci-infisical-oidc-recovery.md) |
| Cloud provider outage | SRE / Incident Commander | SEV1 | Detect → recover | DR failover validation; cloud-provider status evidence | [Cloud provider outage](../troubleshooting/runbooks/incident/cloud-provider-outage.md) |
| Service outage and SLO breach | SRE / Service owner | SEV1 | Detect → recover | SLO burn-rate review; service smoke; `make verify` after remediation | [Service down](../troubleshooting/runbooks/infrastructure/service-down.md), [SLO breach response](../troubleshooting/runbooks/application/slo-breach-response.md) |
| Layer 6 health and readiness | Layer 6 owner / SRE | SEV2 | Detect → recover | Layer 6 readiness probe; benchmark service smoke | [Layer 6 health readiness](operational/layer6-health-readiness.md) |
| Agent workflow stall | Layer 4 Agents owner | SEV2 | Detect → recover | Agent workflow regression tests; checkpoint/resume validation; evals when prompts/tools changed | [Agent workflow stall](../troubleshooting/runbooks/application/agent-workflow-stall.md), [Workflow stalled](../troubleshooting/runbooks/application/workflow-stalled.md) |
| LLM provider outage and agent cost anomalies | Layer 4 Agents owner / FinOps | SEV2 | Detect → contain | Provider failover smoke; budget threshold validation; agent evals when behavior changed | [LLM provider outage](../troubleshooting/runbooks/application/llm-provider-outage.md), [High LLM cost](../troubleshooting/runbooks/application/high-llm-cost.md), [LLM cost anomaly](../troubleshooting/runbooks/application/llm-cost-anomaly.md), [Budget exceeded](../troubleshooting/runbooks/application/budget-exceeded.md), [Token spike](../troubleshooting/runbooks/application/token-spike.md) |
| Model registry governance incident | Layer 4 Agents owner / Platform Governance | SEV2 | Detect → review | Model registry governance review; evals for changed model behavior | [Model registry governance incident](operational/model-registry-governance-incident.md) |
| Alerting source of truth and Alertmanager secret management | Observability / SRE | SEV2 | Deploy → detect | Alert rule lint; Alertmanager config validation; secret rotation evidence | [Alerting source of truth](operational/alerting-source-of-truth.md), [Alerting deployment checklist](../troubleshooting/runbooks/infrastructure/alerting-deployment-checklist.md), [Alertmanager secret management](../troubleshooting/runbooks/infrastructure/alertmanager-secret-management.md) |
| SIEM webhook outage and replay | Security / Observability | SEV2 | Detect → recover | SIEM delivery replay validation; audit event completeness | [SIEM webhook outage and replay](../troubleshooting/runbooks/application/siem-webhook-outage-and-replay.md) |
| Audit write failure | Platform Governance / Service owner | SEV1 | Detect → contain | Audit-write regression; tenant-isolation and governance evidence review | [Audit write failure](../troubleshooting/runbooks/application/audit-write-failure.md) |
| Ground-truth freshness and formula approval | Layer 5 Ground Truth / Data Governance | SEV2 | Detect → remediate | Ground-truth validation; formula approval checks | [Formula approval](formula-approval.md), [troubleshooting formula approval](../troubleshooting/runbooks/application/formula-approval.md), [Stale ground truth](../troubleshooting/runbooks/application/stale-ground-truth.md) |
| Quarterly control attestation | Compliance / Security | SEV3 | Review | Control attestation evidence review | [Quarterly control attestation](compliance/quarterly-control-attestation.md) |
| Customer communication and postmortem | Customer Operations / Incident Commander | SEV2 | Communicate → review | Postmortem completion; customer notification audit | [Communication templates](../troubleshooting/runbooks/incident/communication-template.md), [Incident postmortem template](../troubleshooting/runbooks/incident/incident-postmortem-template.md) |

## Alert-specific runbooks preserved in place

The following runbooks are tactical alert responses, not canonical production procedure runbooks. Keep them in their current alert directories unless a future migration creates a dedicated canonical procedure under one of the new `docs/runbooks/` category directories.

| Alert runbook | Owner | Severity default | Lifecycle phase | Related gate / validation | Existing runbook |
|---|---|---:|---|---|---|
| HighErrorRate | SRE / Service owner | SEV1 | Detect → remediate | Service smoke; regression test for changed service | [High error rate](../troubleshooting/runbooks/application/high-error-rate.md) |
| LogErrorSpike | Observability / Service owner | SEV2 | Detect → triage | Log query validation; service owner review | [Log error spike](../operations/runbooks/log-error-spike.md) |
| LogPanicDetected | SRE / Service owner | SEV1 | Detect → contain | Crash-loop and panic regression validation | [Log panic detected](../operations/runbooks/log-panic-detected.md) |
| LogDatabasePoolExhaustion | Database Reliability | SEV1 | Detect → contain | Connection-pool metrics and load validation | [Database pool exhaustion](../operations/runbooks/database-pool-exhaustion.md) |
| DiskSpaceLow | SRE | SEV2 | Detect → contain | Disk usage validation | [Disk space low](../troubleshooting/runbooks/infrastructure/disk-space-low.md) |
| DiskSpaceCritical | SRE | SEV1 | Detect → contain | Disk usage validation; service recovery smoke | [Disk space critical](../troubleshooting/runbooks/infrastructure/disk-space-critical.md) |
| DiskInodeExhaustion | SRE | SEV2 | Detect → contain | Inode usage validation | [Disk inode exhaustion](../troubleshooting/runbooks/infrastructure/disk-inode-exhaustion.md) |
| HighCPUUsage | SRE / Service owner | SEV2 | Detect → triage | Resource dashboard review; service smoke | [High CPU usage](../troubleshooting/runbooks/infrastructure/high-cpu-usage.md) |
| HighMemoryUsage | SRE / Service owner | SEV2 | Detect → triage | Resource dashboard review; service smoke | [High memory usage](../troubleshooting/runbooks/infrastructure/high-memory-usage.md) |
| SlowQueries | Database Reliability / Service owner | SEV2 | Detect → remediate | Query-plan review; tenant-scoped query validation | [Slow queries](../troubleshooting/runbooks/application/slow-queries.md) |
| Neo4jDown / Neo4jUnreachable | Knowledge Graph / Database Reliability | SEV1 | Detect → recover | Graph health checks; service smoke | [Neo4j down](../troubleshooting/runbooks/infrastructure/neo4j-down.md), [Neo4j unreachable](../troubleshooting/runbooks/infrastructure/neo4j-unreachable.md) |
| PostgresDown / PostgresUnreachable | Database Reliability | SEV1 | Detect → recover | DB health checks; service smoke | [Postgres down](../troubleshooting/runbooks/infrastructure/postgres-down.md), [Postgres unreachable](../troubleshooting/runbooks/infrastructure/postgres-unreachable.md) |
| RedisDown / RedisUnreachable | SRE / Platform Engineering | SEV2 | Detect → recover | Cache/queue health checks; service smoke | [Redis down](../troubleshooting/runbooks/infrastructure/redis-down.md), [Redis unreachable](../troubleshooting/runbooks/infrastructure/redis-unreachable.md) |
| AuthAnomaly | Identity Platform / Security | SEV2 | Detect → triage | Auth log review; audit event validation | [Auth anomaly](../operations/runbooks/auth-anomaly.md) |
| FormulaApprovalRequired | Layer 5 Ground Truth / Data Governance | SEV2 | Detect → remediate | Formula approval workflow validation | [Formula approval](../troubleshooting/runbooks/application/formula-approval.md) |
| StaleGroundTruthObjects | Layer 5 Ground Truth / Data Governance | SEV2 | Detect → remediate | TruthObject validation and freshness checks | [Stale ground truth](../troubleshooting/runbooks/application/stale-ground-truth.md) |
| WorkflowStalled | Layer 4 Agents owner | SEV2 | Detect → recover | Checkpoint/resume and workflow tests | [Workflow stalled](../troubleshooting/runbooks/application/workflow-stalled.md) |
| L2CostBudgetThreshold / L2HighExtractionCost / L2TokenUsageSpike | Layer 2 Extraction owner / FinOps | SEV2 | Detect → contain | Cost budget and token usage validation | [Budget exceeded](../troubleshooting/runbooks/application/budget-exceeded.md), [LLM cost anomaly](../troubleshooting/runbooks/application/llm-cost-anomaly.md), [Token spike](../troubleshooting/runbooks/application/token-spike.md) |

## Operational scripts that are not gates

The files under [`docs/runbooks/operational/`](operational/) include manual operational scripts and checklists. They are retained for incident response and operational validation, but they are not automated CI gates unless a specific production procedure above names them as validation evidence.
