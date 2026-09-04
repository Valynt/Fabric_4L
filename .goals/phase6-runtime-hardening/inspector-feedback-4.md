# Inspector Feedback — Iteration 4

## Verdict: FAIL

## Acceptance Criteria Check

- [ ] AC1 — FAILED: `/v1/runtime/metrics` is privileged, but ordinary authenticated tenants can still read the same global aggregate counters through `/v1/runtime/health` (`runtime.py:155-170`), bypassing the new gate.
- [ ] AC2 — FAILED: runtime paths remain present, but the committed OpenAPI is stale after the metrics route change; the full contract compliance/freshness gate reports drift in `contracts/openapi/layer4-agents.json` and generated Layer 4 clients.
- [x] AC3 — verified: the previously accepted async HTTP transport and canonical error mapping are unchanged by this iteration.
- [x] AC4 — verified: additive engine deprecation and documented facade deferral remain unchanged.
- [x] AC5 — verified: the previously accepted contract-breaking-change policy remains present.
- [ ] AC6 — FAILED: the new metadata, metrics-route, and both checkpoint-adapter hostile tests pass, but no hostile test asserts that an ordinary tenant cannot obtain global metrics through `/v1/runtime/health`.
- [ ] AC7 — FAILED: targeted tests, type-escape ratchet, route matrix, and API-type check pass, but the required full contract compliance/freshness gate fails.
- [ ] AC8 — FAILED: independent verification found a metrics authorization bypass and committed contract drift.

## Quality Gate

- Command: `python -m pytest tests/unit/test_runtime_routes.py tests/unit/test_runtime_checkpoint_inmemory.py tests/unit/test_runtime_checkpoint_postgres.py -q --tb=short` (from `services/layer4-agents`)
- Result: PASS
- Details: 28 passed, 4 warnings.
- Command: `python scripts/ci/type_escape_ratchet.py`
- Result: PASS
- Details: 7247 approved occurrences; no net-new escapes.
- Command: `python scripts/ci/check_layer4_route_contract_matrix.py`
- Result: PASS
- Details: Layer 4 route contract matrix passed.
- Command: `pnpm run check:api-types`
- Result: PASS
- Details: Existing generated frontend API types are internally fresh.
- Command: `python scripts/ci/contract_compliance_gate.py --mode full`
- Result: FAIL
- Details: Fresh export detected drift in `contracts/openapi/layer4-agents.json`, `apps/web/src/api/generated/l4/index.ts`, and `packages/platform-contract/src/typescript/generated/layer4_agents.ts`.

## Issues Found

1. `services/layer4-agents/src/layer4_agents/api/routes/runtime.py:155-170` returns `_metrics_snapshot(metrics)` from the tenant-accessible health route. Those are the same global counters protected at `runtime.py:174-182`, so an ordinary tenant can bypass the privileged metrics route and infer cross-tenant activity.
2. The OpenAPI artifact still describes metrics as available to “an authenticated tenant principal” while source now says privileged operator. A fresh contract export changes the Layer 4 OpenAPI and generated clients; therefore the contract-first hard gate is not green.
3. The four requested fixes otherwise exist: caller authz metadata keys are stripped before runtime submission, background context uses the canonical `system` role, `/metrics` uses `require_privileged_access`, and both checkpoint adapters raise `TenantRequiredError` on absent tenant IDs. Their targeted hostile tests execute successfully.

## What Must Be Fixed

- Remove global counters from the ordinary-tenant `/v1/runtime/health` response, tenant-scope them, or gate that response equivalently; add a hostile test proving ordinary tenants cannot retrieve global activity through health.
- Regenerate and commit the Layer 4 OpenAPI and generated clients after the authorization/description change, then make `python scripts/ci/contract_compliance_gate.py --mode full` pass.
- Preserve the currently passing metadata isolation, canonical `system` background role, checkpoint fail-closed tests, ratchet, and route matrix.
