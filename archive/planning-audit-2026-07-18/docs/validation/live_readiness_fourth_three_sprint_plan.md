# Live Readiness Fourth Three-Sprint Plan

This fourth loop is justified because the previous three loops hardened the local live validation runner, seed reporting, and browser-evidence contract, but the repository still lacked a first-class CI entry point and a repository-owned schema check for the machine-readable evidence it now produces. Those gaps are still material because they affect repeatability and reviewer confidence; after this loop, further work should shift from incremental guardrails to executing the full live stack in an environment with healthy services.

| Sprint | Priority | Objective | Implementation Target | Expected Value |
|---|---:|---|---|---|
| Sprint 10 | P0 | Add a CI/manual-dispatch live validation gate wrapper | Add a GitHub Actions workflow that runs the config-only gate by default and can optionally run seed and Playwright validation when explicitly requested. | Makes the existing local runner discoverable, repeatable, and reviewable through standard repository automation. |
| Sprint 11 | P0 | Add machine-readable artifact schema validation | Add a deterministic schema validator for `live-workflow-validation-summary.json`, `artifact-manifest.json`, endpoint probes, and optional seed reports. | Prevents future changes from silently weakening the evidence contract established in prior loops. |
| Sprint 12 | P1 | Document the nominal-value stop line and operational handoff | Update validation documentation with the CI workflow, schema validator, and a clear stop condition: additional loops are nominal unless they execute the full live stack or fix concrete service failures. | Converts the autonomous loop into a sustainable operating model and prevents low-value churn. |

## Stop Criterion After Sprint 12

After this loop, the next incremental sprint loop should be considered **nominal value** unless it includes one of the following material inputs: a fresh full-stack live run with concrete failures, a new service-level startup regression, a failing CI gate, or a product requirement that changes the live validation contract.

## Implementation status

| Sprint | Status | Implemented artifact |
| --- | --- | --- |
| Sprint 10 — CI live validation gate | Implemented | `.github/workflows/live-workflow-validation.yml` runs the config-only live gate on relevant pull requests and pushes, supports manual full/no-start modes, validates artifacts, and uploads evidence. |
| Sprint 11 — Artifact schema validation | Implemented | `scripts/ci/validate_live_workflow_artifacts.py` validates summary JSON, manifest JSON, required core artifacts, endpoint probe shape, and optional strict seed report shape. |
| Sprint 12 — Nominal-value stop criteria | Implemented | `docs/validation/live-workflow-validation.md` now states explicit criteria for stopping additional autonomous loops unless new changes remove a real blocker or add missing enforceable automation. |

## Marginal-value decision after Sprint 12

After this fourth loop, another autonomous three-sprint cycle would provide **nominal incremental value** unless new runtime evidence appears. The remaining high-value work is no longer more wrappers or documentation; it is execution against a healthy live environment and remediation of any concrete service, seed, or browser failures surfaced by that run.
