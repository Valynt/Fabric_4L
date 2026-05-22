# Runbook: SIEM Webhook Outage and Replay

## Purpose

Respond to SIEM webhook delivery failures, contain alert impact, and safely replay dead-lettered audit events.

## Symptoms

- Elevated `failed_total` in `SIEMAuditSink.metrics`.
- Growth in `dead_letter_queue` backlog.
- `slo_breaches_total` incrementing due to delayed receipt.
- Upstream SIEM endpoint returns non-2xx or timeouts.

## Immediate Actions

1. Confirm endpoint and secret configuration:
   - `SIEMDeliveryConfig.endpoint`
   - `SIEMDeliveryConfig.auth_header`
   - `SIEMDeliveryConfig.signature_secret`
2. Validate network path/TLS from service to SIEM endpoint.
3. Keep event emission enabled (do **not** disable audit generation).
4. Verify dead-letter queue growth rate and projected replay window.

## Recovery Steps

1. Restore SIEM endpoint health (provider incident or internal proxy issue).
2. Trigger replay:
   - invoke `SIEMAuditSink.replay_dead_letters()` from an operational maintenance task/job.
3. Monitor replay success:
   - backlog should converge to zero.
   - duplicate suppression prevents duplicate resubmission of already-successful events.
4. Validate SLO recovery:
   - check new events return to <300s end-to-end delivery.

## Replay Safety Rules

- Preserve original `event_id` for idempotency.
- Preserve original `timestamps.created_at` for true latency measurement.
- Never replay raw unredacted details; sink redaction must remain enabled.
- Keep HMAC signatures enabled if required by the SIEM receiver.

## Escalation

Escalate to platform on-call when any condition persists beyond 15 minutes:

- Dead-letter backlog continues rising.
- Replay cannot drain backlog.
- SLO breaches continue after SIEM endpoint is healthy.

## Post-Incident

- Record outage start/end times and root cause.
- Capture max queue depth, replay duration, and data-loss confirmation.
- File follow-up for tuning retry/backoff and alert thresholds if needed.
