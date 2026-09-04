# Inspector Feedback — Iteration 3

## Verdict: FAIL

## Acceptance Criteria Check

- [ ] AC1 — FAILED: routes are authenticated and registered, but caller-controlled run metadata is copied into `RuntimeContext.metadata`, which downstream authorization consumes as scopes/permissions when ambient context is absent. The metrics endpoint also exposes global counters to any authenticated tenant.
- [x] AC2 — verified: the Layer 4 OpenAPI contract contains seven runtime paths covering eight operations, generated artifacts are current, `pnpm run check:api-types` passes, and the full contract compliance gate is clean.
- [x] AC3 — verified: the previously accepted async HTTP SDK transport and canonical error mapping remain covered by passing unit tests.
- [x] AC4 — verified: additive engine deprecation remains registered in the deprecation budget and the documented facade deferral remains intact.
- [x] AC5 — verified: the previously accepted contract exception policy remains present.
- [ ] AC6 — FAILED: all 862 Layer 4 unit tests pass, but hostile coverage misses caller metadata self-grant, global cross-tenant metrics disclosure, and missing-tenant checkpoint load/list behavior.
- [x] AC7 — verified: unit tests, targeted Ruff, targeted mypy, type-escape ratchet, route-contract matrix, API type freshness, and full contract compliance all pass. `make verify` itself is environment-blocked on this Windows host as documented and is not treated as a failure.
- [ ] AC8 — FAILED: independent source review found tenant/authz hardening gaps despite the green mechanical gates.

## Quality Gate

- Command: `python -m pytest tests/unit -q --tb=short`
- Result: PASS
- Details: 862 passed, 8 warnings.
- Command: `ruff check src/layer4_agents/runtime src/layer4_agents/api/routes/runtime.py tests/unit/test_runtime_routes.py tests/unit/test_runtime_sdk_remote.py`
- Result: PASS
- Details: All checks passed.
- Command: `python -m mypy src/layer4_agents/runtime src/layer4_agents/api/routes/runtime.py`
- Result: PASS
- Details: No issues in 24 source files.
- Command: `python scripts/ci/type_escape_ratchet.py`
- Result: PASS
- Details: 7247 approved occurrences and no net-new escapes.
- Command: `python scripts/ci/check_layer4_route_contract_matrix.py`
- Result: PASS
- Details: Layer 4 route contract matrix check passed.
- Command: `pnpm run check:api-types`
- Result: PASS
- Details: Generated frontend API types are fresh.
- Command: `python scripts/ci/contract_compliance_gate.py --mode full`
- Result: PASS
- Details: Contract artifacts are fresh, backwards compatibility is clean, and frontend typecheck passes.

## Issues Found

1. `submit_runtime_run()` copies untrusted `body.metadata` directly into `RuntimeContext.metadata`. `PolicyAuthzPort` consumes reserved scope/permission keys from that metadata when no ambient request context exists, allowing caller-controlled authorization input.
2. `LangGraphWorkflowEngineAdapter._enter_execution_context()` synthesizes `roles=["tenant_admin"]` whenever ambient context is absent. Background execution therefore receives an implicit administrative role instead of least privilege.
3. `GET /v1/runtime/metrics` returns global aggregate counters after checking only that the caller is authenticated and has any tenant. This leaks cross-tenant activity rather than returning tenant-scoped data or requiring privileged access.
4. Both checkpoint adapters' `load()` and `list()` accept an empty tenant ID and silently return no data. That is not fail-closed behavior and lacks hostile tests.
5. The Layer 7 rewrite concern is resolved by the clarified branch-relative comparison. Against `origin/main`, the contract diff is 495 additions and zero deletions, consisting of generator-emitted shared runtime schemas; the full freshness gate passes. The earlier initial-SHA comparison conflated merged mainline growth with branch work.

## What Must Be Fixed

- Strip or isolate caller metadata keys that can affect authorization; derive trusted scopes/permissions from the authenticated `RequestContext`.
- Stop synthesizing `tenant_admin` for background execution; use least privilege and explicitly propagated trusted authorization data.
- Make runtime metrics tenant-scoped or require an appropriate privileged dependency.
- Make checkpoint `load()`/`list()` raise `TenantRequiredError` for missing tenant context and add hostile tests for both adapters.
- Preserve all currently green runtime, type-escape, matrix, freshness, and test gates.
