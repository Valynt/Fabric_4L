# Sub-plan D: Consolidate CI/Workflow Sprawl (#6)

**Goal:** Reduce the 44 GitHub workflows and 296 `scripts/ci` files to a smaller set of reusable, config-driven checks.

**Files to inspect / modify**
- `.github/workflows/` (44 `.yml` files)
- `scripts/ci/` (296 files)
- `config/ci/`
- `.pre-commit-config.yaml`

**Approach**
1. Group workflows by purpose: PR checks, contract drift, security, release, nightly.
2. Convert narrow drift/check workflows into reusable `workflow_call` jobs invoked from `pr-checks.yml`.
3. Replace per-layer import/drift scripts (`check_layer1_imports.py`, `check_l3_wrapper_drift.py`, etc.) with a single config-driven `scripts/ci/check_import_policy.py`.
4. Remove redundant shell wrappers; standardize on Python entrypoints.
5. Move slow pre-commit checks (`mypy --strict`, `semgrep`, `hadolint`, contract drift) to pre-push or CI.
6. Introduce a workflow registry document.

**Validation**
- `make verify-structure` passes.
- A test PR exercises the new workflow matrix.
- `make check-pytest-skip-governance` passes.
- Pre-commit runs in under ~2 minutes for typical changes.

**Rollback**
Restore deleted workflows/scripts from git history. Keep deprecated scripts for one release if external CI depends on them.

**Risks**
- Consolidation can accidentally drop a required gate.
- External forks or branch protections may reference deleted workflow names.
