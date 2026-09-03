# Goal: P2 #4 CI workflow consolidation 58 to <=55 with registry blocking semantics

## User Request

P2: #4 — consolidate from 58 to <=55 workflows after measuring which workflows
actually duplicate execution, and fix the registry's blocking semantics at the
same time. Retire exactly three redundant workflow files (openapi-drift-check.yml,
generated-api-freshness.yml, merge-group.yml) while preserving every piece of
unique coverage they provide, and make the workflow registry accurately
communicate merge impact by marking required-context emitters blocking:true.

Design context (locked in prior investigation):
- 3 retire candidates confirmed: openapi-drift-check.yml, generated-api-freshness.yml, merge-group.yml.
- Fold-ins designed:
  - 3 unique clerk scripts (check_generated_jsonvalue_absent.py,
    check_clerk_tenant_response_exported.py, check_clerk_tenant_mapping_contract.py)
    -> contract-shape-regression job in contract-compliance.yml.
  - Live suite (entrypoint-smoke + alias-parity + min-tests guard + L6 boot) ->
    runtime-contract-checks job in pr-checks.yml.
  - layer7-billing.json -> contract gate SPEC_CONFIG (REFRESHABLE_ONLY).
- critical-gates.yml already covers the 5 non-clerk scripts (check_l1_target_schema,
  check_targets_stats_named_schema, check_generated_client_reproducibility) plus full
  export/diff (openapi-drift gate). Only the 3 clerk scripts + live suite are unique.

## Refined Goal

Reduce the workflow directory from 58 to exactly 55 YAML files by retiring the
three redundant workflows, folding every unique check they performed into the
canonical gates so no coverage is lost, and fix the workflow registry so that
workflows emitting required CI contexts are marked blocking:true (currently zero
entries are blocking, so the registry does not accurately communicate merge
impact). Delivery requires the workflow-count invariant to be relaxed from 58 to
55 in both the registry verifier and the consolidation test, the retired files to
be deleted from both .github/workflows/ and .depot/workflows/, registry entries
updated, and all CI validation gates to pass.

## Acceptance Criteria

- [ ] Criterion 1: Exactly 3 files retired — openapi-drift-check.yml,
      generated-api-freshness.yml, merge-group.yml — deleted from BOTH
      .github/workflows/ and .depot/workflows/ (workflow directory count = 55).
- [ ] Criterion 2: Retired unique coverage is folded into canonical workflows:
      (a) the 3 clerk scripts run in contract-compliance.yml contract-shape-regression
      job; (b) entrypoint-smoke + alias-parity tests + ensure-pytest-collection
      min-tests guard run in pr-checks.yml runtime-contract-checks job against a
      stack that boots layer6-benchmarks and waits on L6 /health; (c) layer7-billing.json
      added to SPEC_CONFIG as REFRESHABLE_ONLY so the contract gate regenerates+diffs it.
- [ ] Criterion 3: MAX_WORKFLOW_FILES updated from 58 to 55 in
      scripts/ci/verify_workflow_registry.py (line 21) and
      .github/workflows/generated-api-freshness.yml removed from FORCE_FULL_PREFIXES
      in scripts/ci/contract_compliance_gate.py (line ~110).
- [ ] Criterion 4: Registry blocking semantics fixed: the 3 retired entries removed
      from .github/workflows/workflow-registry.json, and blocking:true set on every
      workflow that emits a required CI context (pr-checks.yml, security-gates.yml,
      contract-compliance.yml, prod-readiness.yml, supply-chain-integrity.yml,
      release-evidence-bundle.yml, publish-sdk.yml, and any others emitting required
      contexts).
- [ ] Criterion 5: Tests updated: tests/ci/test_ci_workflow_consolidation.py adds the 3
      retired files to RETIRED_WORKFLOWS, asserts len(workflow_files) <= 55 (not 56),
      updates the "at most 55" phrase, and keeps consolidation-proof assertions intact.
