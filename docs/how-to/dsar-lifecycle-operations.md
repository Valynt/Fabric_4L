# DSAR Lifecycle Operations

## Lifecycle
1. Register request via `POST /v1/privacy/dsar`.
2. DSAR orchestration persists request, computes SLA deadline (`requested_at + 30 days`), and launches tenant-scoped export.
3. Reconciliation validates package completeness before status transitions to `complete`.
4. Package download is provided via short-lived signed URL tied to requester identity.

## Escalation policy
- Any request that is not complete after SLA deadline is escalated to `escalated` status.
- Operators should review daily and prioritize escalated requests.

## Audit evidence retention
Persist and retain:
- request ID
- lawful basis
- data categories
- redaction status
- completion evidence
- completion timestamp
- escalation timestamp (if applicable)
