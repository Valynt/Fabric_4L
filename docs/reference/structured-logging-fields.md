# Structured Logging Field Dictionary

This reference standardizes JSON log fields across Layer 2, Layer 5, and Layer 6.

## Required core fields

- `event`: Stable event name (snake_case) for filtering/alerts.
- `level`: Log severity emitted by structlog.
- `timestamp`: UTC ISO-8601 timestamp.
- `tenant_id`: Authenticated tenant identifier.
- `request_id`: Request correlation ID (also mirrored into `correlation_id`).
- `correlation_id`: Alias of request ID for cross-layer compatibility.

## Common business identifiers

Include when relevant to the event type:

- `document_id` (Layer 2 extraction/inference context)
- `truth_object_id` (Layer 5 truth/governance context)
- `benchmark_id` (Layer 6 benchmark context)
- `entity_id` / `entity_type` (governance entity operations)
- `action` and `status` (governance workflow lifecycle)

## Security constraints

- Never log secrets, tokens, raw auth headers, or payload PII.
- Use stable identifiers, not free-form user input.
- Keep log records machine-parseable JSON.
