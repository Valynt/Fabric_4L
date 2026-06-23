# Merge conflict inventory — 2026-05-19

Status of committed merge-conflict markers on `main` (`<<<<<<< HEAD` etc.).
All conflicts originate from PR `315e84c1` (sprint-2/arch-modernization)
versus prior `main`.

## Resolved in this pass (10 files)

| File | Side taken | Notes |
|---|---|---|
| `services/layer2-extraction/src/layer2_extraction/extraction/cache.py` | `315e84c1` | Structured logging via `_log_cache_failure`, narrowed exception handlers, preserves fail-open. |
| `tests/contract/conftest.py` | HEAD | `_contract_service_gate` keeps `contract_static_no_service` bypass; matches downstream `check_services_availability`. |
| `tests/security/test_tenant_repository_filter_presence.py` | HEAD | File-based source inspection (no Layer3/Layer6 imports at collection). `315e84c1`'s `search_products` assertion not portable: method does not exist on current `ProductService`. |
| `scripts/export_openapi.py` | HEAD | Conditional shim installers (`_install_openapi_dependency_shims`) required by `_export_service_in_process`. |
| `services/layer4-agents/src/api/routes/workflows.py` | `315e84c1` | Adds `WorkflowOutput` envelope. Backward-compatible via `model_config = ConfigDict(extra="allow")`. |
| `services/layer4-agents/src/services/context_gatherer.py` | `315e84c1` | Uses `tenant_cypher` helpers (`fetch_tenant_validated_records` / `_single`); cleaner than HEAD's manual `records[0]` extraction. |
| `services/layer5-ground-truth/src/layer5_ground_truth/api/main.py` | HEAD | Keeps structured `http_exception_handler` / `unhandled_exception_handler`, richer `JWT_SECRET_DENYLIST`. Required imports `Layer3PolicyDeniedError` / `Layer3TenantMismatchError` only exist on HEAD of `layer3_client.py`. |
| `services/layer5-ground-truth/src/layer5_ground_truth/api/router.py` | hybrid | Imports `FreshnessCheckResponse` + `FreshnessSummaryResponse` (used by route response_models). Drops HEAD's ad-hoc `sync_to_kgResult` / `list_staleResult` TypedDictModel locals; uses canonical `SyncToKgResponse` / `StaleTruthsResponse`. |
| `services/layer5-ground-truth/src/layer5_ground_truth/api/schemas.py` | HEAD | Adds `FreshnessCheckResponse`, `FreshnessCounts`, `FreshnessSummaryResponse` to `__all__`; re-exported from `..services.freshness_contracts`. |
| `services/layer5-ground-truth/src/layer5_ground_truth/shared_bootstrap.py` | HEAD | Nested `ours/theirs` shell over identical imports; HEAD's multi-line form retained. Originally missed from upstream list. |

**Validation:** all 10 files pass `ast.parse`. `tests/security/test_tenant_repository_filter_presence.py` collects 3 tests. `tests/contract/...` collects 379 tests; the single remaining collection error (`test_layer3_compat_metrics.py`) is caused by the unresolved `services/layer3-knowledge/src/db/query_execution.py` (out of scope, see below).

## Deferred: contract regeneration (2 JSON files)

| File | Blocker |
|---|---|
| `contracts/openapi/layer4-agents.json` (657 conflict lines) | L4 app import chain pulls in Layer 3 (`services/__init__.py` → `evidence_search.py` → `db/query_execution.py`). L3 must be resolved before `python scripts/export_openapi.py --only layer4-agents.json` can run. |
| `contracts/openapi/layer5-ground-truth.json` (9 conflict lines) | L5 `api/main.py` imports `..integration.layer3_client` (~900-line file, 4 multi-region conflicts with nested `ours/theirs/theirs` markers). HEAD side defines `Layer3PolicyDeniedError`/`Layer3TenantMismatchError` required by main.py; `315e84c1` side replaces them with flat `L3_ERR_*` constants. Resolution is mechanical (must take HEAD) but file is large enough to deserve its own pass. |

