# Progressive enforcement rollout for FastAPI services

This guide documents the staged rollout model for shared FastAPI enforcement controls.

## What changed

`create_fabric_app` now accepts `enforcement_rollout` with explicit control blocks:

- `tenant_enforcement`
- `rate_limiting`
- `idempotency`
- `health_checks`

Each control supports three modes:

- `off`: no block, treated as bypass
- `audit`: log violation / near-miss context and continue request
- `enforce`: block request when violation is detected

Default mode is `audit` to provide one release train of observation before fleet-wide enforcement.

## Per-route opt-out

Use `mark_route_enforcement_opt_out` for health/readiness routes and trusted internal callbacks:

```python
from value_fabric.shared.fastapi_framework import mark_route_enforcement_opt_out

@router.post("/internal/callback")
@mark_route_enforcement_opt_out(reason="internal_callback")
async def internal_callback() -> dict[str, str]:
    return {"status": "ok"}
```

`register_health_endpoint` applies this annotation automatically.

## Metrics/counters

The shared app state exposes structured counters:

- `app.state.enforcement_counters.blocked_total`
- `app.state.enforcement_counters.bypass_total`
- `app.state.enforcement_counters.false_positive_candidate_total`

Use `record_enforcement_decision(...)` inside middleware/guards to apply mode semantics and capture structured context (`tenant_id`, `route`, `actor_id`, `violation`).

## Canary adoption

`services/api` now sets `tenant_enforcement`, `rate_limiting`, and `idempotency` to `audit` explicitly as the first canary before fleet-wide default flip.

## Recommended rollout plan

1. Release with `audit` and collect counters + logs.
2. Confirm low false-positive candidate rate on canary service.
3. Promote a second service to `enforce` for one control at a time.
4. Flip defaults to `enforce` after release-train validation.
