# Live Readiness Second Three-Sprint Implementation Plan

**Author:** Manus AI  
**Repository:** `bmsull560/Fabric_4L`  
**Date:** 2026-05-05  
**Objective:** Extend the first live-readiness sprint loop by hardening the live validation gate, making deterministic seed verification machine-checkable, and preventing live Playwright results from passing through mocked route fulfillment or missing artifacts.

## Sprint Prioritization Summary

The first sprint loop made the live stack more runnable and introduced guarded live commands. The next highest-priority work is to make the gate more trustworthy. A live validation result should be classified from sanitized evidence, the seed step should emit a deterministic contract artifact, and live Playwright should fail before or during execution when mocks or missing evidence could produce false confidence.

| Sprint | Priority | Goal | Exit criteria |
|---|---:|---|---|
| Sprint 4 | P0 | Harden the live workflow gate so failures produce actionable, sanitized evidence and clear PASS/FAIL/BLOCKED classification. | The live validation script captures resolved compose, container status, health details, endpoint probes, and service logs on failure without leaking environment secrets. |
| Sprint 5 | P0 | Make deterministic live seed verification a first-class contract instead of console-only output. | The seed command writes a machine-readable report, enforces required seed areas when requested, and exposes the report path to the live gate summary. |
| Sprint 6 | P0 | Enforce live Playwright mock bans and artifact requirements for live-mode browser validation. | Live-mode helper calls reject route fulfillment, Playwright config writes live artifacts to deterministic paths, and the live gate verifies trace/report artifacts when Playwright is requested. |

## Sprint 4 Backlog: Live Gate Evidence Hardening

Sprint 4 focuses on the gate runner because it is the release-readiness entry point. The previous implementation created the runner; this sprint makes it operationally useful when a stack is partially unhealthy or an endpoint fails.

| Item | Priority | Implementation target | Acceptance criteria |
|---|---:|---|---|
| Failure evidence bundle | P0 | Add reusable evidence collection to `scripts/ci/run_live_workflow_validation.sh`. | On any failure after compose validation, artifacts include container status, resolved health state, sanitized service logs, and endpoint probe results. |
| Sanitized classification | P0 | Write summary status as `PASS`, `FAIL`, or `BLOCKED` with concise details. | A missing/unhealthy service produces a summary that states exact blockers without dumping secrets. |
| Endpoint manifest | P0 | Capture frontend and backend probe status codes in a separate artifact. | Endpoint evidence survives failed runs and can be attached to reports. |

## Sprint 5 Backlog: Deterministic Seed Verification Contract

Sprint 5 makes the canonical Meridian fixture verifiable by automation. It avoids inventing new backend behavior and instead records the existing seed status table in structured form.

| Item | Priority | Implementation target | Acceptance criteria |
|---|---:|---|---|
| Seed report JSON | P0 | Extend `scripts/db/seed-e2e-data.ts` with `--report-json` / `SEED_REPORT_JSON`. | The seed script writes backend URL, tenant ID, status rows, and an aggregate status to JSON. |
| Strict seed mode | P0 | Add `--strict` / `SEED_STRICT=true`. | The seed step exits non-zero if any required area is not `present`. |
| Gate integration | P0 | Teach the live validation runner to pass the report path to `live-seed`. | The live summary links to the seed report artifact when seed is requested. |

## Sprint 6 Backlog: Live Playwright Mock-Ban and Artifact Enforcement

Sprint 6 closes the gap between “browser tests ran” and “browser tests proved live behavior.” It strengthens the helper layer and Playwright output configuration so the validation runner can verify evidence after a requested live browser run.

| Item | Priority | Implementation target | Acceptance criteria |
|---|---:|---|---|
| Live mock helper ban | P0 | Update `mockSequentialResponses` to reject live mode. | Any live test that tries to install sequential fulfilled mocks fails with a direct error. |
| Stronger backend requirement | P0 | Update `requireBackendOrThrow` to enforce live-mode mock flags. | Backend-integrated live tests fail closed if mock environment flags are enabled or the backend URL is invalid. |
| Live artifact paths | P0 | Configure Playwright report/output folders from environment variables. | The live gate can require HTML, JUnit, and trace output locations after Playwright completes. |
| Artifact verification | P0 | Add post-Playwright artifact checks to the live validation runner. | A requested live Playwright run cannot be summarized as pass if expected report artifacts are missing. |

## Execution Note

This plan intentionally starts with evidence and contract hardening rather than new product features. The repository already has live commands and a seeded backend-integrated suite; the immediate risk is false-positive live readiness. These sprints make the next full live execution auditable and fail-closed.

## Implementation Status

The second sprint loop has been implemented in repository code and documentation. Sprint 4 hardened `scripts/ci/run_live_workflow_validation.sh` with sanitized failure evidence, status classification, endpoint probes, service-log capture, and summary artifacts. Sprint 5 extended `scripts/db/seed-e2e-data.ts` with structured JSON reporting and strict seed verification controls, and the live gate now mounts the artifact directory into the seed container so reports persist. Sprint 6 hardened live browser validation by banning central sequential mock fulfillment in live mode, validating backend URL and mock flags in backend-required tests, configuring deterministic Playwright artifact paths, enabling live traces, and enforcing post-run artifact existence.

| Sprint | Status | Validation performed |
|---|---|---|
| Sprint 4 | Implemented | `bash -n scripts/ci/run_live_workflow_validation.sh` and config-only live gate execution passed. |
| Sprint 5 | Implemented | Seed report and strict-mode code type-check through the frontend TypeScript project. Runtime strict seed still requires a healthy live backend and will fail closed if any required seed row is partial or blocked. |
| Sprint 6 | Implemented | Playwright config and helper changes passed the frontend TypeScript check; requested live Playwright execution now requires HTML, JUnit, and trace artifacts. |

The completed work is intentionally fail-closed. A full live PASS still requires executing the live stack, seed, and Playwright run in an environment where the stack can become healthy. The config-only validation path passed in the current environment and should be used as a preflight before full live execution.
