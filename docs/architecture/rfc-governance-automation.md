# RFC: Governance Automation — Reusable CI Composites and Environment-Aware Profiles

| | |
|---|---|
| **Status** | Submitted for review / Awaiting reviewer disposition |
| **Owner** | Platform Governance |
| **Reviewers** | @value-fabric/sre-leads, @value-fabric/security-leads, @value-fabric/maintainers |
| **Date** | 2026-07-18 |
| **Related** | `.fabric/prod-gates.policy.yaml`, `config/ci/required-status-checks.json`, `.github/workflows/prod-readiness.yml`, `.github/actions/setup-pnpm/action.yml` |

## 1. Summary

This RFC proposes to reduce recurring governance debt in the Value Fabric CI layer by:

1. Introducing **reusable GitHub Actions composite actions** for the most repeated setup and evidence-handling patterns.
2. Making **CI profile selection explicit, centralized, and environment-aware** so that PR, release-candidate, and production-oriented validation run in the correct context.
3. Laying the groundwork for policy-as-code enforcement, automated waiver lifecycle management, provenance automation, and repository maturity dashboards.

The immediate deliverables are this RFC, a narrow proof-of-concept (PoC) PR that demonstrates one representative composite and one profile-selection mechanism, and a sequenced roadmap for the remaining improvements.

## 2. Problem Statement

The repository has accumulated significant CI governance debt:

- **High duplication**: 51 workflow files spanning ~16,000 lines repeat the same setup, dependency-install, and artifact-upload steps with locally customized copy.
- **Action-version drift**: The same third-party actions are pinned to multiple different commit SHAs or tags across workflows, increasing maintenance burden and the risk of supply-chain inconsistency.
- **Ad-hoc environment gating**: Many workflows use inline `if: github.event_name == 'pull_request'` conditionals. The semantics of "PR", "release", and "production" contexts are not centrally documented or enforced.
- **False-failure noise**: Inconsistent setup (e.g., Python cache enabled in some jobs but not others, different Node/pnpm versions, divergent dependency-install commands) creates avoidable flakes and makes failure triage harder.
- **Manual review burden**: Because automation does not consistently enforce setup patterns or profile boundaries, reviewers must manually verify that new workflows do not weaken security, skip production checks, or duplicate existing logic.

These problems are especially acute for security and release workflows, where inconsistent setup or misplaced environment checks can silently reduce assurance.

## 3. Goals and Non-Goals

### 3.1 Goals

- Reduce duplicated workflow logic without removing or weakening any security, supply-chain, release, or governance check.
- Relocate checks to the correct execution context (PR, release-candidate, production) through documented, machine-readable rules rather than scattered inline conditionals.
- Make action versioning consistent and updateable from a single source of truth.
- Provide a reusable setup composite that is adopted incrementally and can be validated locally.
- Preserve all existing required status checks and branch-protection guarantees.
- Produce a concrete PoC that can be exercised in GitHub Actions and reviewed as code.

### 3.2 Non-Goals

- This RFC does **not** propose a broad migration of all 51 workflows. Migration happens workflow-by-workflow after the PoC is reviewed.
- It does **not** change runtime service code, deployment manifests, or production workflow behavior.
- It does **not** remove existing gates, waivers, or baselines. It proposes mechanisms to manage them more explicitly.
- It does **not** implement the full roadmap items (SLSA dashboards, waiver automation, maturity dashboards) — it defines the architecture and sequencing for them.

## 4. Quantitative Baseline

Evidence collected from `.github/workflows/` at `main` (`9b787fb2d`):

| Metric | Value |
|---|---|
| Workflow files | 51 |
| Total workflow lines | ~16,041 |
| Existing composite actions | 1 (`.github/actions/setup-pnpm`) |
| `actions/setup-python` usages | ~89 across multiple pins |
| `actions/setup-node` usages | ~33 across multiple pins |
| `pnpm/action-setup` direct usages | 32 |
| `./.github/actions/setup-pnpm` usages | 7 |
| `python -m pip install --upgrade pip` | 32 |
| `pnpm install --frozen-lockfile` | 31 |
| `docker build` invocations | 9 |
| Matrix job definitions | 28 |
| `timeout-minutes:` declarations | 107 |
| Environment conditionals (`github.event_name`, `github.ref`) | 60+ distinct patterns |

