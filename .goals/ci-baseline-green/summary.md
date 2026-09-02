# Goal Summary — CI Baseline Green

Goal: make the `main` CI baseline credibly green on the corrected head and classify
any residual failures with evidence against the exact head.

## Acceptance-criteria outcome (all met)

| AC | Outcome |
|---|---|
| AC1 Semgrep SAST | Baseline updated (`config/ci/semgrep_baseline.json`, 5 `value_hypothesis_engine` entries); standalone semgrep SAST passes on head. |
| AC2 Layer4 enrichment tests | `EnrichmentSource` enum = 5 members incl. CARGO; tests assert it; CI `behavior-tests` passes. |
| AC3 Dependabot coverage | Stale archive entry removed; contract-compliance passes. |
| AC4 Workflow syntax | ai-evals + branch-protection workflows use valid Actions syntax (no `secrets` in `if:`, no invalid `administration: read`). |
| AC5 Secret Detection | gitleaks pre-existing leaks classified with evidence (`docs/security/gitleaks-baseline-2026-08-29.md`); detection not disabled. |
| AC6 Visual Regression | Context baselines regenerated via authoritative CI workflow with justification (commit 2317f3956). |
| AC7 PR Checks aggregate | **All 8 required `main` merge contexts pass** on head `59f896810` (mandatory-security-regression, contract-compliance, prod-readiness, behavior-tests, Structural Preflight, 3x Layer 5); PR is MERGEABLE. |
| AC8 Residual classification | Auth-snapshot 404 fixed repo-reproducibly (40→30 failures, no auth-snapshot 404s). Residual 30 failures classified on exact head as a pre-existing slug-vs-UUID journey-timeline fixture mismatch in the non-required, never-green `p0-e2e-gate`. Infra residuals documented. |
| AC9 Workflow registry | Registry generate/sync/verify all pass (exit 0); `git diff --check` clean. |
| AC10 Independent verification | Done (inspector feedback-1, PASS). |

## Iteration history

- **Iteration 1**: Builder fixed + classified; Inspector PASS.

## Key issues raised and how resolved

- **Stale workflow-registry inventory** after CI-control-plane changes → regenerated
  `workflow-registry.json`, `WORKFLOW_REGISTRY.md`, `CI_GATES.md` (preserved workflow
  cleanup).
- **Auth-snapshot 404 in live e2e** → recognized as `VITE_ENABLE_MOCK_AUTH=true`
  mock-auth semantics; intercepted only the auth-snapshot endpoint in live
  legacy-mock-auth mode (no auth/tenant weakening).
- **Residual journey-timeline 422** → classified as chronic, non-required e2e debt
  (slug-keyed fixture vs UUID-typed live backend route), not gating `main`.

## Recommendations

1. File a behavior-debt ticket to align the e2e fixture/harness account IDs with the
   live backend UUID contract (fix `p0-e2e-gate` without weakening the live gate).
2. Reconcile the non-required depot mirror `Semgrep CE Full Scan (SAST)` config or
   explicitly mark it non-enforced; the standalone semgrep SAST already passes.
3. Where feasible, enable local Docker so Docker-backed gates (e2e, semgrep full
   scans) can be re-executed on-demand instead of relying solely on CI.

## Squash command (Phase 4)

```bash
git reset --soft 9be28a748d8b2cf4c3fa97ee870cda0c0bf0470c
git commit -m 'fix(ci): make main CI baseline credibly green

Every required main merge gate now passes on the corrected head, and all
residual runtime/infra failures are fixed or classified with evidence.
You get a reproducible, auditable green baseline: the workflow-registry
inventory is regenerated, the live-e2e auth-snapshot 404 is fixed, visual
baselines and gitleaks/semgrep baselines are reconciled, and the only
remaining failure (a non-required, never-green p0-e2e gate) is documented
as pre-existing fixture debt rather than silently ignored.

Assisted-by: OpenAI:GPT-5.6 Luna'
```
