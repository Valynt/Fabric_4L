# Third Live-Readiness Sprint Loop Plan

This third implementation loop extends the completed live-readiness work by focusing on **machine-readable evidence**, **seed/backend preflight certainty**, and **operator-facing CI/runbook clarity**. The prior loops established live stack startup hardening, guarded frontend commands, strict seed reporting, mock-ban behavior, and deterministic browser artifacts. The next highest-priority work is to make the gate easier to consume in automation and harder to misinterpret after partial or blocked live runs.

| Sprint | Theme | Highest-priority implementation targets | Definition of done |
|---|---|---|---|
| Sprint 7 | Live validation summary and artifact manifest hardening | Add a machine-readable validation summary, artifact manifest, stable artifact paths, and explicit required-artifact presence checks to the live gate runner. | `run_live_workflow_validation.sh --config-only` writes Markdown and JSON summaries plus a manifest that can be consumed by CI without scraping logs. |
| Sprint 8 | Seed contract and backend endpoint preflight improvements | Add seed preflight metadata, backend capability probes, and strict seed report semantics that distinguish blocked APIs from partial persistence. | The seed report records backend URL, health status, required endpoint probes, and strict-mode blockers before mutating test data. |
| Sprint 9 | CI documentation and operational runbook updates | Document the third-loop evidence contract, required artifacts, and interpretation rules for PASS, FAIL, and BLOCKED outcomes. | Validation documentation explains the JSON summary, artifact manifest, seed preflight, and how CI should promote or reject a live result. |

The implementation remains deliberately fail-closed. A configuration-only pass proves that the gate can resolve compose and enforce local guardrails. A full live PASS still requires a healthy runtime stack, successful strict seed verification, and requested Playwright artifacts.

## Implementation Status

Sprint 7 has been implemented by extending `scripts/ci/run_live_workflow_validation.sh` to emit both a machine-readable JSON summary and an artifact manifest in addition to the existing Markdown summary. The config-only path now produces enough durable evidence for CI to validate compose resolution, frontend live guardrails, and artifact creation without scraping terminal output.

Sprint 8 has been implemented by extending `scripts/db/seed-e2e-data.ts` with backend endpoint preflight probes. The seed runner now records required and optional backend capability checks inside the structured seed report and aborts before mutating seed data when required backend endpoints are not routable with accepted status codes.

Sprint 9 has been implemented by documenting the new evidence contract and seed preflight semantics in `docs/validation/live-workflow-validation.md`. The runbook now distinguishes human-readable evidence, machine-readable summaries, artifact manifests, seed preflight reports, and browser evidence required for a promotable full live PASS.

| Sprint | Status | Validation target |
|---|---|---|
| Sprint 7 | Implemented | `scripts/ci/run_live_workflow_validation.sh --config-only` writes Markdown summary, JSON summary, artifact manifest, and resolved compose config. |
| Sprint 8 | Implemented | The deterministic seed runner records `backendPreflight` in `seed-report.json` and fails closed before mutation when required endpoint probes fail. |
| Sprint 9 | Implemented | The live workflow runbook documents the artifact and promotion contract for CI and operators. |

The full live stack, strict seed, and Playwright browser suite are still intentionally not downgraded into a synthetic PASS. They must be executed in a healthy live environment, with mocks disabled and the required artifacts present, before the result can be promoted.