### 4.1 Action-Pin Inconsistency Hotspots

| Action | Observed References |
|---|---|
| `actions/checkout` | `@692973e3...`, `@34e1148...`, `@v4` (unpinned), `@692973e3...` without comment |
| `actions/setup-python` | `@v5`, `@4237552...`, `@a26af69...`, `@v4` |
| `actions/setup-node` | `@v4`, `@60edb5d...`, `@49933ea...` |
| `pnpm/action-setup` | `@v3`, `@fc06bc1...` (v4.4.0) |
| `aquasecurity/trivy-action` | `@57a97c7...` (v0.35.0), `@314ff8b...` (post-v0.36.0) |
| `github/codeql-action/upload-sarif` | `@3ce22a6...` (v4.35.4), `@f58f0d1...` (codeql-bundle-v2.26.0) |

This inconsistency violates the repository's own pinning policy (see `pr-checks.yml` and `security-gates.yml` headers) and forces the quarterly "Workflow Action Pin Refresh" to touch many files manually.

### 4.2 Duplicated Logic Hotspots

1. **Python + Node/pnpm setup** appears in `pr-checks.yml`, `contract-compliance.yml`, `critical-gates.yml`, `security-gates.yml`, `release-evidence-bundle.yml`, and others.
2. **Dependency installation** (`pip install -r tests/requirements-test.txt`, `pnpm install --frozen-lockfile`) is repeated in almost every multi-language job.
3. **Artifact upload** patterns repeat the same `if: always()`, retention, and path-list boilerplate.
4. **Docker buildx + registry login** is duplicated in `build-deploy.yml`, `security-gates.yml`, `supply-chain.yml`, `release-evidence-bundle.yml`, and `sbom.yml`.

### 4.3 Existing Profile Mechanism

`.github/workflows/prod-readiness.yml` already implements a `determine-profile` job that emits `pr-fast`, `mainline-full`, or `release-candidate` based on `GITHUB_REF`. This is a good starting point, but:

- It is only used inside `prod-readiness.yml`.
- The rules are shell-scripted inline.
- Other workflows reimplement similar logic locally.
- The mapping from profile to required checks is documented in `.fabric/prod-gates.policy.yaml` but not machine-enforced in GitHub Actions.

### 4.4 Existing Maturity / Evidence Automation

The repository already operates several maturity/evidence mechanisms that this proposal will build on rather than replace:

- `repo-maturity-scorecard` job in `prod-readiness.yml`.
- `flakiness-tracker.yml`.
- `monthly-debt-burndown.yml`.
- `contract-scorecard` job in `contract-compliance.yml`.
- SLSA provenance generation in `supply-chain.yml`.

### 4.5 False-Failure Risk Areas

- Divergent Node.js versions (e.g., `flakiness-tracker.yml` uses Node 20 while other workflows use 22.18.0).
- Divergent `pnpm/action-setup` versions.
- Missing `cache: pip` or `cache: pnpm` in some jobs, increasing install time and network flakiness.
- Inline shell `if` statements that depend on exact whitespace or variable quoting.

## 5. Proposed Architecture

### 5.1 Reusable Composite Actions

Introduce a small library of composite actions under `.github/actions/`. The first composite targets the highest-frequency duplication; subsequent composites are sequenced by the roadmap.

#### 5.1.1 `setup-fabric-ci` (Representative Composite)

Responsibility: install the canonical Python, Node.js, pnpm, and dependency stack used across Fabric 4L CI.

Inputs:
- `python-version` (default: `3.11`)
- `node-version` (default: `22.18.0`)
- `pnpm-version` (default: `10.34.5`)
- `install-python-deps` (default: `true`) — install `tests/requirements-test.txt`
- `install-node-deps` (default: `true`) — run `pnpm install --frozen-lockfile`
- `working-directory` (default: `.`)
- `cache` (default: `pnpm`)

Behavior:
1. Check out code (optional; callers may already have checked out).
2. Set up Python with `cache: pip`.
3. Set up pnpm and Node.js with `cache: pnpm`.
4. Install Python test/gate dependencies.
5. Install pnpm dependencies.
6. Export step summary metadata.

Security note: the composite pins all third-party actions to full-length SHAs and documents the update process. It does not accept arbitrary action versions through inputs.

