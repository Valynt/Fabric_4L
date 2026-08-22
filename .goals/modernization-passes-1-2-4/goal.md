# Goal: Modernization Passes 1, 2, and 4

## User Request

Execute the first three recommended modernization passes for the Value Fabric repository:
1. Pass 1 — Registry reconciliation
2. Pass 2 — High-confidence dead-export deletion
3. Pass 4 — Layer 4 test-import migration

## Refined Goal

Safely perform structural modernization across three targeted, low-risk areas without changing runtime behavior:
1. Reconcile the compatibility debt registry (`docs/governance/compatibility-debt-registry.md`) against the actual codebase state (removing stale paths like nonexistent `value_fabric/`, updating review records, and ensuring compatibility gates stay green).
2. Clean up high-confidence dead exports in `packages/shared` and unused frontend utility hooks that have zero references or consumers.
3. Migrate all test imports in `services/layer4-agents/tests/` from legacy `src.*` shim paths to canonical `layer4_agents.*` imports.

## Acceptance Criteria

- [ ] Criterion 1: `docs/governance/compatibility-debt-registry.md` is reconciled and accurately reflects live shims without referencing deleted paths (`value_fabric/`). Compatibility checking gates (`pnpm --dir apps/web run check:compatibility-shims-registered` or equivalent python gates `check_duplicate_source_trees.py`, `check_deprecated_namespace_imports.py`) pass cleanly.
- [ ] Criterion 2: Verified dead exports with 0 references in `packages/shared` (e.g., unused error handling helpers) and unused frontend hooks are safely removed without breaking any active consumers or tests.
- [ ] Criterion 3: All tests in `services/layer4-agents/tests/` import directly from `layer4_agents.*` rather than `src.*` shims.
- [ ] Criterion 4: Frontend typecheck (`pnpm --dir apps/web run typecheck`) and Vitest suite (`pnpm --dir apps/web run test`) pass with 0 errors.
- [ ] Criterion 5: Python linting (`ruff check`) across all modified services and packages passes with no net-new violations.

## Scope Boundaries

**In scope:**
- Updating `docs/governance/compatibility-debt-registry.md` and associated deprecation manifests.
- Deleting verified unreferenced dead exports and helper functions in `packages/shared` and `apps/web`.
- Modernizing import statements in `services/layer4-agents/tests/`.

**Out of scope:**
- Deleting the ~120 runtime shims in `services/layer4-agents/src/` (Pass 5 - reserved for subsequent PR).
- Deleting `packages/feature-flags` (Pass 3 - reserved for separate PR).
- Splitting `executor.py`, `registry.py`, or `router.tsx` god objects (Passes 6-8).
- Any runtime or public API contract changes.

## Applicable Project Conventions

**Quality gate commands:**
- Frontend Typecheck: `pnpm --dir apps/web run typecheck`
- Frontend Test: `pnpm --dir apps/web run test`
- Source Tree Baseline Gate: `python scripts/ci/check_duplicate_source_trees.py`
- Deprecated Namespace Gate: `python scripts/ci/check_deprecated_namespace_imports.py --strict --use-baseline`
- Python Lint: `ruff check services/ packages/`

**Commit convention:**
- Conventional Commits: `type(scope): [B] description` for Builder, `chore(scope): [I] description` for Inspector
- Assisted-by trailer required: `Assisted-by: OpenAI:GPT-5.6 Luna` (Builder), `Assisted-by: OpenAI:GPT-5.6 Sol` (Inspector)
- Co-author trailer: `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`

**Rules:**
- Multi-tenant isolation invariants must remain intact.
- Do not introduce new runtime dependencies.
- Make surgical, targeted edits.
