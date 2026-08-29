# Workspace (live task state)

## Active task
- Goal: Reconcile OpenAPI across Layers 1-6, API Gateway, generated frontend types, and contract tests (eliminate drift, coherent contract chain, MERGE-READY verdict).
- Status: **COMPLETE** — Phase 12 validated, Phase 13 report delivered. See session checkpoint 007 for full details.

## What was delivered
- Gateway security declarations: 16 operations previously missing per-op `security: [{HTTPBearer: []}]` are now stamped via a declaration-only router-level `require_bearer_declaration` dependency across benchmarks/usage/product_endpoints/jobs/api-keys routers. Exactly 16 ops changed; 10 public endpoints remain unstamped. No runtime auth change (context-based `require_authenticated` still enforces 401).
- L2.5 Signal Refinery spec wired into `scripts/ci/contract_compliance_gate.py` (REFRESHABLE_ONLY_SPECS + SPEC_CONFIG); error-envelope contract suite extended to L2.5 (41 tests).
- New contract test `tests/contract/test_gateway_security_declarations.py` (4 tests, contract_static_no_service): fail-closed coverage + allowlist regression guard + 16-op formerly-undeclared guard.
- Stale reference fixed: `scripts/compare_openapi.py` now points at canonical `scripts/export_openapi.py`.

## Validation (post-commit)
- `pytest tests/contract -m "contract_static and not service_required"` → 481 passed, 33 skipped, 1 xfailed, 58 deselected.
- `pnpm -w run check:contract-compliance` → passed (artifact freshness clean, full frontend tsc typecheck).
- `pnpm -w run check:api-types` → passed (exit 0; security declarations did not change generated TS types).

## Commits (branch valyntxyz-friendly-funicular)
- a4dd74b66 feat(contracts): wire L2.5 Signal Refinery into contract compliance gate
- 84fe5dd01 fix(api-gateway): declare HTTPBearer security on all protected operations

## Notes for next session
- 8 layer spec files show as "modified" in `git status` on Windows due to CRLF normalization (`* text=auto eol=lf`); staging produces zero content change (pure line-ending phantoms). Do not commit them as content.
- Working tree is clean after commit.
