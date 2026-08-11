# V1-CI-001 — Aggregate PR Check Contract & Merge Queue — Design Packet

- Task: `release/v1/tasks/V1-CI-001.yaml` (GitHub issue #1263)
- Base: `main` @ `e3ace52032f8c80436e46adee4fba27402ae9f31`
- Patch: `signoff-evidence/gates/workflow-patches/v1-ci-001-aggregation.patch` (**Stage 1 only**)
- Prepared for one-sitting human application. The agent token cannot touch `.github/workflows/**`; a human with workflow write access applies the patch and performs the branch-protection steps.

---

## 1. Current-state inventory

### 1.1 Branch protection on `main` (live, fetched via `gh api repos/bmsull560/Fabric_4L/branches/main/protection`)

`required_status_checks.strict = true`; eight required contexts (all `app_id: 15368` — GitHub Actions):

| # | Required context | Emitting workflow job |
|---|---|---|
| 1 | `mandatory-security-regression` | `security-gates.yml` → job `mandatory-security-regression` |
| 2 | `contract-compliance` | `contract-compliance.yml` → job `contract-compliance` |
| 3 | `Structural Preflight` | `pr-checks.yml` → job `structural-preflight` |
| 4 | `prod-readiness` | `prod-readiness.yml` → job `prod-readiness-summary` |
| 5 | `behavior-tests` | `pr-checks.yml` → job `behavior-tests` |
| 6 | `Layer 5 - Source Contract` | `pr-checks.yml` → job `layer5-source-contract` |
| 7 | `Layer 5 - Tenant Isolation Regression` | `pr-checks.yml` → job `layer5-tenant-isolation-regression` |
| 8 | `Layer 5 - Contract Shape Regression` | `pr-checks.yml` → job `layer5-contract-shape-regression` |

Other protection flags: `enforce_admins: true`, `required_signatures: false`, `required_linear_history: false`, `allow_force_pushes: false`, `allow_deletions: false`. No merge queue configured today.

### 1.2 Machine-readable registry — `config/ci/required-status-checks.json`

Mirrors the same eight contexts in `required_status_checks`; owner team "Platform Governance"; changes require Platform Governance + Security approval via CODEOWNERS-reviewed PRs. `docs/governance/branch-protection-required-checks.yml` carries the identical list and is kept in sync by `scripts/ci/check_required_check_policy.py` (fails if the two files diverge).

### 1.3 Validation loop — `.github/workflows/branch-protection-validation.yml`

Weekly + `workflow_dispatch`. Fetches live branch protection and rulesets, then runs:

- `scripts/ci/validate_branch_protection_checks.py --config config/ci/required-status-checks.json --api-response-file <live protection>` — every required context in the JSON must be required on `main` (a renamed/removed required check fails this).
- `scripts/ci/validate_mandatory_security_gate_enforcement.py` — asserts the mandatory security gate is enforced for PR merges and direct pushes.

Additionally `check_required_check_policy.py` asserts every required check name is emitted by a `pull_request` workflow job — so at Stage 3/4 every added aggregate name must exist as a job `name:` (they do, §2) and no removed name may linger in the JSON/YAML mirrors.

---

## 2. The nine aggregate checks and their fan-in maps

Constraint discovered during design: GitHub Actions `needs:` **cannot reference jobs in another workflow file**. Each aggregate therefore lives in the workflow that owns the jobs it summarizes. All aggregate jobs:

- run `if: always()` so they execute even when children fail or skip;
- perform **no substantive testing** — they call the shared arbiter `scripts/ci/aggregate_gate.py` (new in the patch), which fails the aggregate iff any child `failure`/`cancelled`, or any child `skipped` without an explicit safe-skip confirmation (`--skip-safe JOB=ENV_VAR`, where `ENV_VAR` must be the string `true`, composed in `env:` from change-scope outputs / event gates). This mirrors the existing `security-gates-required` / `unified-readiness-gate` idiom and satisfies the "path-filtered skips must be explicitly confirmed safe" invariant;
- are **informational in Stage 1** — none are added to branch protection or to `required-status-checks.json`.

All fan-in job names below were verified against the workflow files at `e3ace52` (job keys, not display names).

### `01-repository-integrity` — `.github/workflows/pr-checks.yml`

Job key `aggregate-01-repository-integrity`. Fans in **4 gated jobs** (+ `change-scope` for scope outputs):

`structural-preflight`, `pr-overlap-guard`, `governance-docs-check`, `gate-engineering`

Skip policy: `pr-overlap-guard` is `pull_request`-only by design — safe-skip confirmed when `github.event_name != 'pull_request'`. All others must succeed (no `if:` on those jobs).

### `02-code-quality-and-tests` — `.github/workflows/pr-checks.yml`

Job key `aggregate-02-code-quality-and-tests`. Fans in **8 gated jobs** (+ `change-scope`):

`layer1-checks`, `layer2-checks`, `layer3-checks`, `layer4-checks`, `layer5-checks`, `layer6-checks`, `shared-and-tests-checks`, `frontend-checks`

Skip policy: each layer job safe-skips only when its `change-scope` output (`layer1`–`layer6`, `backend`, `web`) resolved to `'false'` — i.e. the change provably cannot affect it.

### `03-contract-compliance` — `.github/workflows/contract-compliance.yml`

Job key `aggregate-03-contract-compliance`. Fans in **13 jobs**:

`contract-compliance`, `plugin-tests`, `validate-dependabot-coverage`, `lint-frontend`, `validate-canonical`, `platform-contract-tests`, `python-lint`, `generate-openapi`, `detect-drift`, `openapi-contract-tests`, `contract-shape-regression`, `validate-deprecations`, `contract-scorecard`

Skip policy: none — the `pull_request` trigger is intentionally unconditional (see the workflow's own comment about required checks and path filters) and none of these jobs have `if:` gates, so any skip fails the aggregate closed. The existing `summary` job is a markdown reporter and is not fanned in.

### `04-security-gates` — `.github/workflows/security-gates.yml`

Job key `aggregate-04-security-gates`. Fans in **16 gated jobs** (+ `change-scope`):

`dev-auth-bypass-guard`, `gitleaks-scan`, `cypher-dynamic-guard`, `semgrep-full-scan`, `trivy-repo-scan`, `osv-scanner-pr`, `trivy-image-scan`, `sbom-policy`, `dast-api-scan`, `bandit-scan`, `pip-audit-scan`, `frontend-security-audit`, `dockerfile-non-root-check`, `dependency-review`, `mandatory-security-regression`, `route-auth-gate`

Skip policy (each confirmed via composed env expression): change-scope-gated jobs safe-skip when their scope (`layer3`/`code`/`deps`/`backend`/`web`/`docker`) is `'false'`; `dependency-review` and `osv-scanner-pr` are PR-only; `trivy-image-scan`, `sbom-policy`, `dast-api-scan` are gated on `pull_request`/`push` events and skip on `merge_group` — treated as confirmed-safe skips in Stage 1–2 with a Stage-3 follow-up to widen their `if:` to `merge_group` (§6, D-3). `mandatory-security-regression`, `dev-auth-bypass-guard`, `gitleaks-scan`, `trivy-repo-scan` have no skip allowance. Deliberately not fanned in: `prepare-helm-dependencies` (helper), `osv-scanner-full` and `openssf-scorecard` (push/schedule only), `sbom-generation` (release artifact), `security-evidence-artifact` (reporter), `security-gates-required` (existing PR-only fan-in).

### `05-tenant-isolation-and-behavior` — `.github/workflows/pr-checks.yml`

Job key `aggregate-05-tenant-isolation-and-behavior`. Fans in **7 gated jobs** (+ `change-scope`):

`behavior-tests`, `tenant-isolation-gate`, `route-auth-gate`, `layer5-source-contract`, `layer5-tenant-isolation-regression`, `layer5-contract-shape-regression`, `critical-behaviors-gate`

Skip policy: scope-gated (`web`, `backend`, `layer5`, `code`) only. This aggregate carries six of today's eight required contexts (`behavior-tests`, the three Layer 5 checks, plus the tenant/auth gates behind `mandatory-security-regression`'s domain).

### `06-production-readiness` — `.github/workflows/prod-readiness.yml`

Job key `aggregate-06-production-readiness`. Fans in **12 gated jobs** (+ `determine-profile`):

`arch-conformance`, `security-isolation`, `dependency-chaos`, `cross-domain-smoke`, `agent-provenance`, `state-consistency`, `db-production-readiness-gate`, `observability-readiness`, `repo-maturity-scorecard`, `readiness-10`, `gate-engineering`, `release-policy`

Skip policy: runtime-gated jobs safe-skip only on docs-only PRs (`event == pull_request` and `runtime == 'false'`); profile-gated jobs safe-skip only when `profile == 'pr-fast'`. `setup` (helper) and `prod-readiness-summary` (existing reporter, today's `prod-readiness` required check) are not fanned in.

### `07-supply-chain-integrity` — `.github/workflows/supply-chain-integrity.yml`

Job key `aggregate-07-supply-chain-integrity`. Fans in **7 jobs**:

`ci-tools-preflight`, `source-sbom-scan`, `sbom-scan`, `provenance`, `verify-signatures`, `dependency-audit`, `license-check`

Skip policy: `sbom-scan`/`provenance`/`verify-signatures` certify release images and only run on dispatch / `certify_images`; on PR and merge_group no release image exists, so the skip is confirmed safe. `supply-chain-summary` (reporter) not fanned in.

### `08-release-evidence` — `.github/workflows/release-evidence-bundle.yml`

Job key `aggregate-08-release-evidence`. Fans in **6 jobs**:

`release-readiness-gate`, `build-and-scan`, `supply-chain-policy-check`, `sast-and-tests`, `live-stack-evidence`, `consolidate-bundle`

Skip policy: none — no job-level `if:` gates in this workflow.

### `09-change-risk-and-approval` — `.github/workflows/pr-checks.yml`

Job key `aggregate-09-change-risk-and-approval`. **0 fan-in jobs — this is the one aggregate that is deterministic policy, not a summary** (the task invariant defines it as such). It runs the new `scripts/ci/check_change_risk_approval.py`, which fails closed unless:

1. an independent-review artifact exists at `signoff-evidence/reviews/<head_sha>.json`;
2. it is schema-valid (`schema_version: 1`, 40-hex SHAs, typed `findings` / `high_risk_surfaces_touched` / `codeowner_approvals`);
3. its `base_sha`/`head_sha` equal the `pull_request` (or `merge_group`) event SHAs;
4. no finding with severity `P0`/`P1` has an unresolved status (`open`/`triaged`/`in_progress`);
5. every surface in `high_risk_surfaces_touched` has a `codeowner_approvals` entry whose approver is not the patch author;
6. `reviewer != author`.

The artifact schema (v1) is documented in the script docstring. No LLM is involved; no network access is required.

### Aggregate fan-in summary

| Aggregate check name | Host workflow | Gated fan-in jobs |
|---|---|---|
| `01-repository-integrity` | pr-checks.yml | 4 |
| `02-code-quality-and-tests` | pr-checks.yml | 8 |
| `03-contract-compliance` | contract-compliance.yml | 13 |
| `04-security-gates` | security-gates.yml | 16 |
| `05-tenant-isolation-and-behavior` | pr-checks.yml | 7 |
| `06-production-readiness` | prod-readiness.yml | 12 |
| `07-supply-chain-integrity` | supply-chain-integrity.yml | 7 |
| `08-release-evidence` | release-evidence-bundle.yml | 6 |
| `09-change-risk-and-approval` | pr-checks.yml | 0 (deterministic policy) |

All nine names are unique, stable, lowercase-hyphenated, and currently emitted by no other job — no collision with the eight existing required contexts.

---

## 3. Staged migration plan

### Stage 1 — Informational aggregates (this patch)

Apply `v1-ci-001-aggregation.patch`. Contents:

- 6 workflow files: `merge_group:` trigger added; nine aggregate jobs appended (four in `pr-checks.yml`, one each in the other five).
- `scripts/ci/aggregate_gate.py` (new) — shared fan-in arbiter.
- `scripts/ci/check_change_risk_approval.py` (new) — deterministic 09 policy gate.
- `tests/ci/test_aggregate_gates.py` (new) — 13 behavior tests (allowed/denied/failure modes for both scripts).
- `docs/governance/branch-protection-required-checks.yml` — nine names added under `informational_status_checks` (required list untouched; `check_required_check_policy.py` only compares required lists and still passes).
- Regenerated `workflow-registry.json`, `WORKFLOW_REGISTRY.md`, `docs/development/CI_GATES.md` (trigger columns gain `merge_group`; nothing else changes — verified the diff is trigger-only).

Verification (from repo root, after applying):

```bash
git apply --check signoff-evidence/gates/workflow-patches/v1-ci-001-aggregation.patch   # pre-flight (already run: PASS)
git apply signoff-evidence/gates/workflow-patches/v1-ci-001-aggregation.patch
python scripts/ci/check_workflow_references.py          # task acceptance test (see §6 D-4 for one pre-existing failure)
pytest tests/ci -q                                      # task acceptance test
make check-workflow-registry                            # registry + docs in sync
make check-workflow-references                          # command/artifact references
python scripts/ci/check_required_check_policy.py        # required mirrors still consistent
```

Then open a PR with the applied change; confirm the nine `0x-*` checks appear on the PR and are green (except `09-change-risk-and-approval`, which fails until a review artifact exists — expected, see §6 D-2), and confirm the eight required contexts are unchanged.

### Stage 2 — Shadow parity (no repo changes; observation stage)

- Run the aggregates across several representative PRs: a backend-only PR, a frontend-only PR, a docs-only PR, a PR touching `.github/**`, and a deliberately-broken PR per required domain. For each, verify: every required child failure fails the correct aggregate (negative case), and every path-filtered skip is either confirmed-safe or fails the aggregate.
- Exercise `merge_group`: with the merge queue still off, dry-run via a test branch/ruleset or a throwaway PR enqueue; confirm each of the six workflows triggers on `merge_group` and aggregates report. Expected merge_queue observations: event-gated security scans skip (confirmed-safe in Stage 1–2); `mandatory-security-regression` must succeed — if it depends on PR metadata, that is a Stage-3 blocker (§6 D-3).
- Parity matrix: for every one of the eight required contexts, record child result vs. aggregate result across the sample PRs. Parity = no case where a required context failed while its covering aggregate(s) passed. Coverage: 01←`Structural Preflight`; 05←`behavior-tests`, three Layer-5 checks; 04←`mandatory-security-regression`; 03←`contract-compliance`; 06←`prod-readiness`.
- Evidence: paste the parity matrix + workflow run URLs into `signoff-evidence/gates/` and link from the Stage-3 PR. Suggested minimum: 5 representative PRs + 1 merge_group cycle.

Verification commands per PR: `gh run list --branch <pr-branch>` and the aggregate job logs; weekly `branch-protection-validation` run must stay green.

### Stage 3 — Aggregates become required, old checks retained (human-sequenced)

Prerequisite: Stage-2 parity evidence recorded; Publisher sign-off.

1. Human workflow PR (cannot be in the Stage-1 patch): widen event-gated job `if:` expressions to include `merge_group` in `security-gates.yml` (`trivy-image-scan`, `sbom-policy`, `dast-api-scan`, `osv-scanner-pr`, `dependency-review`, `security-gates-required`) and re-check `mandatory-security-regression` behavior on merge_group. Also make the `pull_request` triggers of `supply-chain-integrity.yml` and `release-evidence-bundle.yml` unconditional (drop their `paths:` filters) so `07`/`08` are emitted for every PR — same rationale as the existing comment in `contract-compliance.yml`; path-filtered required checks never get emitted and block merges. This is a deliberate, documented widening — **no thresholds lowered**; skipped-scope safety is still enforced by the aggregates.
2. Same PR updates `config/ci/required-status-checks.json` and `docs/governance/branch-protection-required-checks.yml`: add the nine `0x-*` names to `required_status_checks`, move them out of `informational_status_checks`.
3. After merge, a repo admin (Platform Governance) adds the nine contexts to branch protection on `main` (Settings → Branches, or `gh api -X PUT repos/bmsull560/Fabric_4L/branches/main/protection/required_status_checks` — note PUT replaces the full context list, so include all 17: 9 new + 8 old). Order: update registry files first, merge, then flip protection — `check_required_check_policy.py` requires every required name to be emitted by a `pull_request` workflow, which is true from Stage 1 onward.
4. Enable the merge queue on `main` (ruleset or classic protection `merge_queue`), requiring the nine aggregate checks.
5. Run `branch-protection-validation` (workflow_dispatch) and attach the run log to the sign-off evidence.

### Stage 4 — Remove old direct checks from branch protection (human-sequenced)

Prerequisite: at least one full week (or 20+ merged PRs, whichever is later) with zero parity violations at Stage 3.

1. PR removes the eight legacy contexts from `config/ci/required-status-checks.json` and `docs/governance/branch-protection-required-checks.yml`, leaving the nine aggregates. Matrix execution and detailed per-job evidence are untouched — jobs still run; only their direct branch-protection requirement is removed.
2. Repo admin removes the eight old contexts from branch protection (full-list PUT with only the nine names).
3. `branch-protection-validation` run log + human Publisher sign-off recorded in `signoff-evidence/gates/` (completion evidence per the task contract).

---

## 4. Branch-protection convergence spec

| File | Stage 1 | Stage 3 | Stage 4 |
|---|---|---|---|
| `config/ci/required-status-checks.json` → `required_status_checks` | unchanged (8 names) | 8 old + 9 aggregates | 9 aggregates only |
| `docs/governance/branch-protection-required-checks.yml` → `required_status_checks` | unchanged | 8 old + 9 aggregates | 9 aggregates only |
| same file → `informational_status_checks` | + 9 aggregate names | aggregates removed from informational | unchanged |
| GitHub branch protection on `main` | unchanged | add 9 aggregates (keep 8 old); enable merge queue | remove 8 old |

Exact Stage-3 JSON array (order preserved, aggregates appended):

```json
["mandatory-security-regression", "contract-compliance", "Structural Preflight", "prod-readiness", "behavior-tests", "Layer 5 - Source Contract", "Layer 5 - Tenant Isolation Regression", "Layer 5 - Contract Shape Regression", "01-repository-integrity", "02-code-quality-and-tests", "03-contract-compliance", "04-security-gates", "05-tenant-isolation-and-behavior", "06-production-readiness", "07-supply-chain-integrity", "08-release-evidence", "09-change-risk-and-approval"]
```

Human steps and order (who does what):

1. **Platform Governance engineer** — merges the Stage-1 patch PR (this packet).
2. **Platform Governance engineer** — collects Stage-2 parity evidence (§3 Stage 2).
3. **Platform Governance + Security approvers** — review/merge the Stage-3 PR (workflow `if:` widening + registry mirrors).
4. **Repo admin** — updates branch protection contexts (add nine), enables merge queue.
5. **Repo admin** — after the parity window, removes the eight legacy contexts (Stage 4 PR merged first).
6. **Publisher** — records sign-off with the validation run logs.

`branch-protection-validation.yml` needs no edits at any stage — it validates whatever `config/ci/required-status-checks.json` declares against live protection.

---

## 5. `merge_group` trigger plan

Snippet added to each file's `on:` block (bare `merge_group:` = default `types: [checks_requested]`):

```yaml
  # V1-CI-001: merge queue support (Stage 1 shadow; aggregates become
  # required at Stage 3).
  merge_group:
```

| Workflow file | Inserted after | Why |
|---|---|---|
| `.github/workflows/pr-checks.yml` | `push: branches: [main]` | hosts 4 of 8 required contexts + aggregates 01/02/05/09 |
| `.github/workflows/security-gates.yml` | `push:` block, before `schedule:` | hosts `mandatory-security-regression` + aggregate 04 |
| `.github/workflows/contract-compliance.yml` | `pull_request:` block | hosts `contract-compliance` + aggregate 03 |
| `.github/workflows/prod-readiness.yml` | `push:` block | hosts `prod-readiness` + aggregate 06 |
| `.github/workflows/supply-chain-integrity.yml` | `push: branches: [main]` | hosts aggregate 07 (required at Stage 3) |
| `.github/workflows/release-evidence-bundle.yml` | `pull_request:` block | hosts aggregate 08 (required at Stage 3) |

Not modified: `critical-gates.yml`, `zero-trust-validation.yml`, `generated-api-freshness.yml`, `test-reporting.yml` — they host no required check and no aggregate (§6 D-1). Adding `merge_group` to them at Stage 3+ is optional hardening, not required by the contract.

---

## 6. Deviations and flags

- **D-1 — Cross-workflow fan-in is impossible.** `needs:` is workflow-scoped, so nine aggregates cannot cover all ten listed workflow files. Closest faithful mapping: aggregates live in the six workflows that own today's required checks plus the two release/supply-chain workflows. `critical-gates.yml` (`critical-gates`, `critical-gates-merge-blocker`), `zero-trust-validation.yml` (`zero-trust-gate`), `generated-api-freshness.yml` (`generated-api-freshness`), and `test-reporting.yml` (`collect-test-results`, `save-coverage-summary`) are **not** represented in any aggregate. None of them are branch-protection required today, so no protected coverage is lost; if they should gate merges later, add them to an aggregate's host workflow or create a tenth aggregate in a follow-up task.
- **D-2 — 09 is not a fan-in.** No existing job performs independent-review verification (searched `scripts/`, `docs/governance/`, `config/` — nothing). The invariant itself defines 09 as deterministic policy, so the patch adds `scripts/ci/check_change_risk_approval.py` + the `signoff-evidence/reviews/<head_sha>.json` artifact contract (new schema, v1). Until review artifacts are produced, the informational `09-change-risk-and-approval` check will fail on PRs — that is intended shadow behavior, but Stage 3 cannot go required until the artifact-producing process exists (flagged as an open dependency: who writes the artifact — reviewer tooling or manual sign-off — is out of scope for this task).
- **D-3 — Event-gated jobs skip on `merge_group`.** In `security-gates.yml`, `trivy-image-scan`/`sbom-policy`/`dast-api-scan`/`osv-scanner-pr`/`dependency-review`/`security-gates-required` have `if:` conditions limited to `pull_request`/`push`; `pr-overlap-guard` (pr-checks) is PR-only. Stage 1 treats these as confirmed-safe skips on merge_group; Stage 3 step 1 widens their `if:` to include `merge_group` (human workflow edit). `mandatory-security-regression` has no event gate and must be watched in Stage 2 merge_group cycles.
- **D-4 — Pre-existing acceptance-test failure (not caused by this patch).** `python scripts/ci/check_workflow_references.py` fails identically on unmodified `main` @ e3ace52: `environment-promotion.yml` job `deploy-production` references missing `scripts/ci/canary_analysis.py`. Verify with the same command before and after applying — the failure set must be identical. Recommend filing behavior-debt; not fixed here (out of scope).
- **D-5 — Path-filtered aggregate-host workflows.** `supply-chain-integrity.yml` and `release-evidence-bundle.yml` filter `pull_request` by paths, so `07`/`08` are not emitted on non-matching PRs. Safe in Stage 1–2 (informational); must be made unconditional before Stage 3 (Stage-3 step 1). This is the explicit "path-filtered skip confirmed safe" handling for whole-workflow filters.
- **D-6 — `timeout-minutes` omitted on two aggregates.** `prod-readiness.yml` and `release-evidence-bundle.yml` have no job-level timeouts; giving the new aggregates `timeout-minutes: 5` made them the max and silently lowered the recorded `runtime_budget_minutes` (30→5) in the generated registry. To keep the registry diff trigger-only, those two aggregate jobs carry no `timeout-minutes` (runner default). Cosmetic; align in Stage 3 if desired.

---

## 7. Verification evidence for this packet

- `git apply --check --verbose signoff-evidence/gates/workflow-patches/v1-ci-001-aggregation.patch` from repo root @ e3ace52 → **exit 0**, all 13 files check out.
- Patch built in a pristine `git archive` copy of e3ace52; post-apply validation in that tree:
  - All six edited workflows parse (PyYAML, bool-preserving loader); every aggregate `needs:` entry resolves to an existing job (checked programmatically — zero missing).
  - `python scripts/ci/generate_workflow_registry.py --check` → in sync; `sync_ci_gate_docs.py --check` → in sync; `verify_workflow_registry.py` → passed.
  - `python scripts/ci/check_workflow_targets_and_artifacts.py` (`make check-workflow-references`) → passed.
  - `python scripts/ci/check_required_check_policy.py` → passed.
  - `pytest tests/ci/test_aggregate_gates.py` → 13 passed.
  - Full `pytest tests/ci` in the patched tree: **58 failed, 565 passed, 3 skipped** — and in the unmodified base tree: **58 failed, 552 passed, 3 skipped**. The 58 failing test IDs are byte-identical between base and patched runs (diff of sorted FAILED lists: empty), i.e. all pre-existing at e3ace52 in a clean `git archive` tree (several are date-sensitive, e.g. compatibility-debt review dates, or depend on untracked working-tree files); the +13 passed are the new `test_aggregate_gates.py` tests. The patch introduces zero regressions.
- Branch-protection inventory fetched live via `gh api repos/bmsull560/Fabric_4L/branches/main/protection` (§1.1).
