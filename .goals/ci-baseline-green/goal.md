# Goal: Resolve PR #1585 CI-Baseline Failures on the Corrected Head

## User Request

> Fixed and pushed commit `657042342` to PR #1585. The mismatch was a stale generated
> workflow inventory after the CI-control-plane changes. Regeneration updated
> `.github/workflows/workflow-registry.json`, `.github/workflows/WORKFLOW_REGISTRY.md`,
> and `docs/development/CI_GATES.md`. This preserves the workflow cleanup; no workflow
> files or API clients were altered.
>
> So the registry defect is corrected, but the overall baseline should not yet be called
> green while run #7324 and the other required workflows remain pending. For the baseline
> repair to be credibly green, the fresh head needs:
> 1. Structural Preflight to pass through "Validate workflow ownership registry" and all later steps.
> 2. Generated API freshness/reproducibility to pass on the same SHA.
> 3. PR Checks and required aggregate gates to finish successfully.
> 4. Any remaining failures to be classified against this exact head — not inherited from the
>    superseded run. Visual Regression or unrelated runtime failures cannot be treated as repaired
>    merely because the registry gate passes.

## Refined Goal

Make the `main` CI baseline credibly green on the current corrected head (`9be28a7`,
the post-merge head containing PR #1585's registry synchronization). This requires
(1) fixing the remaining repo-fixable gate failures that block or cascade from the
corrected head, and (2) classifying every residual failure against this exact head with
evidence. The workflow-registry defect itself is already merged and must stay intact;
no workflow files or API clients are to be silently altered. Every fix must be scoped,
contract-safe, tenant-safe, and validated by the repo's existing gates.

## Acceptance Criteria

- [ ] AC1 — Semgrep SAST gate passes on the corrected head. The 9 "new" findings are
      already-baselined legacy findings whose baseline line numbers are stale (line-shift:
      5x `value_hypothesis_engine` +102, `layer3_client` 1->253, 3x `_batch_and_stats` +4).
      Update the acknowledged entries in `config/ci/semgrep_baseline.json` to their current
      line numbers (rule_id/path/message preserved) so a fresh real scan reports 0 new
      ERROR findings. The `docs/evidence/fabric4l-e2e-mock-workflow-probe` duplicates are a
      local Windows path-alias artifact only and must not be put into the baseline.
- [ ] AC2 — Layer 4 tests are green: `pytest services/layer4-agents/tests/test_enrichment.py
      services/layer4-agents/tests/test_enrichment_orchestrator_contract.py` passes.
      `test_enrichment_source_list` must reflect the 5-member `EnrichmentSource` enum
      (CARGO present) and `test_batch_status_sources_and_dependency`'s
      `set(all_sources) == set(EnrichmentSource)` assertion must hold.
- [ ] AC3 — Dependabot coverage validation is green: the stale npm ecosystem entry for
      `docs/archive/frontend-root-2026-05-02/source-snapshot` in `.github/dependabot.yml`
      is removed or corrected so `Validate Dependabot Coverage` and the
      `03-contract-compliance` aggregate pass.
- [ ] AC4 — `.github/workflows/ai-evals-pipeline.yml` and
      `.github/workflows/branch-protection-validation.yml` no longer produce phantom
      workflow-level failures. Specifically: ai-evals-pipeline must not use the `secrets`
      context in `if:` step conditions (5 sites: 136, 204, 320, 368, 763); branch-protection
      validation must not use the invalid `permissions: administration: read` block (not a
      valid GITHUB_TOKEN permission). Fixes must keep the workflows' intent intact and use
      valid GitHub Actions syntax, without weakening the safety/governance intent.
- [ ] AC5 — Secret Detection (gitleaks) is classified: the failure is from pre-existing
      leaks in old commits (40 findings) unrelated to this PR. Either add a documented,
      time-boxed allowlist/baseline for those pre-existing findings while keeping detection
      of new leaks strict, OR produce an evidence-backed classification that the failure is
      pre-existing debt requiring an owner decision. Do not weaken detection by disabling
      the scan.
- [ ] AC6 — Visual Regression `context — desktop @visual` snapshot mismatch is reconciled:
      85158 pixels (ratio 0.10) differ vs `context.png` because e2e golden-path routing
      changed. Regenerate the snapshot only if the current UI is the intended state, with a
      clear justification; otherwise identify and fix the actual regression. The
      `toHaveScreenshot` diff must be resolved, not hidden.
- [ ] AC7 — PR Checks aggregate on the corrected head: Structural Preflight passes through
      "Validate workflow ownership registry" and all later steps; generated API
      freshness/reproducibility passes on the same SHA; the PR Checks workflow and required
      aggregate gates complete successfully (excluding failures on the superseded head).
- [ ] AC8 — Residual runtime/infra failures are explicitly classified against the exact head
      with evidence (not inherited): Build Images QEMU/buildkit emulator failure,
      layer6 GHCR "installation not allowed to Create organization package", evidence-bundle
      artifact 409, and any others — documented as infra/org-permission/transient issues with
      a recommendation, or fixed if repo-reproducible.
- [ ] AC9 — `make check-workflow-registry` and the deterministic registry regeneration check
      still pass after the changes; `git diff --check` is clean.
- [ ] AC10 — Inspector independently verifies each claim (gate commands actually run and
      pass, snapshots/baselines legitimate, no weakened gates).

## Scope Boundaries

**In scope:**
- Update stale line numbers in `config/ci/semgrep_baseline.json` for the 9 line-shifted
  legacy findings (rules/paths/messages preserved, no new acknowledgments).
- Fix the two Layer 4 enum-drift tests to match the 5-member `EnrichmentSource` enum
  (including `CARGO`), if and only if `_determine_sources` behavior is consistent with it.
- Remove/correct the stale dependabot npm entry for the archived
  `docs/archive/frontend-root-2026-05-02/source-snapshot` directory.
- Fix the two phantom workflow files (ai-evals-pipeline `secrets` in `if:`; branch-protection
  invalid `permissions: administration: read`) with valid GitHub Actions syntax.
- Gitleaks: document/allowlist pre-existing historical findings (evidence-backed) without
  disabling detection.
- Visual Regression `context.png` snapshot reconciliation (regenerate with justification or
  fix the underlying regression).
- Verify/diagnose remaining PR Checks issues (structural preflight registry step, generated
  API freshness) and the aggregate gates on the exact head.
- Classify residual runtime/infra failures (QEMU build, GHCR org package permission,
  evidence-bundle artifact conflicts) with evidence.

**Out of scope:**
- Rewriting git history to purge pre-existing leaked secrets (org-level decision; allowlist/
  classification only).
- Changing GitHub org/package/role configuration itself (must be documented as an
  infrastructure action with a runbook pointer).
- New features or unrelated refactors.
- Any silent change to API contracts, tenant isolation, governance middleware, or
  production gates.

## Applicable Project Conventions

**Quality gate command:**
- `make check-workflow-registry` (validates workflow ownership/artifact registry)
- `make verify` (full pre-PR verification suite)
- Targeted: `python scripts/ci/generate_workflow_registry.py --check`,
  `python scripts/ci/check_semgrep_sarif.py --sarif <fresh> --baseline config/ci/semgrep_baseline.json`,
  `pytest services/layer4-agents/tests/test_enrichment.py services/layer4-agents/tests/test_enrichment_orchestrator_contract.py`,
  `git diff --check`
- See the repo `custom_instruction` Value Fabric Agent Reference for the full command map.

**Commit convention:**
- Conventional commits with role marker: `type(scope): [B] description` (Builder),
  `chore(scope): [I] description` (Inspector). Title <= 72 chars.
- Required trailer: `Assisted-by: OpenAI:GPT-5.6 Luna` (Builder) /
  `Assisted-by: OpenAI:GPT-5.6 Sol` (Inspector).
- Do not use `npm install`/`yarn install` (pnpm-only repo).

**Guidelines:**
- `AGENTS.md` (project brain), `DESIGN.md` (frontend governance, required before
  `apps/web/` edits), `docs/governance/behavior-first-testing.md` (behavior-first testing),
  `.agent/protocols/permissions.md` (read before tool calls).

**Rules:**
- No critical behavior exists unless tested; denied behaviors must have passing hostile tests.
- Never weaken auth, RBAC, tenant isolation, rate limiting, audit logging, governance
  middleware, contract validation, or production gates.
- Do not leak secrets; never commit real secrets; use Infisical-injected env in CI.
- Drift prevention: update contracts/types/tests/docs when behavior changes. Contracts are
  the source of truth.