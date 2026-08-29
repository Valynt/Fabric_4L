# Brooks Shared-Hub & Code-Health Remediation

**Branch:** `fix/brooks-shared-hub-remediation`
**Description:** One PR that reduces the change radius of `value_fabric.shared`, removes speculative modules, decomposes three megafiles, and centralizes duplicated compat-surface contract tests — no runtime behavior changes.

## Goal
Address the four `brooks-health` warnings (R2 change radius, R1 megafiles, R4 speculative modules, R3 duplicated tests) so platform changes ripple less, each shared boundary is versioned, unused surface is not maintained, and one decision is enforced in exactly one place. All steps are behavior-preserving; each is independently committable and verifiable.

Assumptions (made under autopilot; change with reviewer feedback):
- New plan directory `plans/brooks-shared-hub-remediation/` rather than extending `plans/brooks-remediation/`, which covers a different issue set.
- "Archive" = delete files + record in governance notes (git history preserves them); no separate archive tree.
- [Step 1 ADJUSTED during execution] Pre-research over-counted removals. Verified with an exhaustive git-ls-files consumer scan, the safe deletions are `shared.billing_schemas`, `shared.tracing`, `shared.tests` (0 consumers each). `shared.testing` (8 test-tree consumers: L1/L2/L2-5/L5 conftests, tests/conftest.py, tests/integration) and `shared.projections` (1 test consumer: tests/integration/test_cross_store_consistency.py) are reached by the test suite and are KEPT per the Risk clause below. `shared.llm_safety` (4 runtime + 2 test use) is kept under the consumer policy. Additional zero-external-consumer modules found by the scan but OUTSIDE Step-1 scope (`shared.mcp_gateway`, `shared.storage`, top-level `http_client.py`, `tenant_context_metrics.py`, `security_middleware.py`) are documented on the policy-test allowlist for future cleanup rather than deleted here.

## Implementation Steps

### Step 1: Archive speculative shared modules + enforce consumer policy (R4)
- [x] Verify actual consumer counts (git ls-files scan) — corrected scope: delete `billing_schemas`, `tracing`, `tests`; keep `testing`, `projections` (test-tree consumers), `llm_safety` (plan).
- [x] Delete `packages/shared/src/value_fabric/shared/{billing_schemas,tracing,tests}/` via `git rm`.
- [x] Refresh `config/ci/type_escape_baseline.json` (`python scripts/ci/type_escape_ratchet.py --update`) to purge 2 stale `billing_schemas/webhooks.py` entries.
- [x] Create `packages/shared/SURFACES.md` governance note (consumer policy + boundary/version map; also feeds Step 4).
- [x] Create `tests/contract/test_shared_module_consumer_policy.py` — every non-`__init__` shared module has ≥1 external consumer or is on an explicit allowlist (allowlist covers `testing`, `projections`, and out-of-scope-but-kept `mcp_gateway`, `storage`, `http_client`, `tenant_context_metrics`, `security_middleware`).
- [x] Validate: `pytest tests/contract/test_shared_module_consumer_policy.py` (3 passed); `make contract-tests` static subset (484 passed, 0 failures — includes new test); `type_escape_ratchet` (passes, 7069); import smoke for kept modules (OK); deleted modules absent. Note: full `make verify` gate could not run via `make` (git-bash on Windows fails parsing the `$(PYTHON)` Windows drive path — pre-existing infra issue); its direct sub-commands that relate to this step were run individually and pass.
**Files:** `packages/shared/src/value_fabric/shared/{tracing,projections,billing_schemas,testing,tests}/` (delete), `packages/shared/src/value_fabric/shared/llm_safety/` (keep), new `tests/contract/test_shared_module_consumer_policy.py`, new `packages/shared/SURFACES.md` (governance note; or extend existing notes), `config/ci/` allowlist if the repo convention requires (mirror `behavior_readiness_waivers.yaml` style).
**What:** Delete the five zero-runtime-consumer modules (confirmed: tracing/projections/billing_schemas/tests 0/0, testing 6 test-only); keep `llm_safety` (5 uses) under policy. Add a contract test asserting every non-`__init__` shared module either has ≥1 runtime consumer or is on an explicit allowlist, so a module may not live in `shared` without a consumer and a contract test.
**Testing:** `pytest tests/contract/test_shared_module_consumer_policy.py`; `make contract-tests`; full `make verify` (deletion must not break any import).

