# SIEM Outbound Audit Schema (v1)

This document defines the outbound webhook schema used by `SIEMAuditSink` in `packages/shared/src/value_fabric/shared/audit/siem_integration.py`.

## Envelope

- `schema_version` — fixed string (`v1`).
- `event_id` — globally unique immutable audit event UUID.
- `tenant_id` — owning tenant UUID (nullable for platform-wide actions).
- `actor.user_id` — human or service principal user ID.
- `actor.api_key_id` — API key identifier when API-key auth is used.
- `action` — canonical audit action string from `AuditAction`.
- `target.resource_type` — resource class affected (e.g., `Workflow`, `Tenant`).
- `target.resource_id` — resource identifier.
- `outcome` — `success|failure|partial|denied`.
- `trace.request_id` — request correlation ID.
- `trace.trace_id` — distributed tracing ID (when available).
- `timestamps.created_at` — original internal event timestamp (UTC ISO-8601).
- `timestamps.dispatched_at` — SIEM transport dispatch timestamp (UTC ISO-8601).
- `details` — redacted event metadata map.

## Field-level Mapping

| SIEM field | Internal source |
|---|---|
| `event_id` | `AuditEvent.id` |
| `tenant_id` | `AuditEvent.tenant_id` |
| `actor.user_id` | `AuditEvent.user_id` |
| `actor.api_key_id` | `AuditEvent.api_key_id` |
| `action` | `AuditEvent.action` |
| `target.resource_type` | `AuditEvent.resource_type` |
| `target.resource_id` | `AuditEvent.resource_id` |
| `outcome` | `AuditEvent.outcome` |
| `trace.request_id` | `AuditEvent.request_id` |
| `trace.trace_id` | optional caller-supplied `trace_id` |
| `timestamps.created_at` | `AuditEvent.timestamp` |
| `timestamps.dispatched_at` | sink delivery clock |
| `details` | redacted `AuditEvent.details` |

## Transport Security + Idempotency

- `Authorization` header is optional and configured via `SIEMDeliveryConfig.auth_header`.
- `X-Signature-SHA256` HMAC is optional and configured via `SIEMDeliveryConfig.signature_secret`.
- `X-Event-ID` and `Idempotency-Key` both carry `event_id`.
- Duplicate suppression is enforced in-memory per sink process via a delivered-event ID set.

## SLO Guardrail

- Delivery SLO target: successful SIEM delivery in under 5 minutes (`300s`) from `timestamps.created_at`.
- `SIEMAuditSink.metrics.slo_breaches_total` increments on successful deliveries that exceed the threshold.
- Alerting should trigger when `slo_breaches_total > 0` in any 5-minute evaluation window.
