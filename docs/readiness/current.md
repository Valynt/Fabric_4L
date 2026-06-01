# Current Launch Readiness (Canonical)

- **Canonical Source:** This document is the single source of truth for launch readiness criteria and percentage.
- **Generated From CI:** `make verify` (lint, type-check, tests, contract tests, build gates) and release-gate evidence scripts.
- **Snapshot Date (UTC):** 2026-06-01
- **Last Updated:** 2026-06-01
- **Launch Readiness:** **CONDITIONALLY UNBLOCKED — service-backed skipped-test evidence pending** (see Current Status below)

## Current Status

> ✅ **All current P0 blockers have passing local evidence or have been verified resolved in the current working tree as of 2026-06-01.**
>
> Final launch sign-off still requires running the skipped service-backed tenant isolation tests in CI/staging with PostgreSQL and Redis available.
>
> | ID | Area | Status | Evidence |
> |---|---|---|---|
> | P0-1 | Security / RLS | ✅ Resolved | `pytest tests/security/test_rls_enforcement.py -q --no-mandatory-dep-check` passes 26/26 |
> | P0-2 | Architecture | ✅ Resolved | `pytest tests/arch/ -q --no-mandatory-dep-check` passes 35/35 |
> | P0-3 | Security / Cache | ✅ Resolved | `pytest tests/cache/test_redis_tenant_isolation.py -q --no-mandatory-dep-check` passes 16/16 |
> | P0-4 | Infra / K8s | ✅ Resolved | `scripts/ci/test_placeholder_digest_detection.sh` passes 9/9; `scripts/ci/check-k8s-image-digests.sh` passes |
>
> **Previously resolved:**
> - ✅ P0-0 — Merge conflict markers resolved
> - ✅ P0-004 — Deploy workflow now uses AWS OIDC auth + server-side dry-run + rollout checks
> - ✅ P0-008 — API gateway Alembic migration structure created
> - ✅ P0-010 — Readiness docs regenerated from live evidence

## CI Evidence Inputs

- `make verify`
- `scripts/ops/release-gate.sh`
- `scripts/ops/render-release-summary.sh`
- `artifacts/release/gate-result.json`
- `artifacts/release/summary.md`
- `scripts/ci/platform_contract_lint.py`
- `scripts/ci/check_tool_contracts.py`
- `.github/workflows/graph-module-tests.yml` (Graph Query module quality gates on PR + release branches)

## Sprint Roadmap Progress (as of 2026-05-17)

| Sprint | Status | Key outcomes |
|---|---|---|
| S1 — Foundations | ✅ Complete | `PYTEST` var fixed to use pipx binary; `make setup` installs into pytest venv; root `pytest.ini` `addopts` scoped (removed `--timeout`/`--randomly-seed`); `CONTRIBUTING.md` updated |
| S2 — Core fixes | ✅ Complete | `get_openai_provider` mock → `get_llm_provider`; `Layer3KnowledgeClient` → `Layer3Client` import fixed (0-signal regression resolved); `HarnessRunRepository.list()` tuple handling verified; `CoreferenceResolver` verified implemented; `platform-contract` verified Pydantic v2 |
| S3 — Integration | ✅ Complete | Formula category filter verified implemented; k8s Kustomize overlay verified correct; Layer 4 secret names verified (`llm-provider-secret` + `TOGETHER_API_KEY`) |
| S4 — Release prep | ✅ Complete | Layer 3 Neo4j tenant isolation audit verified (see `docs/reference/layer3-tenant-isolation-audit.md`); `SqlTelemetryEmitter.get_events()` verified intentional `NotImplementedError`; readiness doc updated |
| S5 — Broad GA sprint | ✅ Complete (2026-05-19) | All 12 P0 + 11 P1 code blockers resolved; frontend 1773/1773 ✅; backend arch/cache/contract/unit 677/677 ✅; security P0/P1 suites 78/78 ✅; LLM cost telemetry 66/66 ✅; staging digests fixed; state inspector auth wired; assurance score ≥85% |

## Launch Criteria

The platform is launch-ready when all of the following are true:

1. `make verify` passes with no failing gate.
2. Contract lint + tool contract checks pass.
3. Security smoke tests pass.
4. Graph Query module gate passes on PR and release branches (coverage: lines ≥90%, branches ≥80%, functions ≥90%; flaky rate ≤1.0%; contract and performance jobs green).
5. Release gate report indicates no P0 blockers.
6. Launch readiness percentage remains aligned across canonical docs.

## Historical Snapshot Tagging

Any archived readiness note that includes percentages must include at least one of:

- `Historical Snapshot`
- `Snapshot Date:`
- Filename prefix `ARCHIVED_`

This allows automated checks to distinguish historical records from canonical readiness state.

## Decision Artifact

- Canonical launch decision package: `docs/readiness/launch-decision-artifact.md`
