# Alert Triage Runbook

## Scope

Use this runbook for first-response triage of PagerDuty, Alertmanager, Grafana, Loki, cloud, CI, and synthetic monitoring alerts. The goal is to classify severity, preserve evidence, route to the right focused runbook, and avoid premature silencing.

## Severity

Classify by customer impact, data integrity, and security risk rather than by the component that emitted the alert.

- **SEV1:** Complete outage, active data loss/corruption, suspected security breach, tenant exposure, credential compromise, or alert indicates multiple critical services unavailable.
- **SEV2:** Major feature or production layer degraded, bounded data recovery needed, or failed deployment impacting customers.
- **SEV3:** Minor degradation, noisy but real alert with workaround, or localized non-critical workflow issue.
- **SEV4:** Cosmetic/non-user-facing signal or confirmed false positive with no customer impact.

## Immediate Actions

1. Acknowledge the page according to severity target; do not silence before checking impact.
2. Capture alert payload, firing labels, dashboard link, query, threshold, and start time.
3. Check whether related alerts are firing across services, layers, infrastructure, auth, database, security, or deployment.
4. Determine customer impact and whether an incident channel is required.
5. Select the focused runbook for the alert domain and hand off to the service owner when needed.
6. Preserve logs/events before restarting pods, rolling back deploys, scaling down workloads, or changing alert rules.
7. If the alert is false positive, document why, adjust the alert only through reviewed change, and keep evidence.

## Diagnosis

```bash
# Snapshot current cluster health.
kubectl get pods -A -o wide | rg -i "crashloop|error|pending|imagepull|oom|evicted|terminating"
kubectl get events -A --sort-by=.lastTimestamp | tail -200

# Check recent deploys and commits that may correlate with alert start.
git log --oneline --since='48 hours ago' -- services packages value_fabric contracts apps/web k8s monitoring

# Pull recent logs for an affected service.
kubectl logs -n <namespace> -l app=<service> --since=30m --all-containers | tail -200
```

Record whether the signal is **user-impacting**, **data-impacting**, **security-impacting**, **capacity-impacting**, or **observability-only**.

## Validation

- Alert severity, customer impact, and affected scope are recorded.
- Focused runbook is linked, or false-positive rationale is documented.
- Alert is either resolved by remediation, routed to an active incident, or tracked as an owned follow-up.
- If silenced, silence has an owner, expiry, reason, and linked incident or ticket.
- Dashboards and logs confirm recovery before alert closure.
- Any alert-rule change is reviewed and does not hide tenant isolation, security, data integrity, or availability signals.

## Evidence to Preserve

- Alertmanager/PagerDuty payload, labels, annotations, threshold, and query.
- Dashboard snapshots before and after mitigation.
- Logs, traces, request IDs, Kubernetes events, and recent deployment evidence.
- Silence records, escalation notes, and handoff decisions.
- False-positive analysis and alert-rule change approval if applicable.

## Related Gates

- `make verify`
- `make contract-tests`
- `python3 scripts/ci/k8s_preflight.py`
- `make test-backend-integrated-release-smoke`
- `pytest tests/security`
- `pnpm run verify:frontend`

## Related Runbooks

- [Incident Command](../01-incident-command.md)
- [Deploy Production Release](../deployment/deploy-production-release.md)
- [Rollback Production Release](../deployment/rollback-production-release.md)
- [Failed Deployment](../deployment/failed-deployment.md)
- [Failed Migration](../database/failed-migration.md)
- [Respond to Tenant Data Exposure](../security/respond-to-tenant-data-exposure.md)
- [Respond to Secret Leak](../security/respond-to-secret-leak.md)
- [Auth Provider Outage](../auth/auth-provider-outage.md)