**Recommended next pass:**
1. Resolve `services/layer5-ground-truth/src/layer5_ground_truth/integration/layer3_client.py` → HEAD (forced by `api/main.py` import names).
2. Run `python scripts/export_openapi.py --only layer5-ground-truth.json`.
3. Resolve Layer 3 chain (see below), then run `--only layer4-agents.json`.

## Remaining ~37 files (out of scope for pass B)

Grouped by required follow-up action.

### A. Layer 3 chain (required before L4 regen)
- `services/layer3-knowledge/src/db/query_execution.py` (10 conflict regions; blocks contract collection)
- `services/layer3-knowledge/src/agents/provenance_tracking.py`
- `services/layer3-knowledge/src/agents/roi_calculation.py`
- `services/layer3-knowledge/src/agents/value_tree_projection.py`
- `services/layer3-knowledge/src/agents/whitespace_analysis.py`
- `services/layer3-knowledge/src/analytics/centrality.py`
- `services/layer3-knowledge/src/analytics/communities.py`
- `services/layer3-knowledge/src/analytics/similarity.py`
- `services/layer3-knowledge/src/api/dependencies_tenant.py`
- `services/layer3-knowledge/src/api/routes/calculators.py`
- `services/layer3-knowledge/src/api/routes/entities.py`
- `services/layer3-knowledge/src/api/routes/signals.py`
- `services/layer3-knowledge/src/api/routes/value_packs.py`
- `services/layer3-knowledge/tests/test_query_execution_boundary.py`
- `services/layer3-knowledge/README.md`

### B. Layer 5 transitive imports
- `services/layer5-ground-truth/src/layer5_ground_truth/integration/layer3_client.py` (forced HEAD)
- `services/layer5-ground-truth/src/layer5_ground_truth/services/freshness_monitor.py`
- `services/layer5-ground-truth/tests/test_layer3_failure_modes.py`

### C. Layer 4 test
- `services/layer4-agents/tests/test_context_gatherer.py` — references both `tenant_query_helper` (HEAD) and `tenant_cypher` (315e84c1). Must align with our `context_gatherer.py` choice (`315e84c1`, i.e. `tenant_cypher`).

### D. Build / scripts / tooling
- `Makefile`
- `scripts/check_layer3_cypher_scope.py`
- `scripts/ci/check_conflict_markers.sh`
- `scripts/ci/check_layer3_source_mirror.py`
- `scripts/resolve_conflicts.py`

### E. Frontend generated / contract artifacts (regenerate after backend chain resolves)
- `apps/web/src/api/generated/l4/index.ts`
- `apps/web/src/api/generated/l5/index.ts`
- `apps/web/src/api/workflows.ts`
- `apps/web/scripts/quality/assert-compatibility-shims-registered.mjs`
- `apps/web/scripts/quality/assert-frontend-hygiene.mjs`
- `packages/platform-contract/src/typescript/generated/layer4_agents.ts`
- `packages/platform-contract/src/typescript/generated/layer5_ground_truth.ts`

### F. Docs / audit reports
- `docs/governance/compatibility-debt-registry.md`
- `docs/security/multi-tenancy.md`
- `fabric_audit/v1.0.0_release_gate_report_2026-05-12.md`
- `docs/archive/quality-reports/2026-05-22/RELEASE_READINESS_AUDIT_2026-05-12.md`
- `docs/archive/quality-reports/2026-05-22/TEST_COVERAGE_RUBRIC_AUDIT_2026-05-12.md`
- `signoff-evidence/phase-04-contracts/contract-static-tests.txt`

## Suggested resolution order for next pass

1. Layer 3 group A (resolves contract collection error and unblocks L4 regen chain)
2. Layer 5 group B (`layer3_client.py` first → unblocks L5 regen)
3. Layer 4 test C (align with `tenant_cypher` choice)
4. Run `python scripts/export_openapi.py --only layer4-agents.json layer5-ground-truth.json` to regenerate both contract JSONs
5. Regenerate frontend group E from the new contracts (`packages/platform-contract` typed clients + `apps/web/src/api/generated/*`)
6. Resolve group D build/scripts; ensure CI conflict-marker check is clean
7. Resolve group F docs/audit reports (text-only conflicts)