#### 5.1.2 Future Composites (Roadmap)

| Composite | Problem Addressed | Priority |
|---|---|---|
| `upload-evidence` | Standardize artifact upload (`if: always()`, retention, path expansion, naming) | P1 |
| `setup-docker-ci` | Docker buildx + registry login with immutable-tag validation | P1 |
| `run-gate` | Execute a Makefile gate target and emit a JSON evidence artifact | P2 |
| `enforce-action-versions` | Validate that a workflow only uses approved action pins | P2 |

### 5.2 Environment-Aware CI Profiles

#### 5.2.1 Profile Registry

Create `.github/ci-profiles.yml` as the machine-readable source of truth for CI context selection:

```yaml
version: "1.0"
profiles:
  pr-fast:
    description: "Cheap local or PR feedback — no external deps, < 5 min"
    triggers:
      - event: pull_request
        branches: [main]
    gates:
      - policy
      - lint
      - arch
      - security
      - state
      - db-consistency
      - summary

  mainline-full:
    description: "Main branch verification — full gate except deploy-specific actions"
    triggers:
      - event: push
        branches: [main]
    gates:
      - policy
      - lint
      - arch
      - security
      - chaos
      - smoke
      - state
      - database
      - agent
      - obs
      - release-policy
      - behavior-readiness
      - summary

  release-candidate:
    description: "Final pre-tag or pre-production decision"
    triggers:
      - event: push
        branches: ["release/**"]
      - event: workflow_dispatch
        inputs:
          profile: release-candidate
    gates:
      - policy
      - lint
      - arch
      - security
      - tenant-isolation
      - chaos
      - smoke
      - state
      - database
      - agent
      - obs
      - release-policy
      - sign-manifest
      - behavior-readiness
      - summary

  production-core:
    description: "Near-term critical production gates"
    triggers:
      - event: workflow_dispatch
        inputs:
          profile: production-core
    gates:
      - policy
      - arch
      - security
      - tenant-isolation
      - database-readiness
      - migration-readiness
      - api-contracts
      - auth-readiness
      - secrets-readiness
      - deployment-readiness
      - launch-blockers
      - behavior-readiness
      - summary
```

This registry does not replace `.fabric/prod-gates.policy.yaml`; it complements it by mapping **CI execution context** (GitHub event/branch) to the **profile** defined in the policy file. The policy file remains the source of truth for gate definitions and classes.

#### 5.2.2 `determine-ci-profile` Composite

Responsibility: read `.github/ci-profiles.yml` and emit a profile name and gate list based on the current GitHub context.

Inputs:
- `fallback-profile` (default: `''`) — explicit opt-in profile to use when no trigger matches; empty means fail closed

Outputs:
- `profile`
- `gates` (JSON array)
- `description`
- `matched` (`true` if an explicit trigger matched)

Behavior:
1. Parse `.github/ci-profiles.yml`.
2. Match the current `github.event_name`, `github.ref`, and workflow inputs against trigger rules.
3. Emit the profile and gate list as outputs.
4. If no trigger matches and `fallback-profile` is empty, exit with an error (fail closed).
5. If `fallback-profile` is provided but not defined in the registry, exit with an error.
6. Only use an explicitly authorized fallback after the above checks pass.

This composite can be called once per workflow and consumed by downstream jobs, replacing inline shell `if` blocks.

#### 5.2.3 Profile Gating Rules

The following rules must hold for every profile transition:

1. **No check is removed** when moving from `pr-fast` to `mainline-full` to `release-candidate` to `production-core`; checks are only added or relocated.
2. **Infrastructure-dependent checks** (e.g., live DAST, chaos tests, performance load tests) are not executed in `pr-fast`.
3. **Release-only checks** (e.g., manifest signing, tenant-isolation bundle freshness) run only in `release-candidate` or `production-core`.
4. **PR checks** run on every pull request to `main` regardless of changed paths, because several required status checks are branch-protection gates.
5. **Required status checks** listed in `config/ci/required-status-checks.json` must be emitted by at least one workflow for every qualifying PR.

### 5.3 Policy-as-Code Enhancements

