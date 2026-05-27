# API Distributed Store Operational Expectations

This runbook covers the `services/api` distributed session/share-link store contract.

## Required environment variables

- `REDIS_URL` (required): Redis endpoint used by `RedisDistributedStore`.

If `REDIS_URL` is missing, API startup fails fast during lifespan readiness checks.

## Startup/readiness behavior

Before serving requests, the API now validates:

1. Redis is reachable (`PING`).
2. JSON serialization contract is round-trip compatible (`set_json` -> `get_json` -> `delete`).

A failure in either check prevents startup with a fatal initialization error.

## Runtime failure modes

`RedisDistributedStore` enforces consistent outage behavior:

- bounded retry with exponential backoff for Redis operations,
- circuit-breaker open state after repeated failures,
- reset window before retrying requests after open-circuit.

Contract-safe propagation:

- backend reachability failures raise `StoreUnavailableError`,
- malformed/non-object payloads raise `StorePayloadError`.

Routers map these to HTTP 503 for share-link and impersonation flows (fail closed).

## Alerting hooks

Trigger alerts on:

- startup failures containing `Distributed store initialization failed`,
- elevated HTTP 503 on `/v1/accounts/*/share` and `/v1/auth/impersonation/*`,
- recurring `Distributed store circuit is open` errors.

Suggested SLO signal: ratio of store-backed flow failures (503) over total store-backed requests.
