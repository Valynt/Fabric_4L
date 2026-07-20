# Contract Freshness Gate Evidence

> **Audit note (2026-07-18):** The gate inventory mentions only Layer 1–Layer 6 OpenAPI files. The current `scripts/ci/check_contract_freshness.sh` also checks `layer7-billing.json` and `fabric-4l-api.json`, so this evidence record is incomplete for the current gate scope.

**Author:** Manus AI  
**Date:** 2026-05-05  
**Scope:** Fabric_4L frontend-backend type-alignment gate between Sprint 1 and Sprint 2.

## Summary

This document records the repository-owned contract freshness gate added after Sprint 1 OpenAPI source-of-truth reconciliation. The gate makes the current backend FastAPI service sources and frontend generated DTO artifacts a deterministic, testable contract boundary. It regenerates Layer 1 through Layer 6 OpenAPI files, regenerates frontend generated TypeScript DTO files, and fails when those generated artifacts differ from the committed repository state.

| Gate Asset | Purpose | Status |
|---|---|---|
| `scripts/ci/check_contract_freshness.sh` | Local and CI executable freshness gate for OpenAPI and generated frontend DTO artifacts. | Added |
| `Makefile` target `contract-freshness` | Repository-standard command surface for running the gate locally. | Added |
| `.github/workflows/contract-freshness.yml` | Dedicated CI workflow for backend, OpenAPI, and frontend generated-contract changes. | Added |

## Gate Behavior

The gate executes `python3 scripts/export_openapi.py` from the repository root and verifies that the six live source-backed OpenAPI specifications exist, are non-empty, and parse as valid JSON. It then runs `pnpm run generate:types` from `apps/web` and compares the resulting OpenAPI JSON and generated frontend DTO directory against the committed Git state.

| Step | Command | Drift Boundary |
|---|---|---|
| OpenAPI regeneration | `python3 scripts/export_openapi.py` | `contracts/openapi/layer1-ingestion.json` through `contracts/openapi/layer6-benchmarks.json` |
| Frontend DTO regeneration | `cd apps/web && pnpm run generate:types` | `apps/web/src/api/generated/` |
| Drift check | `git diff --exit-code` | Fails when generated outputs are stale or uncommitted |

## Validation Evidence

The gate was executed locally after implementation with the current Sprint 1 contract artifacts already committed. The validation completed successfully and reported that all six source-backed OpenAPI files were verified, all frontend generated DTO files were regenerated, and no generated contract drift remained.

| Validation | Result |
|---|---|
| Layer 1 through Layer 6 OpenAPI export | PASS |
| Required OpenAPI JSON presence and parseability | PASS |
| Frontend generated DTO regeneration for L1-L6 and signals | PASS |
| Drift check over OpenAPI and generated frontend DTOs | PASS |

## Remaining Constraints

The signals OpenAPI contract remains intentionally static because Sprint 1 did not identify a repository FastAPI source for the signals service. The freshness gate therefore protects the current source-backed Layer 1 through Layer 6 contracts and the full frontend generated DTO output directory, including generated signals types derived from the static signals OpenAPI file.

## Handoff to Sprint 2

Sprint 2 should now build on this gate by moving selected frontend API boundary code from generated DTO exposure toward runtime-validated DTO parsing and DTO-to-domain adapters. The freshness gate should remain green before and after each Sprint 2 migration slice so runtime validation work does not mask schema-generation drift.