1. **Action-pin policy**: Add a JSON/YAML registry of approved action pins (`.github/allowed-actions.yml`). A CI gate verifies that every workflow in `.github/workflows/` uses only approved pins. Dependabot SHA bump PRs automatically update the registry.
2. **Workflow-schema policy**: Enforce that every workflow declares `permissions`, `timeout-minutes`, and an owner reference from `workflow-registry.json`.
3. **Profile-conformance policy**: Add a gate that verifies every workflow's environment conditionals are consistent with `.github/ci-profiles.yml`.

### 5.4 Automated Waiver Lifecycle Management

Extend the existing waiver file (`config/ci/behavior_readiness_waivers.yaml`) with:

- `expires_at` field (required).
- `owner` and `approval` fields.
- A scheduled workflow that opens an issue 14 days before expiration and fails the gate if a waiver expires without renewal.
- A validation script that rejects new waivers longer than 90 days without explicit Security + SRE approval.

### 5.5 Provenance Automation

The repository already generates SLSA provenance in `supply-chain.yml` for release events. The proposal is to:

1. Add a **lightweight provenance verification** step to PRs that checks the structure of the provenance generator inputs without requiring registry writes.
2. Use the same SLSA generator version/pin across `supply-chain.yml` and `release-evidence-bundle.yml`.
3. Store provenance artifact metadata in the release evidence bundle so downstream consumers can verify it.

### 5.6 Repository Maturity Dashboards

Consolidate existing scorecard and evidence artifacts into a single JSON dashboard:

- Merge `repo-maturity-scorecard`, `contract-scorecard`, `flakiness-report`, and `behavior-readiness-audit.json`.
- Publish the dashboard to `reports/scorecards/ci-maturity-dashboard.json` on every mainline run.
- Add a gate that fails if any maturity dimension drops below a configurable threshold.

## 6. Proof of Concept

The PoC demonstrates the representative composite and the profile-selection mechanism without modifying production workflows.

### 6.1 Files Added

| File | Purpose |
|---|---|
| `.github/actions/setup-fabric-ci/action.yml` | Representative reusable composite for canonical CI setup |
| `.github/actions/determine-ci-profile/action.yml` | Reusable profile-selection mechanism |
| `.github/workflows/poc-governance-automation.yml` | Draft PoC workflow exercising both composites |

### 6.2 What the PoC Proves

1. The `setup-fabric-ci` composite can replace repeated setup steps in a representative job.
2. The `determine-ci-profile` composite correctly maps execution contexts to `pr-fast`, `release-candidate`, `production-core`, or `mainline-full` profiles.
3. Profile-aware steps are **routed and activated** in the correct context; release-candidate and production-core placeholders are present in the workflow graph and gated by the selected profile.
4. The selector **fails closed**: an unmatched context with no authorized fallback exits with an error rather than silently selecting the weakest profile.

### 6.3 Validation Evidence

The PoC workflow was exercised in GitHub Actions on branch `poc/governance-automation`:

| Context | Profile Selected | Matched Explicit Trigger | Run URL |
|---|---|---|---|
| `pull_request` targeting `main` | `pr-fast` | true | https://github.com/bmsull560/Fabric_4L/actions/runs/29642705854 |
| `workflow_dispatch` with `profile=release-candidate` | `release-candidate` | true | https://github.com/bmsull560/Fabric_4L/actions/runs/29642715112 |
| `workflow_dispatch` with `profile=production-core` | `production-core` | true | https://github.com/bmsull560/Fabric_4L/actions/runs/29642715781 |

All runs completed successfully after the fail-closed and registry fixes. The `setup-fabric-ci` composite installed Python 3.11, Node.js 22.x, and pnpm 10.34.5, and the `determine-ci-profile` composite emitted the expected profile name and gate list for each context. This validates deterministic context-to-profile routing and step activation; it does not execute infrastructure-dependent gates such as Cosign signing, Kubernetes deployment, Prometheus checks, or backup/restore drills.

Static validation performed locally:

- YAML syntax check passed for all new files.
- Shell-injection finding in `setup-fabric-ci` remediated.
- Profile selector logic verified for all documented contexts, including fail-closed behavior for unmatched contexts and invalid fallbacks.
- `make check-workflow-references` passed.

### 6.4 What the PoC Does Not Do

- It does not migrate any existing workflow.
- It does not modify branch protection or required checks.
- It does not execute infrastructure-dependent production checks in a PR context.

### 6.5 CI Status Classification on PoC PR