- [ ] Criterion 6: Docs updated: docs/operations/ci-workflow-consolidation.md adds the 3
      retire records and reconcilies the count, WORKFLOW_REGISTRY.md and README.md reflect
      55 workflows and the corrected blocking semantics.
- [ ] Criterion 7: No new skips, weakened thresholds, allowlist inflation, or
      continue-on-error introduced anywhere.
- [ ] Criterion 8: Validation passes: `python scripts/ci/verify_workflow_registry.py`
      with MAX 55 and the full register gate; `pytest tests/ci/test_ci_workflow_consolidation.py`
      and the related tests/ci/* gates; contract_static collection still >= 330.

## Scope Boundaries

**In scope:**
- Editing .github/workflows/contract-compliance.yml (fold clerk scripts into
  contract-shape-regression job) and its push/schedule paths if applicable.
- Editing .github/workflows/pr-checks.yml (runtime-contract-checks job: add
  layer6-benchmarks to compose boot + LAYER6_API_URL env + extend pytest command
  with entrypoint-smoke and alias-parity files; extend the L1-L5 health wait loop
  to include L6).
- Editing infra/compose/docker-compose.full.yml only if layer6-benchmarks requires
  it to boot deterministically (prefer minimal/no change).
- Editing scripts/ci/verify_workflow_registry.py (MAX 58 -> 55).
- Editing scripts/ci/contract_compliance_gate.py (FORCE_FULL_PREFIXES cleanup +
  SPEC_CONFIG addition of layer7-billing.json as REFRESHABLE_ONLY).
- Editing .github/workflows/workflow-registry.json (remove 3 entries; set
  blocking:true on required-context emitters).
- Editing tests/ci/test_ci_workflow_consolidation.py and any other tests/ci tests
  whose assertions change due to the retirement.
- Editing docs/operations/ci-workflow-consolidation.md, .github/workflows/WORKFLOW_REGISTRY.md,
  .github/workflows/README.md.
- Deleting the 3 retired files from .github/workflows/ and .depot/workflows/.

**Out of scope:**
- R5 architectural changes.
- The deleted L3->L4 proxy or compatibility shims.
- Unrelated dead-code cleanup or formatting churn.
- Cargo work, tenant-isolation feature changes, broad refactors.
- Opportunistic dependency upgrades.
- Any changes to tracks already delivered (branch protection, supply-chain scoping,
  release-evidence scoping, paths-filters split, failure-backlog wiring, ESLint
  harness fix, CACHE_REDIS_URL fix).

## Applicable Project Conventions

**Quality gate command:**
- `python scripts/ci/verify_workflow_registry.py`
- `pytest tests/ci/test_ci_workflow_consolidation.py` (plus related tests/ci gates:
  test_workflow_permissions.py, test_deterministic_gate_workflows.py, test_visual_regression_contract.py,
  test_code_scanning_workflow_configuration.py, test_heavy_workflow_concurrency.py,
  test_merge_group_contract.py, test_merge_queue_simulation.py)
- `python scripts/ci/contract_compliance_gate.py --mode full` (requires deps;
  at minimum verify contract_static collection >= 330)

**Commit convention:**
- Conventional commits, one commit per iteration from the Builder.
- Trailer required per goal-skill convention: `Assisted-by: OpenAI:GPT-5.6 Luna`
- Project convention: `Co-authored-by: Ona <no-reply@ona.com>` also applies.

**Guidelines:**
- Verify registry S6-6 cap, FORCE_FULL_PREFIXES, and consolidation test invariants
  before claiming success. There are no .github/guidelines/ files.

**Rules:**
- Do not silence the rule, skip tests, weaken contract-compliance, or add
  blanket continue-on-error/retries/allowlists.
- Worktree rule: never use git reset --hard or git rebase --abort. Branch is
  `valyntxyz-sturdy-pancake`, ahead 8 / behind 3 vs origin/main; the 3 commits on
  origin/main are unrelated L4 billing mojibake fixes. A rebase onto fresh
  origin/main is expected at final DoD but must not be part of the Builder commit
  work unless conflicts force it.