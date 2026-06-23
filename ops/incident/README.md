# Incident Response Workflow

Use this workflow for production incidents affecting Value Fabric availability,
auth, data stores, queues, billing webhooks, tenant isolation, security,
customer trust, or production readiness controls.

## Incident Lifecycle

1. **Detect**: alert, customer report, support escalation, deploy gate failure,
   or operator observation identifies production risk.
2. **Declare**: classify severity with [severity_matrix.md](severity_matrix.md),
   open an incident channel, and assign incident commander, technical lead,
   communications lead, and scribe.
3. **Triage**: identify affected layer, tenant scope, first-bad timestamp,
   current deploy SHA, active alerts, and likely blast radius.
4. **Mitigate**: follow the matching runbook in [runbooks/](runbooks/) or the
   broader [docs runbook index](../../docs/runbooks/00-runbook-index.md).
5. **Communicate**: use [customer_comms_template.md](customer_comms_template.md)
   and follow the cadence in [escalation_policy.md](escalation_policy.md).
6. **Resolve**: confirm recovery through service health, customer-critical
   workflow checks, logs, metrics, traces, and audit evidence.
7. **Postmortem**: complete [postmortem_template.md](postmortem_template.md)
   for every SEV-1, SEV-2, security/privacy incident, tenant-isolation incident,
   data-loss incident, and repeated SEV-3.

## First Actions

- Freeze non-essential production changes when availability, auth, data
  integrity, tenant isolation, or customer trust may be affected.
- Preserve evidence before restarts, rollbacks, credential rotation, data
  restore, queue purge, or destructive remediation.
- Do not trust request-body tenant IDs during incident analysis; use
  authenticated tenant context and audit evidence.
- Keep updates factual, time-stamped, and free of speculation.

## Failure-Mode Runbooks

| Failure mode | Runbook |
|---|---|
| API outage or severe error-rate spike | [api_outage.md](runbooks/api_outage.md) |
| Database degradation | [database_degradation.md](runbooks/database_degradation.md) |
| Queue backlog | [queue_backlog.md](runbooks/queue_backlog.md) |
| Auth failure | [auth_failure.md](runbooks/auth_failure.md) |
| Billing webhook failure | [billing_webhook_failure.md](runbooks/billing_webhook_failure.md) |

## Related Production References

- [Production runbook index](../../docs/runbooks/00-runbook-index.md)
- [Incident command runbook](../../docs/runbooks/01-incident-command.md)
- [Operations severity escalation policy](../../docs/operations/severity-escalation-policy.md)
- [Production readiness](../../docs/production-readiness.md)

## Validation

```bash
pnpm ops:runbooks:lint
pnpm ops:incident:check
```