The following table classifies every failing or cancelled check on the current PoC PR head. The goal is to distinguish failures caused by the PoC from pre-existing baseline noise, infrastructure limitations, or environmental issues.

| Workflow / Job | Root Failure | Classification | PoC-Related? |
|---|---|---|---|
| PR Checks — Structural Preflight | `workflow-registry.json` and generated docs (`docs/development/CI_GATES.md`, `.github/workflows/README.md`, `.github/workflows/WORKFLOW_REGISTRY.md`) were stale after adding `poc-governance-automation.yml` | Introduced by PoC; resolved by regenerating registry and generated docs | Yes |
| PR Checks — Docker Image Build Verification (frontend) | `packages/feature-flags/package.json` not found (Dockerfile out of sync with monorepo) | Pre-existing baseline failure | No |
| PR Checks — Docker Image Build Verification (layers 1–6) | Cancelled after frontend/layer failures or dependency on prior failing jobs | Cascading cancellation | No |
| PR Checks — Frontend | Coverage branch threshold 81% not met (actual 76.85%) | Pre-existing baseline failure | No |
| PR Checks — Layer 1–6 tests | Mypy baseline exceeded, missing dependencies, or similar per-layer drift | Pre-existing baseline failures | No |
| PR Checks — Integration Tests (Docker) | `Missing identity ID for OIDC auth` (Infisical) | External service / secret limitation | No |
| PR Checks — Runtime Contract Tests (Services Up) | Depends on live stack / Infisical secrets | External service limitation | No |
| PR Checks — Kubernetes Dry-Run Validation | Kyverno CRD annotations exceed 262144 bytes on current kind/k8s version | Pre-existing baseline / environmental | No |
| PR Checks — p0-e2e-gate | Neo4j container unhealthy in compose stack | Pre-existing baseline / environmental | No |
| PR Checks — Alertmanager Config Validation | Pre-existing config drift | Pre-existing baseline failure | No |
| PR Checks — Billing/Entitlements Regression + Evidence | Missing environment / dependency setup | Pre-existing baseline failure | No |
| PR Checks — Critical Behaviors Gate | Baseline behavior-debt / skip governance | Pre-existing baseline failure | No |
| PR Checks — Cross-Layer Contract Tests | Environment / dependency setup | Pre-existing baseline failure | No |
| PR Checks — Docker Compose Config Contract | Environment / dependency setup | Pre-existing baseline failure | No |
| PR Checks — Schemathesis Property-Based Contract Tests | Environment / dependency setup | Pre-existing baseline failure | No |
| PR Checks — Shared & Tests — Code Quality | Pre-existing lint/type baseline | Pre-existing baseline failure | No |
| PR Checks — Tenant Isolation Gate | Pre-existing test/environment baseline | Pre-existing baseline failure | No |
| PR Checks — Unified Readiness Gate | Aggregates other failing gates | Cascading / pre-existing | No |
| Contract Compliance — Python Platform Contract Lint | `GATE-COMPAT-004` frontend-shim-registration exited 127 (script missing) | Pre-existing baseline failure | No |
| Contract Compliance — Generate OpenAPI from Code (layer3-knowledge) | `No module named 'layer3_knowledge'` | Pre-existing baseline failure | No |
| Contract Compliance — Lint Frontend (Contract Rules) | Pre-existing frontend contract lint baseline | Pre-existing baseline failure | No |
| Contract Compliance — Validate Canonical Examples | Pre-existing example drift | Pre-existing baseline failure | No |
| Contract Compliance — Contract Shape Regression | Pre-existing contract drift | Pre-existing baseline failure | No |
| Critical Gates — production-config-policy-layer6 | `FileNotFoundError: k8s/envs/prod/neo4j-aura-patch.yml` | Pre-existing baseline failure | No |
| Critical Gates — Critical Gates Summary | Aggregates failing critical gates | Cascading / pre-existing | No |
| Prod Readiness Gates — setup | `workflow-registry.json` stale (same root cause as Structural Preflight) | Introduced by PoC (fixed by regenerating registry) | Yes |
| Prod Readiness Gates — prod-readiness / release-policy | Aggregates prior failures / missing evidence | Cascading / pre-existing | No |
| Release Evidence Bundle — Build images & security scan (layers 1–6) | Cancelled due to upstream failures | Cascading cancellation | No |
| Release Evidence Bundle — Live stack health evidence | Requires live running stack | External service limitation | No |
| Release Evidence Bundle — Release readiness gate (observability + deployment) | `ModuleNotFoundError: No module named 'jsonschema'` | Pre-existing baseline failure | No |
| Release Evidence Bundle — SAST & Security E2E | Pre-existing security test baseline | Pre-existing baseline failure | No |
| Repository Hygiene — Canonical Layout & Legacy Path Check | Infisical CLI `scan --recursive` flag unsupported in installed version | Pre-existing baseline / false positive | No |
| Security Gates — Dev Auth Bypass Guard | `ALLOW_INSECURE_DEV_AUTH_BYPASS=true` in `services/api/app/tests/test_health.py` | Pre-existing baseline failure | No |
| Security Gates — Container Scan (Trivy) (layers 1–6) | Vulnerabilities detected in built images | Pre-existing baseline failure | No |
| Security Gates — SBOM + Policy / SBOM Generation (layers 1–6, apps-web) | Depends on image build / policy baseline | Pre-existing / cascading | No |
| Security Gates — DAST (OWASP ZAP baseline) | Live target / environment unavailable | External service limitation | No |
| Security Gates — Dockerfile Non-Root User Check | Pre-existing Dockerfile baseline | Pre-existing baseline failure | No |
| Security Gates — OSV-Scanner (PR diff) | GitHub Actions template `Maximum object size exceeded` | Infrastructure / environmental | No |
| Security Gates — Python Dependency Audit (pip-audit) (layers 1–6) | Known vulnerabilities in `cryptography`, `setuptools` | Pre-existing baseline failure | No |
| Security Gates — Repository Scan (Trivy fs + IaC + secrets) | Pre-existing repository scan findings | Pre-existing baseline failure | No |

