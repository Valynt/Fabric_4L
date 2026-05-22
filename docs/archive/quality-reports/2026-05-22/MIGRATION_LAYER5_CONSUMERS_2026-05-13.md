# Layer 5 Consumer Migration Report — 2026-05-13

## Objective

Migrate all production/runtime consumers from `value_fabric.layer5.*` imports to canonical service-path imports per ADR-027 (service-first canonical model).

## Discovery

**Result: Zero production imports found.**

A comprehensive scan of the repository (`services/`, `value_fabric/`, `scripts/`, `tests/`) found **no occurrences** of `from value_fabric.layer5` or `import value_fabric.layer5` outside of:

- The compatibility shim files themselves (`value_fabric/layer5/`)
- Tests that intentionally verify shim integrity (`tests/ci/test_check_layer5_shim_integrity.py`)
- Architecture sentinel tests that track canonical vs. compatibility path pairs

This indicates Layer 5 consumers were already using `layer5_ground_truth.*` directly.

## Critical Finding

**Canonical imports were broken from the repo root.**

While `services/layer5-ground-truth/pyproject.toml` correctly set `pythonpath = ["src", ...]` for in-service test runs, the **root `pytest.ini`** did not include `services/layer5-ground-truth/src/`. This meant:

- `layer5_ground_truth` was **not importable** when running `pytest` from the repo root
- `value_fabric.layer5` also failed because the shim tries to `from layer5_ground_truth import *`

## Fixes Applied

### 1. Root pytest.ini — enable canonical imports

**File:** `pytest.ini`

```diff
-pythonpath = . packages/shared/src
+pythonpath = . packages/shared/src services/layer5-ground-truth/src
```

This makes `layer5_ground_truth` importable from any test run initiated at the repo root.

### 2. Regression tests — prove canonical imports work

**File:** `tests/arch/test_canonical_module_sentinels.py`

Added 5 regression tests:

| Test | Purpose |
|------|---------|
| `test_layer5_ground_truth_imports_directly` | `layer5_ground_truth` is importable without `value_fabric` namespace |
| `test_layer5_api_imports_directly` | `layer5_ground_truth.api` resolves via canonical path |
| `test_layer5_models_imports_directly` | `layer5_ground_truth.models` resolves via canonical path |
| `test_layer5_resolves_to_canonical_service_tree` | Module path is `services/layer5-ground-truth/src/layer5_ground_truth/` |
| `test_layer5_no_production_imports_via_value_fabric_namespace` | No production code imports `value_fabric.layer5.*` |

### 3. ADR-027 update — document Layer 5 status

**File:** `docs/architecture/adr-027-layer3-canonical-path.md`

Updated Migration Status table:
- Layer 5: `Compliant` — "Canonical imports enabled 2026-05-13 via pytest.ini pythonpath; shim remains for backward compat"

## Files Modified

| File | Change |
|------|--------|
| `pytest.ini` | Added `services/layer5-ground-truth/src` to `pythonpath` |
| `tests/arch/test_canonical_module_sentinels.py` | Added 5 Layer 5 canonical import regression tests |
| `docs/architecture/adr-027-layer3-canonical-path.md` | Updated migration status notes for Layer 5 |

## Tests Run

```bash
# Architecture sentinel tests (all pass)
python -m pytest tests/arch/test_canonical_module_sentinels.py -v

# Contract import topology tests (pass, contract tests skip due to missing live services)
python -m pytest tests/contract/test_import_topology.py::TestImportTopology -v

# Layer 5 unit tests (pass)
python -m pytest services/layer5-ground-truth/tests/unit -v
```

**Results:** 7 architecture tests passed, 14 contract tests skipped (expected — no live services), 2 Layer 5 unit tests passed.

## Imports Intentionally Left in Place

| Location | Reason |
|----------|--------|
| `value_fabric/layer5/*.py` | Compatibility shim files — required by ADR-027 for backward compatibility |
| `tests/ci/test_check_layer5_shim_integrity.py` | Verifies shim integrity — explicitly tests the compatibility layer |
| `tests/arch/test_canonical_module_sentinels.py` | Tracks canonical vs. compatibility path pairs — architecture guardrail |

## Risks and Follow-Up

| Risk | Mitigation |
|------|------------|
| `value_fabric.layer5` shim may drift if developers add logic to it | CI sentinel tests enforce shim-only discipline |
| `pytest.ini` pythonpath addition may affect import resolution for other layers | Scoped to `layer5_ground_truth` package only; no other layer paths added |
| Plain `python` (outside pytest) still cannot import `layer5_ground_truth` unless PYTHONPATH is set | Expected for service-first model; services should be installed as packages or run in containers with proper paths |

## Acceptance Criteria

- [x] No production/runtime code imports `value_fabric.layer5.*`
- [x] `layer5_ground_truth` canonical imports work from repo root pytest runs
- [x] `value_fabric/layer5/` shim remains intact for backward compatibility
- [x] `value_fabric/__init__.py` path appending unchanged
- [x] Existing Layer 5 tests still pass
- [x] Regression tests prove canonical import parity
