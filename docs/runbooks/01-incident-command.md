# Incident Command Runbook

## Scope

Use this runbook to start and run any production incident, customer-impacting degradation, suspected data integrity issue, or suspected security event. It consolidates the severity expectations from the legacy severity classification runbook into the canonical Phase 1 runbook path.

## Severity

If impact is unclear, classify at the higher severity until the Incident Commander documents evidence for a downgrade.

| Severity | Definition | Initial response target | Incident Commander required | Update cadence |
|---|---|---:|---|---:|
| **SEV1** | Complete outage, data loss, confirmed or suspected security breach, cross-tenant exposure, credential compromise, or ransomware indicator. | 15 minutes | Yes | Every 15 minutes until mitigated |
| **SEV2** | Major feature degraded, one production layer unavailable with workaround, bounded partial data loss, or restore required for a bounded dataset. | 1 hour | Yes | Every 30 minutes until mitigated |
| **SEV3** | Minor feature issue with documented workaround, single non-critical workflow degraded, or latency below SLO breach thresholds. | 4 hours | Optional | Every 2 hours or on material change |
| **SEV4** | Cosmetic or non-user-facing issue with no customer impact. | 24 hours | No | Owner discretion |

Security and data-integrity events start as **SEV1** until Security or the Incident Commander records a downgrade with evidence.

## Immediate Actions

1. Open the incident channel and declare severity, affected service or tenant scope, and current customer impact.
2. Assign Incident Commander, Technical Lead, Communications Lead, Scribe, and Security/Privacy Lead when applicable.
3. Start a timeline with UTC timestamps for every decision, command, mitigation, escalation, and customer communication.
4. Freeze non-essential deploys for affected services unless a deploy is the approved containment or recovery action.
5. Preserve volatile evidence before restarts, rollbacks, scale-downs, or destructive cleanup.
6. Select the focused runbook for the failure domain and link it in the incident channel.
7. Set the next update time based on severity and keep customer/status-page messaging synchronized with internal facts.

## Diagnosis and Coordination

```bash
# Capture current cluster events before they age out.
kubectl get events -A --sort-by=.lastTimestamp | tail -200

# Identify unhealthy workloads across namespaces.
kubectl get pods -A -o wide | rg -i "crashloop|error|pending|terminating|imagepull|oom"

# Capture recent deploy history for affected services.
git log --oneline --since='48 hours ago' -- services packages value_fabric contracts apps/web k8s
```

Use facts, not theories, in incident updates. Separate **confirmed**, **likely**, **possible**, and **ruled out** findings.

## Validation

- Incident roles are assigned and acknowledged.
- Severity, customer impact, affected services, and current mitigation are documented in the incident channel.
- Evidence links are stored in the evidence log or incident document.
- Status page or customer communication cadence matches the severity table.
- A focused remediation runbook is active, or the Incident Commander explicitly records why no focused runbook applies.
- Closure has named owners for corrective actions and post-incident review when required.

## Evidence to Preserve

- Alert payloads, dashboard snapshots, and paging timestamps.
- Incident channel transcript and decision log.
- Request IDs, trace IDs, audit logs, gateway logs, application logs, and Kubernetes events.
- Release SHAs, image digests, feature-flag changes, migration versions, and configuration diffs.
- Customer reports, support tickets, and approved external communications.

## Related Gates

- `make verify`
- `make contract-tests`
- `make check-conflict-markers`
- `make check-pytest-skip-governance`
- `pnpm run check:contract-compliance`
- `pnpm run check:api-types`

## Related Runbooks

- [Deploy Production Release](deployment/deploy-production-release.md)
- [Rollback Production Release](deployment/rollback-production-release.md)
- [Failed Deployment](deployment/failed-deployment.md)
- [Restore Postgres From Backup](database/restore-postgres-from-backup.md)
- [Failed Migration](database/failed-migration.md)
- [Respond to Tenant Data Exposure](security/respond-to-tenant-data-exposure.md)
- [Respond to Secret Leak](security/respond-to-secret-leak.md)
- [Auth Provider Outage](auth/auth-provider-outage.md)
- [Alert Triage](observability/alert-triage.md)
