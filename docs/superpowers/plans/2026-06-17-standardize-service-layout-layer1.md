# Sub-plan B: Standardize Service Layout and Delete Layer 1 Duplicate Source Tree (#4)

**Goal:** Eliminate the duplicate `services/layer1-ingestion/src/` tree and adopt one consistent package layout for all six services.

**Canonical layout**
- `services/layerN-*/src/<layerN_*>/` as the nested package root.
- Remove flat `src/api/`, `src/shared/`, etc. duplicates inside Layer 1.

**Files to inspect / modify**
- `services/layer1-ingestion/src/` (flat duplicate tree)
- `services/layer1-ingestion/src/layer1_ingestion/` (canonical nested tree)
- `services/layer1-ingestion/pyproject.toml`
- `services/layer{2,3,4,5,6}-*/src/` (review for layout consistency)
- All Layer 1 imports referencing `src.*`

**Approach**
1. Identify files present in both Layer 1 trees and reconcile divergent copies.
2. Move any unique files from the flat tree into `layer1_ingestion/`.
3. Delete the flat `services/layer1-ingestion/src/` modules, keeping only `layer1_ingestion/`.
4. Update `pyproject.toml` `pythonpath`, ruff/mypy includes, and pytest settings.
5. Replace `from src.` imports with `from layer1_ingestion.` across the service and tests.
6. Propose a standard layout document for future services.

**Validation**
- `make test-layer1` passes.
- `make lint-layer1` passes.
- `make typecheck-layer1` passes.
- No `from src.` imports remain in `services/layer1-ingestion/`.

**Rollback**
Restore the flat tree from git history if tests fail unexpectedly.

**Risks**
- Divergent files may contain fixes that were not backported to the canonical tree.
- Import rewrites can miss dynamic imports or string-based module references.
