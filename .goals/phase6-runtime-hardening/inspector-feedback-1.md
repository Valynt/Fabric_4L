# Inspector Feedback — Iteration 1

## Verdict: FAIL

## Acceptance Criteria Check

- [x] AC1 — verified: authenticated `/v1/runtime/health`, `/metrics`, `/types`, and run-operation routes are registered under `/v1`; tenant context is derived from `RequestContext` and missing tenant fails closed.
- [ ] AC2 — FAILED: the explicit DTOs and runtime paths are present in the committed OpenAPI document, but `pnpm contract:breaking` fails with 43 unapproved breaking changes, so contract drift is not resolved.
- [x] AC3 — verified: `AgentRuntimeClient` retains its existing methods while supporting an httpx-backed transport; tenant headers, canonical tenant/not-found errors, transport failures, and timeouts are mapped in code.
- [ ] AC4 — FAILED: package-level deprecation warnings were added additively, but `contexts/orchestration/public.py` remains only a `StateManager` re-export. It neither provides/aligned an `OrchestrationController` facade over `AgentRuntimeImpl` nor documents an explicit deferral with rationale.
- [x] AC5 — verified: `docs/governance/contract-exception-policy.md` documents the OpenAPI breaking gate and exception/approval process.
- [ ] AC6 — FAILED: new tests cover tenant fail-closed, response shape, cross-tenant invisibility, remote success, tenant propagation, and two error cases, but do not test unauthenticated route denial, health/metrics response shapes, or remote timeout/error mapping requested by the criterion.
- [ ] AC7 — FAILED: unit tests, targeted Ruff, and mypy pass, but mandatory repository gates do not. `make verify` fails the type-escape ratchet; `pnpm contract:breaking` fails; `make contract-tests` cannot run on this Windows environment because Cygwin bash cannot fork.
- [ ] AC8 — FAILED: independent commands exposed unresolved contract drift and a failing verification gate; therefore the goal cannot be independently certified.

## Quality Gate

- Command: `python -m pytest tests/unit -q --tb=short` (from `services/layer4-agents`)
- Result: PASS
- Details: 845 passed, 10 warnings.
- Command: `ruff check src/layer4_agents/runtime src/layer4_agents/api/routes/runtime.py tests/unit/test_runtime_routes.py tests/unit/test_runtime_sdk_remote.py`
- Result: PASS
- Details: All checks passed.
- Command: `python -m mypy src/layer4_agents/runtime`
- Result: PASS
- Details: No issues in 23 source files; only documented pre-existing unused-section notes.
- Command: `pnpm contract:breaking`
- Result: FAIL
- Details: 43 unapproved OpenAPI breaking changes were detected.
- Command: `make verify`
- Result: FAIL
- Details: type-escape ratchet reports five net-new unapproved `Any` uses in the runtime route and its test.
- Command: `make contract-tests`
- Result: FAIL (environment)
- Details: static collection aborted because Cygwin bash could not fork on Windows (`Resource temporarily unavailable`).

## Issues Found

1. The contract-breaking gate is red with 43 unapproved findings, contrary to AC2 and AC7.
2. `make verify` is red because the changed runtime route/test introduce unapproved `Any` escapes.
3. The required `OrchestrationController` facade alignment or explicit documented deferral is absent.
4. Route/remote tests omit unauthenticated denial, metrics/health shape assertions, and timeout/transport-error mapping.
5. `make contract-tests` was attempted but could not execute in the current Windows/Cygwin environment.

## What Must Be Fixed (FAIL only)

- Resolve the 43 breaking-change findings without weakening the gate, then rerun `pnpm contract:breaking` successfully.
- Remove the net-new `Any` escapes (preferred) or obtain and encode the required approval so `make verify` passes.
- Align `OrchestrationController` as the specified thin runtime facade, or add a clear documented deferral and rationale.
- Add explicit unauthenticated, health/metrics shape, timeout, and transport/error-mapping tests.
- Rerun all gates; run `make contract-tests` in a supported shell/CI environment and report a green result.