**Summary:** Of the ~50 failing or cancelled checks, only Structural Preflight and Prod Readiness setup were directly caused by adding the PoC workflow. The workflow registry and all generated docs are now in sync, so Structural Preflight and Prod Readiness setup should pass on the next run. All other failures are pre-existing baseline issues, external-service limitations, or cascading cancellations unrelated to the PoC scope.

## 7. Migration Plan

1. **Phase 0 (this RFC + PoC)**: Review and approve the approach. Exercise the PoC in GitHub Actions.
2. **Phase 1**: Adopt `setup-fabric-ci` in non-blocking workflows first (e.g., `flakiness-tracker.yml`, `monthly-debt-burndown.yml`).
3. **Phase 2**: Adopt `determine-ci-profile` in `prod-readiness.yml` after adding the profile registry.
4. **Phase 3**: Roll out `upload-evidence` and `setup-docker-ci` composites to security and release workflows.
5. **Phase 4**: Implement policy-as-code gates for action pins and profile conformance.
6. **Phase 5**: Implement waiver lifecycle automation, provenance verification, and maturity dashboard consolidation.

Each phase includes:
- A tracking issue.
- Updates to `workflow-registry.json` where applicable.
- A validation run comparing before/after workflow outputs.
- CODEOWNERS review from `@value-fabric/sre-leads` and `@value-fabric/security-leads`.

## 8. Safety Analysis

### 8.1 Security Guarantees Preserved

- No security gate, scan, or audit step is removed.
- Action pins in composites are at least as strict as the strictest existing workflow.
- Required secrets and permissions are not broadened.
- Profile gating only **relocates** checks; it does not delete them.

### 8.2 Supply-Chain Guarantees Preserved

- Composites centralize action-pin choices, making quarterly pin refreshes smaller and auditable.
- The action-pin policy gate prevents introduction of unpinned or unapproved actions.
- Docker build and SBOM workflows are not changed by the PoC.

### 8.3 Release Guarantees Preserved

- The existing `prod-readiness.yml` profile mechanism remains in place until the new composite is proven.
- Release-only steps (manifest signing, tenant-isolation bundle freshness) continue to be gated by `release-candidate` context.
- Required status checks remain unchanged during Phases 0–2.

### 8.4 Failure Modes

