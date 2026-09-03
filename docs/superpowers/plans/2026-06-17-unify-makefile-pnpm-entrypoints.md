# Sub-plan E: Unify Makefile/pnpm Entrypoints (#7)

> Superseded on 2026-08-31 by [ADR-047](../../explanations/adr/ADR-047-task-graph-build-orchestration.md). This plan remains historical context; do not implement its Makefile pattern-rule destination.

**Goal:** Remove overlapping and ambiguous commands so developers have one clear entrypoint per ecosystem.

**Responsibility split**
- `Makefile` owns Python/infra tasks: lint, typecheck, test, migrate, contract gates, K8s checks.
- `pnpm`/`package.json` owns JS/TS workspace tasks: frontend dev/build/test/lint/typecheck.

**Files to inspect / modify**
- `Makefile` (1,059 lines)
- `package.json` (75 scripts)
- `scripts/ci/run_root_aggregate_checks.py` (if it duplicates Makefile targets)
- `apps/web/package.json`
- `packages/*/package.json`
- CI workflows that call root `pnpm` scripts for Python tasks.

**Approach**
1. Audit `package.json` scripts and delete any that duplicate Makefile targets (e.g., `test:security`, `db:migrate:check`, `typecheck` if it dispatches Python).
2. Rename ambiguous targets:
   - `make lint` → keep for Python; add `make lint-frontend` or rely on `pnpm --dir apps/web run lint`.
   - `pnpm lint` → removed from root; use `pnpm --dir apps/web run lint` for frontend.
3. Replace explicit per-layer Makefile targets (`lint-layer1`…`lint-layer6`, `typecheck-layer1`…`typecheck-layer6`) with pattern rules over a `LAYERS` variable.
4. Move per-layer mypy flags to `config/ci/mypy-layer-config.yaml`.
5. Create a single root `pnpm` script `verify:frontend` that calls the frontend verification suite.

**Validation**
- `make lint` runs ruff across all Python layers.
- `pnpm --dir apps/web run lint` runs frontend lint.
- `make verify` still succeeds end-to-end.
- CI jobs use the correct entrypoint.

**Rollback**
Restore the original `Makefile`/`package.json` from git history.

**Risks**
- Muscle memory scripts break; document the new commands in `docs/development/COMMANDS.md`.
- CI workflows may fail if they call removed scripts.
