# Live Readiness Three-Sprint Implementation Plan

**Author:** Manus AI  
**Repository:** `bmsull560/Fabric_4L`  
**Date:** 2026-05-05  
**Objective:** Convert the current live-validation status from **NO GO/BLOCKED** to a runnable live environment that can support real frontend login, live backend calls, persisted-state verification, and Playwright workflow validation without mocks.

## Sprint Prioritization Summary

The implementation sequence follows the live-validation dependency chain. The backend-integrated L1–L6 stack must become healthy first, because frontend startup, live login, seed data, and Playwright validation are not meaningful until real backend services are reachable from the host environment.

| Sprint | Priority | Goal | Exit criteria |
|---|---:|---|---|
| Sprint 1 | P0 | Make the backend-integrated L1–L6 stack start and expose healthy host endpoints. | **Implemented and locally validated:** backend-integrated L1, L2, L3, L5, L6, Postgres, Redis, MinIO, and Neo4j reached healthy status after the readiness, migration, dependency-recovery, and host-gateway fixes. |
| Sprint 2 | P0 | Make the live frontend and deterministic seed/login path usable against the live backend stack. | **Implemented:** `dev:live`, `seed:live`, guarded live Playwright commands, live compose readiness parity, and live compose syntax validation are in place. Full credential-based UI login remains dependent on the backend auth contract exercised by the live suite. |
| Sprint 3 | P0 | Automate live workflow validation evidence collection and prevent mock-based false positives. | **Implemented:** `scripts/ci/run_live_workflow_validation.sh` validates compose, blocks mock-enabled runs, waits for service health, writes evidence artifacts, and optionally runs seed plus live P0 Playwright. [VERIFY:DOC-PROBE-001] |

## Sprint 1 Backlog: Backend Live-Stack Startup

Sprint 1 owns the concrete service startup blockers observed after the final live environment gate attempt. The first implementation pass targets source-level blockers that prevent containers from importing or starting, then validates the stack through compose and host endpoint probes.

| Item | Priority | Implementation target | Acceptance criteria |
|---|---:|---|---|
| L2 shared bootstrap resilience | P0 | Ensure `services/layer2-extraction/src/layer2_extraction/shared_bootstrap.py` resolves mounted shared framework code without hard-coded parent indexes. | L2 imports in the container and no longer exits with `IndexError` during uvicorn startup. |
| L6 shared bootstrap resilience | P0 | Ensure `services/layer6-benchmarks/src/shared_bootstrap.py` resolves mounted shared framework code without hard-coded parent indexes. | L6 imports in the container and no longer exits with `IndexError` during uvicorn startup. |
| L3 metrics import mismatch | P0 | Ensure `services/layer3-knowledge/src/api/main.py` re-exports `get_system_metrics` and `set_app_metrics` from the module where they actually live. | L3 imports in the container and no longer exits with missing-symbol import errors. |
| L5 migration database readiness | P0 | Harden the Layer 5 migration startup path so Alembic does not race or indefinitely fail against a just-started Postgres service. | `vf-bi-layer5-migrate` completes successfully and `vf-bi-layer5` starts. |
| L1 health/Redis readiness | P0 | Diagnose and fix the L1 API/worker health path so Redis-backed startup does not leave the API unhealthy once Redis is reachable. | `vf-bi-layer1` becomes healthy and `8001/health` responds from the host. |
| Compose dependency looseness for diagnosis | P1 | Keep strict production readiness, but reduce validation-stack deadlocks where downstream services remain permanently `Created` after upstream recoverable delays. | Services can be rebuilt/restarted and produce actionable health/log evidence during validation. |

## Sprint 2 Backlog: Frontend, Seed Data, and Login Readiness

Sprint 2 starts only after Sprint 1 can produce a healthy backend graph. It establishes the minimum real user path required for live workflow execution.

| Item | Priority | Implementation target | Acceptance criteria |
|---|---:|---|---|
| Documented live frontend command | P0 | Add or update the documented command that starts the frontend against L1–L6 live backend URLs. | A human and CI runner can start the frontend without enabling route mocks or MSW. |
| Live backend URL wiring | P0 | Ensure frontend environment variables point to live service URLs and fail closed if mock-mode variables are enabled. | Browser network traffic targets the live backend stack. |
| Deterministic seed tenant and users | P0 | Add a live seed command for tenant, admin, sales, reviewer, read-only users, account, evidence, formula, and workflow starter data. | Seed data survives reload and can be verified through backend persistence checks. |
| Login verification runbook | P0 | Document exact credentials and role expectations for live validation users in a safe development-only format. | Each role can log in and lands in the expected tenant/workspace context. |

## Sprint 3 Backlog: Live Validation Automation and Evidence

Sprint 3 converts the live environment into a repeatable validation gate. Its highest priority is to avoid counting mocked tests as live proof.

| Item | Priority | Implementation target | Acceptance criteria |
|---|---:|---|---|
| Live-only Playwright gate | P0 | Add a command that requires a reachable frontend and backend health manifest before tests run. | The gate fails before browser execution if any backend service is unavailable. |
| Mock-ban guardrails | P0 | Add validation that rejects route fulfillment, fixture-only pass paths, and MSW/mock mode in live suites. | Live workflow reports cannot mark PASS when backend calls are mocked. |
| Workflow evidence artifacts | P0 | Capture traces, screenshots, network/backend call evidence, and persistence checks per workflow. | Every workflow PASS/FAIL/BLOCKED has supporting artifacts. |
| Final readiness report update | P0 | Update live workflow documentation based on actual gate output. | The report states exact PASS/FAIL/BLOCKED counts and links to artifacts. |

## Execution Note

Implementation began with Sprint 1 because it was the dependency root for all remaining live-readiness work. The first execution pass has now implemented the P0 backend startup fixes, frontend live-mode guardrails, deterministic seed entrypoint, and live validation automation. The remaining highest-priority follow-up is to run the full canonical `docker-compose.live.yml` stack with seed and Playwright enabled in a clean validation window and record the resulting PASS/FAIL/BLOCKED counts without counting any mocked execution path as live success.