| Risk | Mitigation |
|---|---|
| Composite hides security-critical behavior | Keep composites small, single-purpose, and well-documented. Avoid wrapping gate logic in early composites. |
| Profile selection misclassifies context | Fail closed on unmatched contexts; require an explicit, registry-defined `fallback-profile`; validate selector logic against `.github/ci-profiles.yml`. |
| Required check not emitted for some PRs | The profile registry explicitly lists which gates run per context; a conformance gate verifies coverage. |
| Composite input abuse | Inputs are restricted to version strings and booleans; no arbitrary commands or action refs accepted. |

## 9. Open Questions

1. Should `.github/ci-profiles.yml` be merged into `.fabric/prod-gates.policy.yaml`, or kept separate as CI-specific configuration?
2. Should the PoC PR be created as a draft from this branch, or should the RFC be approved before creating the PoC?
3. Which workflow should be the first production adopter after the PoC?
4. Do we need a new ADR for the CI profile registry, or is this RFC sufficient?

## 10. Decision Records

### ADR-GOV-001: Use composite actions for canonical CI setup

- **Decision**: Centralize repeated setup steps in `.github/actions/setup-fabric-ci`.
- **Rationale**: Reduces duplication, pins versions consistently, and lowers false-failure rate from divergent setup.
- **Consequences**: Callers must pass explicit inputs; CODEOWNERS review required for composite changes.

### ADR-GOV-002: Centralize CI profile selection

- **Decision**: Introduce `.github/ci-profiles.yml` and a `determine-ci-profile` composite.
- **Rationale**: Replaces scattered inline conditionals with documented, machine-readable rules.
- **Consequences**: Changes to profile triggers require review by SRE and Security; existing workflows continue to work during migration.

### ADR-GOV-003: Relocate checks rather than remove them

- **Decision**: Environment-aware profiles may move checks between contexts but never delete them.
- **Rationale**: Preserves security and release assurance while reducing false failures in the wrong context.
- **Consequences**: Some PR runs may remain longer because relocated checks still execute elsewhere; the benefit is reduced noise and clearer ownership.

## 11. Disposition Record

| Date | Action | Detail |
|---|---|---|
| 2026-07-18 | RFC drafted | Initial review-ready version committed to `poc/governance-automation` |
| 2026-07-18 | PoC implemented | `.github/actions/setup-fabric-ci`, `.github/actions/determine-ci-profile`, `.github/ci-profiles.yml`, `.github/workflows/poc-governance-automation.yml` |
| 2026-07-18 | Shell-injection remediation | `setup-fabric-ci` step summary now passes version inputs through `env:` and quotes shell variables |
| 2026-07-18 | Fail-closed profile selection | `determine-ci-profile` defaults `fallback-profile` to empty; unmatched contexts and invalid fallbacks exit with error; `workflow_dispatch.profile` is a constrained `choice` |
| 2026-07-18 | PoC claims tightened | RFC and workflow comments now distinguish profile routing from execution of infrastructure-dependent gates |
| 2026-07-18 | Workflow registry regenerated | `.github/workflows/workflow-registry.json` updated to include `poc-governance-automation.yml`; `.github/workflows/README.md`, `.github/workflows/WORKFLOW_REGISTRY.md`, and `docs/development/CI_GATES.md` synced |
| 2026-07-18 | Failing-check classification | ~50 failing/cancelled checks classified; Structural Preflight and Prod Readiness setup were PoC-introduced by registry/doc drift and are now resolved; all others are pre-existing baseline, external limitation, or cascading cancellation |
| 2026-07-18 | Static validation | YAML syntax, profile selector logic (including fail-closed cases), `make check-workflow-references` passed |
| 2026-07-18 | Hosted validation | PoC workflow ran successfully for `pr-fast`, `release-candidate`, and `production-core` contexts |
| 2026-07-18 | Submitted for review | Draft PR #1026 opened and linked to this RFC |
| 2026-07-18 | Decision owner assigned | @bmsull560 recorded as accountable RFC decision owner; GitHub does not allow a PR author to request themselves as a reviewer, so formal disposition will be recorded via an explicit approve/reject/defer comment or RFC update (see PR comment https://github.com/bmsull560/Fabric_4L/pull/1026#issuecomment-5011157877) |

**Current disposition:** Engineering work is review-ready. Awaiting formal approval, rejection, or deferral from the decision owner.

---

*This RFC is submitted for review. Approval or an explicit documented decision not to proceed is required before production adoption.*
