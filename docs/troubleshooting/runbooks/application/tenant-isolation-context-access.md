# Tenant Isolation Context Access

## Trigger

`InconsistentTenantContextAccess` fires when a canonical tenant boundary rejects a request or action because the trusted tenant context conflicts with an untrusted tenant hint or target tenant.

## Immediate Response

1. Treat the alert as a security incident until proven benign.
2. Identify the affected `layer`, `service`, `route`, and `source` labels in Prometheus or Alertmanager.
3. Correlate the request window with authentication logs, audit events, WAF logs, and application structured logs.
4. Confirm that the request was rejected and that no cross-tenant read or write succeeded.
5. If any data exposure is suspected, escalate to the security/governance owner and preserve logs before restarting services.

## Investigation

- `source="header"` indicates an `X-Tenant-ID` or equivalent request hint conflicted with authenticated context.
- `source="header_invalid"` indicates a malformed tenant hint reached the gateway.
- `source="target_tenant"` indicates an authorization helper rejected an action against a tenant outside the authenticated scope.

Check whether the event came from an expected negative test, a misconfigured integration, a stale client, or a hostile request. Do not whitelist the route unless the caller has a documented service-to-service authentication path and still preserves tenant ownership from trusted context.

## Recovery

- For client or integration drift, fix the caller to stop sending forged or stale tenant hints.
- For repeated hostile traffic, apply abuse controls and rate limiting before clearing the alert.
- For confirmed tenant isolation defects, block promotion, open a P0 security incident, and run tenant-boundary regression tests before recovery sign-off.

## Evidence

Record the alert timestamp, labels, request IDs, rejection logs, audit correlation, owner decision, and any follow-up ticket. Redact raw tokens, customer data, and tenant-identifying payload details before attaching evidence to launch records.
