# Inspector Feedback — Iteration 2

## Verdict: FAIL

## Acceptance Criteria Check

- [x] AC1 — verified: authenticated `/v1/runtime/*` health, metrics, types, and run-operation routes remain registered; tenant extraction fails closed and cross-tenant run lookup is tested.
- [ ] AC2 — FAILED: the Layer 4 OpenAPI file retains all seven runtime paths and `pnpm contract:breaking` passes, but the full contract compliance gate detects drift in the Layer 4 contract and both generated TypeScript artifacts. Regeneration also replaces the committed Layer 7 billing rewrite from its actual FastAPI source, proving that rewrite is not a legitimate generated normalization.
- [x] AC3 — verified: the existing SDK surface supports the httpx remote client, tenant headers, canonical runtime/not-found/tenant errors, timeout mapping, and transport-error mapping.
- [x] AC4 — verified: additive legacy engine deprecation remains, and `contexts/orchestration/public.py` now explicitly documents why facade alignment is deferred to an atomic startup compatibility migration. Unit startup-dependent coverage still passes.
- [x] AC5 — verified: `docs/governance/contract-exception-policy.md` references `pnpm contract:breaking` and the existing approval hierarchy.
- [x] AC6 — verified: explicit tests now cover unauthenticated 401 denial, health/metrics response shapes, cross-tenant invisibility, timeout mapping, and connection/read transport failures; all pass.
- [ ] AC7 — FAILED: pytest, Ruff, mypy, and the OpenAPI breaking gate pass, but `make verify` fails the type-escape ratchet and the full contract compliance gate fails freshness. Iteration 2 restored `config/ci/type_escape_baseline.json` to its initial-goal version, thereby dropping the runtime occurrences that iteration 1's baseline contained; the ratchet now reports the runtime body as net-new unapproved escapes. `make contract-tests` also remains unavailable on this Windows host (native process exit `-1073741502`).
- [ ] AC8 — FAILED: independent execution found mandatory verification and contract-freshness checks red, so the goal cannot be certified.

## Quality Gate

- Command: `python -m pytest tests/unit -q --tb=short`
- Result: PASS
- Details: 850 passed, 8 warnings.
- Command: `ruff check src/layer4_agents/runtime src/layer4_agents/api/routes/runtime.py tests/unit/test_runtime_routes.py tests/unit/test_runtime_sdk_remote.py`
- Result: PASS
- Details: All checks passed.
- Command: `python -m mypy src/layer4_agents/runtime`
- Result: PASS
- Details: No issues in 23 source files; only the documented pre-existing configuration notes.
- Command: `pnpm contract:breaking`
- Result: PASS
- Details: OpenAPI breaking-change gate passed.
- Command: `python scripts/ci/contract_compliance_gate.py --mode full`
- Result: FAIL
- Details: Regeneration reports drift in `contracts/openapi/layer4-agents.json`, `contracts/openapi/layer7-billing.json`, and both Layer 4 generated TypeScript artifacts.
- Command: `make verify`
- Result: FAIL
- Details: Type-escape ratchet reports many runtime occurrences as net-new unapproved escapes, beginning with `api/runtime_state.py`, runtime adapters, core, models, ports, and SDK modules.
- Command: `make contract-tests`
- Result: FAIL (environment)
- Details: The Windows process exited with `-1073741502`; this environment-only failure is not the basis of the verdict.

## Issues Found

1. `make verify` is still red. The iteration 2 baseline change is a net revert to the baseline at the goal's initial SHA, but that baseline does not contain the runtime occurrences present in the current tree. Consequently, the ratchet rejects a large set of runtime `Any` and `type: ignore` occurrences. A mandatory gate cannot be considered fixed merely because the five route/test escapes were removed.
2. Contract freshness is unresolved. The committed generated TypeScript files omit the runtime additions, and full regeneration changes them as well as the Layer 4 OpenAPI document.
3. The `layer7-billing.json` change is unrelated and not generated from `services/layer7-billing/src/layer7_billing/api/main.py`: iteration 2 changes 6 path names and removes/replaces a large contract surface, while the exporter immediately rewrites the file and reports drift. Passing only the breaking-change gate does not legitimize this silent out-of-scope contract rewrite.

## What Must Be Fixed

- Reconcile `config/ci/type_escape_baseline.json` with the approved runtime baseline without weakening or wholesale resetting the ratchet, then run `make verify` to a genuine exit code 0.
- Run the required contract generation sequence, commit the actual generated Layer 4 contract/types, and remove the unrelated non-generated Layer 7 rewrite; ensure the full contract freshness gate passes.
- Re-run all required gates and preserve the passing breaking-change, unit, Ruff, and mypy results.
