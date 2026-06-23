# Queue Backlog Runbook

## Purpose

Recover delayed ingestion, extraction, agent, billing, or background jobs while
preserving job lifecycle semantics, provenance, tenant scope, and auditability.

## Trigger

- Redis/Celery backlog growth, stale workflow alerts, delayed ingestion,
  extraction batches not progressing, agent workflows stalled, or webhook replay
  queues accumulating.

## Severity

- SEV-1 when queues block customer-critical workflows globally, data loss is
  suspected, jobs process under the wrong tenant, or destructive replay risk
  exists.
- SEV-2 when backlog delays major workflows but data is safe and replayable.
- SEV-3 when backlog is bounded, tenant-specific, or non-critical.

## Preconditions

- Access to queue dashboards, worker logs, job state, Redis metrics, task IDs,
  tenant IDs from authenticated context, and downstream dependency health.
- Incident commander approval before purging, replaying, requeueing, or changing
  worker concurrency broadly.

## Immediate Actions

1. Declare severity and identify affected queue, worker group, and layer.
2. Capture backlog size, oldest job age, failed task classes, affected tenants,
   worker health, and recent deploy/config changes.
3. Pause non-critical producers if backlog growth risks data integrity or
   customer-visible delay.
4. Preserve task IDs, retry counts, error payloads, and provenance metadata.

## Diagnosis Steps

1. Determine whether the backlog is producer surge, worker crash, dependency
   outage, poisoned task, rate limit, lock contention, or capacity limit.
2. Check worker logs for repeated exceptions and verify failures do not expose
   secrets or tenant data.
3. Confirm jobs are tenant-scoped and do not process tenant IDs from untrusted
   request bodies.
4. Identify whether retries are idempotent and whether downstream systems can
   absorb replay.
5. Check database, auth, provider, and billing dependencies before replay.

## Resolution Steps

1. Fix or isolate poisoned jobs before increasing concurrency.
2. Scale workers or restart unhealthy workers only after dependency health is
   confirmed.
3. Replay or requeue jobs in tenant-scoped batches with evidence capture.
4. Avoid purging queues unless the incident commander and service owner approve
   documented data-loss or duplicate-processing risk.

## Validation

- Backlog age and depth return to expected ranges.
- Failed task rate declines and worker health is stable.
- Representative affected jobs complete successfully.
- Provenance, audit, and tenant ownership are preserved.
- Customer workflows depending on the queue recover.

## Rollback / Fallback

- Revert recent worker, producer, or queue configuration changes when correlated.
- Temporarily pause non-critical producers or throttle ingestion when downstream
  systems are degraded.

## Customer / Stakeholder Communication

- Communicate delayed workflow impact and expected recovery behavior.
- Do not expose internal queue names, tenant identifiers, raw payloads, or
  provider responses externally.

## Evidence to Preserve

- Queue metrics, task IDs, oldest job age, failed job samples, worker logs,
  retry/replay decisions, deployment SHA, tenant-scope evidence, and validation
  output.

## Escalation

- Escalate to affected layer owner, SRE, database owner for downstream
  contention, Security for tenant or data risk, and Customer Operations for
  workflow delay communications.

## Related Runbooks

- [Incident response workflow](../README.md)
- [Database degradation](database_degradation.md)
- [API outage](api_outage.md)
- [Billing webhook failure](billing_webhook_failure.md)

## Post-Incident Follow-Up

- Add backlog age alerts, idempotency tests, poison-task handling, or replay
  controls discovered missing during the incident.
