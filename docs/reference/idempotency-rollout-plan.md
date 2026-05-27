# Idempotency Rollout Plan (Mutating Routes)

## Implemented (Phase 1)

Shared idempotency primitives now live in `value_fabric/shared/idempotency` and are applied to high-impact account mutation routes:

- `POST /v1/accounts`
- `PATCH /v1/accounts/{account_id}`

Replay semantics for covered endpoints:

- Same tenant + same endpoint + same `Idempotency-Key` + same request fingerprint:
  - Returns stored `status/body/headers`
  - Adds `X-Idempotent-Replay: true`
- Same tenant + same endpoint + same `Idempotency-Key` + different request fingerprint:
  - Returns `409 Conflict`

Storage abstraction:

- `IdempotencyStore` protocol for pluggable persistence
- `InMemoryIdempotencyStore` reference implementation with TTL expiration

## Remaining Mutating Routes (Phase 2+)

Apply the same shared module incrementally to:

1. `POST/PATCH` routes in `services/api/app/routers/reviews.py`
2. `POST/PATCH` routes in `services/api/app/routers/value_cases.py`
3. `POST` workflow routes in `services/api/app/routers/agents.py`
4. External side-effect routes (`share`, exports, restore/cancel/resume endpoints) with stronger persistence backing

## Rollout Strategy

1. Introduce endpoint-level opt-in only (no global middleware auto-apply).
2. Cover each endpoint with:
   - duplicate replay test
   - payload mismatch conflict test
   - tenant isolation test
   - expiration test (for chosen backend)
3. Move from in-memory store to distributed persistence for multi-instance deployments.
4. Emit observability metrics for hit/miss/conflict and replay latency.
