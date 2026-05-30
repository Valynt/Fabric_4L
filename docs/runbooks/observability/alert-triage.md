# Alert Triage Runbook

## Purpose

Provide a consistent first-response workflow for Value Fabric alerts so responders classify severity, preserve evidence, select the right tactical runbook, and validate recovery without suppressing true production risk.

## Trigger

- Pager, Slack, monitoring dashboard, log query, synthetic probe, SLO burn alert, readiness gate, CI gate, or customer signal indicates anomalous production behavior.
- Alert-specific runbook is missing, stale, ambiguous, or points to a broader incident procedure.

## Severity

- **SEV1:** Alert indicates complete outage, data loss, tenant-isolation/security risk, credential compromise, critical dependency outage, or fast SLO burn with customer impact.
- **SEV2:** Major workflow/layer degraded, bounded partial data loss, deployment regression, or sustained error/latency affecting many users.
- **SEV3:** Minor feature degradation, single-tenant issue, non-critical alert with workaround, or slow burn requiring owner action.
- **SEV4:** No customer impact, cosmetic/dashboard issue, alert label drift, or confirmed false positive.

## Preconditions

- Responder has access to alert payload, dashboard, logs, traces, metrics, deployment history, runbook index, and escalation contacts.
- Alert source-of-truth and ownership are known or can be discovered from labels/service metadata.
- Evidence capture is performed before silencing, restarting, rolling back, or rotating credentials.

## Immediate Actions

1. Acknowledge the alert and record alert name, source, UTC timestamp, severity guess, affected environment, service/layer, and tenant/customer scope if known.
2. Check whether multiple alerts point to the same underlying incident; open incident command for SEV1/SEV2 or cross-functional impact.
3. Preserve alert payload, dashboard links, log/traces query links, deployment SHA, and recent change context.
4. Select the tactical runbook from `docs/runbooks/00-runbook-index.md` or alert-specific troubleshooting runbooks.
5. Silence only duplicate/noisy pages after an owner is assigned and the active incident record links to the silence.

## Diagnosis Steps

1. Confirm whether the alert is firing, resolved, flapping, or stale.
2. Validate the signal with at least one independent source: logs, traces, metrics, synthetic checks, customer reports, health endpoints, or CI/readiness output.
3. Determine likely category: deployment, database, auth, security, dependency, capacity, application error, contract drift, data quality, or observability defect.
4. Check recent deploys, migrations, config/secret changes, feature flags, dependency status, and traffic spikes.
5. Identify the safest immediate mitigation or the owner/runbook needed for deeper response.

## Resolution Steps

1. If the alert is valid and customer/security/data impact exists, escalate to incident command and follow the tactical runbook.
2. If the alert is valid but bounded, assign the service owner, mitigate the root cause, and record validation evidence.
3. If the alert is a false positive, document why, attach evidence, and file an alert tuning issue before closing.
4. If observability is impaired, preserve what evidence exists, use customer/synthetic/manual checks, and restore telemetry as a priority.
5. Do not silence, disable, or lower thresholds for production alerts without owner approval and a replacement detection path.

## Validation

- Confirm the original alert resolves or is intentionally silenced with linked incident/owner.
- Confirm independent health signal returns to baseline.
- Confirm customer-critical paths work when customer impact was suspected.
- Confirm no related security, tenant-isolation, auth, data, or deployment alerts remain active.
- Confirm follow-up issue exists for false positive, missing runbook, stale owner, or weak signal.

## Rollback / Fallback

- Roll back recent deployment/config only when evidence links it to the alert and rollback is safer than forward fix.
- If telemetry is unavailable, use service health endpoints, synthetic smoke checks, customer support reports, and infrastructure status as temporary signals.
- If no owner is known, escalate through incident command rather than leaving the alert unowned.

## Customer / Stakeholder Communication

- Customer Operations is notified for customer-visible SEV1/SEV2 alerts or repeated SEV3 issues.
- Internal updates should include alert name, impact, mitigation, owner, and next update time.
- Do not communicate unconfirmed root cause externally.

## Evidence to Preserve

- Alert payload, labels, thresholds, expression/query, dashboard links, screenshots, logs/traces/metrics, active silences, and alert history.
- Deployment/config/secret changes, incident timeline, owner handoff, mitigation commands, validation outputs, and false-positive analysis.

## Related Gates

- Observability alert gates and synthetic probes.
- Service health/readiness checks.
- `make verify`
- `make contract-tests`
- Deployment, migration, tenant-boundary, security, backup/restore, and frontend verification gates based on alert category.

## Related Runbooks

- [Incident command](../01-incident-command.md)
- [Deploy production release](../deployment/deploy-production-release.md)
- [Failed deployment](../deployment/failed-deployment.md)
- [Rollback production release](../deployment/rollback-production-release.md)
- [Failed migration](../database/failed-migration.md)
- [Respond to tenant data exposure](../security/respond-to-tenant-data-exposure.md)
- [Auth provider outage](../auth/auth-provider-outage.md)
- [Runbook index](../00-runbook-index.md)

## Post-Incident Follow-Up

- Tune thresholds, labels, ownership, dashboards, and runbook links based on triage outcome.
- Add missing alerts for discovered blind spots and remove duplicate noise only after replacement coverage exists.
- Update the runbook index if a new alert class or tactical runbook is needed.