### Step 2: Centralize compat-surface contract tests (R3)
**Files:** new `tests/contract/compat_surface/harness.py` (hoists `get_route_prefix`, `collect_paths`, `collect_routes`, middleware-order helpers), `services/layer4-agents/tests/test_compat_app_surface_contract.py`, `services/layer5-ground-truth/tests/test_compat_app_surface_contract.py`, `services/layer6-benchmarks/tests/test_compat_app_surface_contract.py` (thin per-layer files importing the harness), `services/layer6-benchmarks/tests/test_benchmark_route_matrix_and_contracts.py` (delete after merging into `test_benchmark_route_matrix.py`).
**What:** Remove the triplicated helper code (verified: L4 has 3 tests, L5 4, L6 5 — all share the same copied helpers) by centralizing; each layer test keeps only its layer-specific assertions and imports the shared harness. Merge the two L6 route-matrix files so happy/hostile paths, dataset lineage, and OpenAPI shape live in one file (`test_benchmark_route_matrix.py`).
**Testing:** run `pytest` for L4, L5, L6 test trees; `pytest tests/contract`; confirm route-matrix coverage counts are unchanged after the merge.

### Step 3: Decompose megafiles with behavior-preserving shims (R1)
**Files:**
- `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` → new `services/layer1-ingestion/src/layer1_ingestion/shared/tasks/` package (`crawl.py`, `extraction.py`, `post_processing.py`, `validation.py`, `storage.py`, `notification.py`, `dlq.py`, `cleanup.py`); `tasks.py` reduced to a re-export shim.
- `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/persistence.py` → extract the ~26 `_x_to_db`/`_x_from_db` serializers into `serialization.py`; keep `PersistenceManager`/`update_knowledge_graph` (re-export serializers from `persistence.py` so existing imports keep working).
- `services/layer4-agents/src/layer4_agents/engine/executor.py` → extract pure helpers only; `OrchestrationController` and the `WorkflowExecutor = OrchestrationController` alias stay intact.
**What:** Split each megafile by responsibility (queue-handler modules by stage, serializer module, pure helpers). Preserve public names and Celery autodiscovery (the shim keeps `layer1_ingestion.shared.tasks` resolvable). Move/mirror behavior tests next to extracted code.
**Testing:** per-layer `pytest` + a Python import smoke (`python -c "import layer1_ingestion.shared.tasks"`, `...audit_orchestrator.persistence`, `...engine.executor`); `make test-layer*` for affected layers; expect the same pass counts as before the split.

### Step 4: Versioned shared boundaries + bounded-change policy (R2)
**Files:** `packages/shared/src/pyproject.toml` (part of the `value-fabric-shared` version line, with per-boundary surface markers), `packages/shared/src/value_fabric/shared/identity/__init__.py` and `.../error_handling/__init__.py` (explicit public-API exports as versioned surfaces), new `packages/shared/SURFACES.md` (boundary → version map), new `tests/contract/test_shared_boundary_contracts.py` (snapshots each boundary's public surface; asserts a boundary change requires a coordinated version bump), `scripts/ci/` structural-preflight drift check (mirror `check:api-types`).
**What:** Make `identity` (590 uses) and `error_handling` (283 uses) independently versioned, narrow surfaces reachable only through explicit `__init__.py` exports. Add contract tests on each boundary so any cross-service change must be coordinated with a version bump (bounded-change policy), enforced in CI structural preflight.
**Testing:** `make contract-tests`; import smoke for all nine services importing `value_fabric.shared` (`identity`/`error_handling`); run the structural-preflight gate; spot-run L4 and API test suites (heaviest consumers).

## Validation (whole PR)
- `make verify` (canonical gate) after each step.
- `make contract-tests`; `make check-behavior-contract` (no behavior intent changes).
- `make check-conflict-markers`, `make check-migration-heads` (no migrations touched — quick guards).
- No frontend change → no `pnpm --dir apps/web` gates required; `pnpm run check:api-types` untouched.

## Risk / Follow-up
- Step 3 shims must be exact — a missed re-export breaks broker/Celery tasks; mitigated by import smoke + per-layer test counts before/after.
- Step 4 is the largest blast radius; done last so the shared hub is clean (post Step 1) when boundaries are pinned.
- If any zero-consumer module is actually reached dynamically (e.g., via pkg_resources or getattr), Step 1 must be adjusted; the consumer-policy contract test will catch it.