# Billing Webhook Failure Runbook

## Purpose

Restore billing webhook ingestion, verification, processing, and replay without
duplicating customer charges, losing entitlement changes, or exposing sensitive
billing data.

## Trigger

- Billing provider webhook delivery failures, signature verification failures,
  replay queue backlog, entitlement sync drift, subscription state mismatch, or
  customer reports of incorrect billing status.

## Severity

- SEV-1 when webhook handling risks duplicate charges, lost payments, broad
  entitlement outage, data exposure, or irreversible billing state corruption.
- SEV-2 when billing events are delayed but replayable and customer access can
  be reconciled.
- SEV-3 when failures are isolated, bounded, and no revenue, entitlement,
  security, or data-integrity risk exists.

## Preconditions

- Access to billing provider dashboard, webhook delivery logs, signature secret
  metadata, replay queue, entitlement state, audit logs, and customer support
  context.
- Finance or billing owner approval before manual billing state changes,
  refunds, retries with charge impact, or customer-specific billing statements.

## Immediate Actions

1. Declare severity and assign billing technical lead.
2. Capture provider event IDs, affected tenants/customers, failed delivery
   timestamps, signature errors, replay state, and current entitlement impact.
3. Pause risky automated retries if duplicate processing or charge impact is
   possible.
4. Preserve raw provider event references, but do not post sensitive payloads in
   public incident channels.

## Diagnosis Steps

1. Determine whether the failure is provider delivery, endpoint availability,
   signature verification, secret rotation, idempotency, queue backlog, database
   write, or entitlement propagation.
2. Confirm webhook idempotency keys and event IDs are enforced.
3. Verify failed events are tenant-scoped and mapped to trusted billing records,
   not request-body tenant values.
4. Check recent deploys, secret rotations, provider configuration, endpoint URL,
   and network changes.
5. Compare provider event state against internal billing and entitlement state.

## Resolution Steps

1. Restore endpoint availability or correct provider/secret configuration.
2. Replay failed events in chronological, idempotent, tenant-scoped batches.
3. Reconcile entitlements against provider source of truth before manual
   correction.
4. Escalate before refunds, manual subscription edits, destructive replay, or
   secret rotation.
5. Record every replay, reconciliation, and manual adjustment.

## Validation

- Webhook signature verification succeeds.
- New provider events process successfully.
- Failed events are replayed exactly once or documented as intentionally skipped.
- Internal billing and entitlement state matches provider source of truth.
- Audit records exist for replay and manual correction.

## Rollback / Fallback

- Roll back recent webhook handler, endpoint routing, or secret config changes
  when correlated.
- Temporarily reconcile entitlements manually only with billing owner approval
  and audit evidence.

## Customer / Stakeholder Communication

- Coordinate customer billing statements with Customer Operations and Finance.
- Legal/Privacy approval is required before discussing sensitive billing data or
  security/privacy impact.

## Evidence to Preserve

- Provider event IDs, delivery logs, signature verification errors, replay
  commands, idempotency records, entitlement diffs, audit events, deployment SHA,
  and validation results.

## Escalation

- Escalate to billing service owner, Finance, SRE, Security for data or secret
  risk, Legal/Privacy for customer-impacting billing or data statements, and
  Customer Operations for customer follow-up.

## Related Runbooks

- [Incident response workflow](../README.md)
- [Queue backlog](queue_backlog.md)
- [API outage](api_outage.md)
- [Auth failure](auth_failure.md)

## Post-Incident Follow-Up

- Add missing idempotency, replay, reconciliation, provider config, or alerting
  coverage. Assign owners and due dates in the postmortem.
