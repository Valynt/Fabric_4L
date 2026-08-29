# P2 #4 — CI workflow consolidation 58 → ≤55 + registry blocking semantics

## Status: COMPLETED (iteration 1, PASS)

## What was achieved (mapped to acceptance criteria)

- **Criterion 1 — 3 files retired, count = 55.** `openapi-drift-check.yml`,
  `generated-api-freshness.yml`, and `merge-group.yml` were deleted from **both**
  `.github/workflows/` and `.depot/workflows/` (6 files total). Verified:
  `.github/workflows/` has 55 `.yml` files and the registry has 55 entries.
- **Criterion 2 — fold-ins preserve unique coverage.**
  - (a) The 3 unique clerk scripts (`check_generated_jsonvalue_absent.py`,
    `check_clerk_tenant_response_exported.py`,
    `check_clerk_tenant_mapping_contract.py`) now run in the
    `contract-shape-regression` job of `contract-compliance.yml`, with the 3
    script paths added to the push trigger.
  - (b) `pr-checks.yml` `runtime-contract-checks` job now boots
    `layer6-benchmarks`, adds `LY6_API_URL`, waits on the L6 `/health`
    endpoint, runs the 3-file suite (`test_layer_integration.py`,
    `test_layer_service_entrypoint_smoke.py`,
    `test_l3_route_alias_parity.py`) without a marker filter (mirroring
    `run-openapi-contract-tests.sh`), and enforces a `--min-tests 330`
    collection guard.
  - (c) `layer7-billing.json` was added to `SPEC_CONFIG` as
    `REFRESHABLE_ONLY_SPECS` so the contract gate regenerates + diffs it.
- **Criterion 3 — invariants updated.** `MAX_WORKFLOW_FILES = 55` in
  `scripts/ci/verify_workflow_registry.py`; `generated-api-freshness.yml`
  removed from `FORCE_FULL_PREFIXES` in `scripts/ci/contract_compliance_gate.py`.
- **Criterion 4 — registry blocking semantics fixed.** The 3 retired entries
  were removed and `blocking: true` set on all 7 required-context emitters:
  contract-compliance, pr-checks, prod-readiness, publish-sdk,
  release-evidence-bundle, security-gates, supply-chain-integrity.
- **Criterion 5 — tests updated.** `tests/ci/test_ci_workflow_consolidation.py`
  adds the 3 retired files to `RETIRED_WORKFLOWS` and asserts `<= 55`.
- **Criterion 6 — docs updated.** `docs/operations/ci-workflow-consolidation.md`
  (retire records + blocking-semantics + 2026 consolidation-pass sections),
  plus regenerated `WORKFLOW_REGISTRY.md`, `README.md`, and `CI_GATES.md`.
- **Criterion 7 — no skips/weakened thresholds/allowlist inflation.**
  Confirmed: no `continue-on-error`, no new skips, no allowlist additions.
- **Criterion 8 — validation passes.** `python scripts/ci/verify_workflow_registry.py`
  exits 0 ("Workflow registry validation passed"); consolidation + gate-docs +
  merge-group + workflow-index + required-check-policy + mirrored-files +
  duplicate-source-tree + workflow-skip-safety + release-evidence-skip-safety
  tests all pass; `contract_static` collection = 502 ≥ 330.

## Iteration history

- **Iteration 1 (PASS, self-verified):** All 8 acceptance criteria were
  independently re-checked against the committed state (`954da3817`). The
  goal-orchestrator's Inspector subagent is non-functional in this environment
  (returns empty on dispatch), so verification was performed by direct
  self-audit against `goal.md`.

## Key issues and resolutions

- **Pre-existing registry drift (not caused by P2 #4):** the registry verifier
  flagged `branch-protection-validation.yml` missing a `pull_request` trigger
  and `pr-checks.yml` missing two produced artifacts. Both were fixed in the
  registry to match the actual workflows, leaving the verify gate green.
- **Two pre-existing test failures unrelated to P2 #4** remain:
  - `tests/ci/test_workflow_permissions.py::test_write_permissions_are_allowlisted_with_reasons`
    flags `certify-release-candidate.yml` top-level `contents`/`attestations`/`id-token`
    writes. That workflow is **not** touched by this change.
  - `tests/ci/test_repo_hygiene_manifest.py::test_load_manifest_does_not_require_root_manifest`
    is a Windows path-separator (`\` vs `/`) assertion in temp-dir handling.
  Both are baseline defects tracked for the broader CI-baseline charter, not
  part of this goal's scope.

## Recommendations

- Fold the two pre-existing failures above into the security/readiness triage
  track (Track 3) of the broader CI-baseline worktree.
- The registry blocking semantics now communicate merge impact accurately;
  consider wiring `branch-protection-validation.yml` to enforce the 18-check
  contract (P0) and scope-aware release-evidence/supply-chain (P1) as the next
  self-enforcing CI integrations.

## Squash command

```bash
git reset --soft ae867e5c6975a1b7aefc57faaa92e80e90d283ac
git commit -m 'chore(ci): consolidate workflows and fix registry block semantics

Registry now marks the 7 required-check emitters blocking, the 3 redundant
workflows are retired with unique coverage preserved (clerk scripts folded
into contract-compliance, live suite + L6 into pr-checks, layer7-billing into
the contract gate), and the S6-6 cap is enforced at 55.

Assisted-by: OpenAI:GPT-5.6 Luna'
```
