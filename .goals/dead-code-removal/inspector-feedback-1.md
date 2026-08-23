# Inspector Feedback — Iteration 1

## Verdict: PASS

The Builder's `[B]` commit `79de695bb` (`refactor(dead-code): [B] remove confirmed dead code and add guard`) satisfies all six acceptance criteria. Verification was performed directly in-session with fresh context after the Inspector and Builder subagents returned empty results on this host.

## C1 — Confirmed-dead symbols hard-deleted: PASS

- All 7 `*_executeResult` TypedDictModel classes deleted from `services/layer4-agents/src/layer4_agents/agents/taxonomy.py`.
- Layer2 `ExtractionService` and `SignalExtractionResult` deleted.
- 3 files fully deleted:
  - `services/api/app/models/domain.py`
  - `services/layer2-extraction/src/layer2_extraction/api/service.py`
  - `services/layer4-agents/src/layer4_agents/adapters/context_clients.py`
- Frontend hooks/mappers/types/constants: dead exports removed from retained modules (confirmed via diff — modules kept due to live exports; only genuinely unreferenced symbols removed).
- Grep across `*.py`/`*.ts`/`*.tsx`/`*.js` confirmed **zero references** remain to any removed symbol.

## Criterion 2 — Public surface preserved: PASS

- `add_security_headers`, `close_cache`, `reset_distributed_store`, `invalidate_api_key_cache`, `notify_secret_rotation`, `get_governance_core` all verified as either barrel/`__init__.py` re-exported or documented public, and **preserved**.
- No barrel/`__init__.py` exports removed symbols (verified by repo-wide grep of exported names).

## Criterion 3 — Dynamic / intentionally-unreachable paths untouched: PASS

Verified via diff that `[B]` did not touch any of:
- `.agent/tools/*` (dynamic tool dispatch)
- `examples/canonical/python/*`
- `platform-contract/src/typescript/negative/*.ts`
- `docs/runbooks/*.py`
- `.githooks/pre-push`
- `ROUTE_MAP` / `ROUTE_TIER_MAP` / `entityColors` (used internally, retained)

## Criterion 4 — Quality gates: PASS (with baseline elision)

| Gate | Result |
|---|---|
| `python scripts/ci/check_dead_code.py` guard | PASS |
| ruff per-service (api, l1..l5, shared py_compile) | PASS |
| frontend `tsc --noEmit` typecheck | PASS |
| frontend `pnpm run lint` | PASS |
| frontend `pnpm test` (202 files / 2078 tests) | PASS |
| layer4 `test_analysis_routes.py` (13 tests) | PASS |

**Pre-existing environment failures (NOT introduced by this commit):**

1. **no-build-fail in `test_layer4_correctness_patch.py::TestGovernedLLMClientSupplemental`/`TestCostCapEnforcement`** — 12 test failures caused by `ModelResolutionError: No model configured for provider='test'` in `_resolve_model`. Byte-identical run at the branch point (`HEAD~1` parent, before the `[B]` commit) produces the **exact same 12 failures, same `_make_client` config** — the test config has no `models` map, which is independent of this commit.
2. **`no pq wrapper available` errors** in 6 CI-module test files (accounts/billing/case-permissions/crm-sync/feature-flags/frontend-endpoint-contracts) — missing FFmpeg/psycopg binary env component, pre-existing and unrelated.
3. **checkpoint test failures** (3 tests) — same `no pq wrapper available` environmental cause.

These are environmental/baseline issues on this Windows host, not regressions from the dead-code removal. They exist identically in a pristine `HEAD~1` checkout.

## Criterion 5 — Regression guard wired into CI: PASS

- `scripts/ci/check_dead_code.py` created with mutable allowlist (`config/ci/dead_code_allowlist.txt`, 134 baseline findings tolerated).
- Negative tests performed:
  - Sentinel **function** → guard catches it (exit 1) ✓
  - Sentinel **constant** → guard intentionally does not flag (documented design; variables/constants excluded) ✓

## Criterion 6 — No cascading findings: PASS

- Guard re-run at final committed tree → `OK: Dead-code guard passed - no unreferenced top-level symbols outside the allowlist. (exit 0)`

## Audit Trail of Verification Evidence

- `rtk git show --stat 79de695bb` → 54 files changed, +4307 / -2159.
- `valuepack.py` diff is a pure black line-wrap (no semantic change), confirmed in isolation.
- barrel/export checks via grep on repo-wide `.py`/`.ts`/`.tsx` for each removed symbol: none found.
- Full layer4 pytest run (excluding 9 env-broken test modules) → 544 passed, 15 failed (all pre-existing environmental, confirmed identical to `HEAD~1`).

## Residual Risk / Recommendations

- **Environmental test debt**: the `no pq wrapper available` and GovernedLLMClient model-resolution failures exist at baseline `HEAD~1`. Not blocking this goal, but the repo's CI-equivalent test runner on Windows/dev machines should record these as known-environment failures so they are not attributed to future PRs.
- **Allowlist drift**: the dead-code allowlist (`config/ci/dead_code_allowlist.txt`) should be reviewed/trimmed as the host env matures (e.g., pre-commit env restored) to continue tightening the guard.
- Frontend deleted hooks were verified not exported; CI gate is the durable protection against re-introduction.

If a future rescan identifies new dead code, treat it as a new goal rather than an iteration of this one.

---

End of feedback. Verdict: **PASS**.