# L6 Package Restructuring Plan

**Status:** Planning Phase  
**Created:** 2026-05-28  
**Priority:** HIGH  
**Blocks:** L6 canonical imports, facade removal, test migration

## Goal

Make L6 importable through its canonical package name `layer6_benchmarks.*` without relying on `value_fabric.layer6.*`.

**Target end-state:** `layer6_benchmarks.*` imports work from repo root, service directory, tests, and CI.

## 1. Current L6 Layout Inventory

### Service Root Structure
```
services/layer6-benchmarks/
├── Dockerfile.full
├── Dockerfile.live
├── pyproject.toml
├── README.md
├── src/                    # CURRENT FLAT STRUCTURE (MISMATCH)
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── settings.py
│   ├── shared_bootstrap.py
│   ├── adapters/
│   │   └── value_fabric_api.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── deps.py
│   │   ├── schemas.py
│   │   ├── startup_logging.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── benchmarks.py
│   │       └── system.py
│   ├── metrics/
│   │   ├── __init__.py
│   │   └── prometheus_metrics.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── benchmark_dataset.py
│   ├── observability/
│   │   ├── __init__.py
│   │   └── metrics_contract.py
│   ├── repositories/
│   │   └── benchmark_repository.py
│   └── layer6_benchmarks/     # EXISTING NESTED DIR (MINIMAL)
│       └── logging_config.py
└── tests/
```

### pyproject.toml Configuration
```toml
[project]
name = "layer6-benchmarks"
version = "1.0.0"

[tool.hatch.build.targets.wheel]
packages = ["src"]  # CURRENT: Treats entire src/ as package root

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = [".", "src", "../..", "../../packages/shared/src"]  # LOCAL CONFIG
```

### Files Using Relative Imports
**Flat modules using `from .` (will break without package context):**
- `src/__init__.py`: `from .settings import`
- `src/database.py`: `from .config import`
- `src/config.py`: `from .settings import`
- `src/api/startup_logging.py`: `from ..settings import`
- `src/api/routes/system.py`: `from .. import main as handlers`
- `src/api/routes/benchmarks.py`: `from ..deps import`
- `src/metrics/__init__.py`: `from .prometheus_metrics import`
- `src/metrics/prometheus_metrics.py`: `from ..observability.metrics_contract import`
- `src/repositories/benchmark_repository.py`: `from ..models.benchmark_dataset import`
- `src/models/__init__.py`: `from .benchmark_dataset import`

### Public Entrypoints
- `src/api/main.py`: FastAPI app entrypoint
- `src/database.py`: Neo4j driver management
- `src/settings.py`: Pydantic settings

### Tests Importing via Facade
**All 16 L6 test files currently use `value_fabric.layer6.*`:**
- `tests/conftest.py`: `import value_fabric.layer6.database as database`
- `tests/test_api_schemas.py`: `from value_fabric.layer6.api.schemas import`
- `tests/test_api_tenant_propagation.py`: `from value_fabric.layer6.api.deps import`
- `tests/test_benchmark_api.py`: `from value_fabric.layer6.api.main import app`
- `tests/test_benchmark_edge_cases.py`: `from value_fabric.layer6.api.main import app`
- `tests/test_benchmark_route_matrix.py`: `from value_fabric.layer6.api.main import app`
- `tests/test_benchmark_route_matrix_and_contracts.py`: `from value_fabric.layer6.api.main import app`
- `tests/test_database_driver.py`: `import value_fabric.layer6.database as db_module`
- `tests/test_metrics_contract.py`: `import value_fabric.layer6.api.main as main_module`
- `tests/test_metrics_prometheus.py`: `from value_fabric.layer6.metrics.prometheus_metrics import`
- `tests/test_models_benchmark_dataset.py`: `from value_fabric.layer6.models.benchmark_dataset import`
- `tests/test_observability_metrics_contract.py`: `from value_fabric.layer6.observability.metrics_contract import`
- `tests/test_repository_pures.py`: `from value_fabric.layer6.models.benchmark_dataset import`
- `tests/test_repository_tenant_isolation.py`: `from value_fabric.layer6.models.benchmark_dataset import`
- `tests/test_scope_authorization.py`: `from value_fabric.layer6.api.schemas import`
- `tests/test_settings_validation.py`: `from value_fabric.layer6.settings import`
- `tests/test_startup_logging.py`: `from value_fabric.layer6.api.startup_logging import`

### Dockerfile References
**Dockerfile.full:**
```dockerfile
COPY services/layer6-benchmarks/src/ ./value_fabric/layer6/
```
**Dockerfile.live:**
```dockerfile
COPY services/layer6-benchmarks/src/ ./value_fabric/layer6/
```

### K8s/CI/Makefile References
- **No direct L6 references found in initial scan**
- Root pytest.ini does NOT include L6 src in pythonpath
- L6 pyproject.toml has local pythonpath configuration

### Current Facade Behavior
`value_fabric/layer6/__init__.py` appends `services/layer6-benchmarks/src` to `__path__`, making the entire `src/` a namespace package. This allows imports like `value_fabric.layer6.database` to resolve to `src/database.py`.

## 2. Proposed File Move Map

### Strategy: Move flat files into nested `layer6_benchmarks/` package

**Move Map:**

| Current Path | New Path | Notes |
|--------------|----------|-------|
| `src/__init__.py` | `src/layer6_benchmarks/__init__.py` | Package init |
| `src/config.py` | `src/layer6_benchmarks/config.py` | Flat module |
| `src/database.py` | `src/layer6_benchmarks/database.py` | Flat module |
| `src/settings.py` | `src/layer6_benchmarks/settings.py` | Flat module |
| `src/shared_bootstrap.py` | `src/layer6_benchmarks/shared_bootstrap.py` | Flat module |
| `src/adapters/` | `src/layer6_benchmarks/adapters/` | Directory |
| `src/api/` | `src/layer6_benchmarks/api/` | Directory |
| `src/metrics/` | `src/layer6_benchmarks/metrics/` | Directory |
| `src/models/` | `src/layer6_benchmarks/models/` | Directory |
| `src/observability/` | `src/layer6_benchmarks/observability/` | Directory |
| `src/repositories/` | `src/layer6_benchmarks/repositories/` | Directory |
| `src/layer6_benchmarks/logging_config.py` | `src/layer6_benchmarks/logging_config.py` | Already in correct location (no move) |

**Resulting Structure:**
```
services/layer6-benchmarks/src/
└── layer6_benchmarks/        # NESTED PACKAGE ROOT
    ├── __init__.py
    ├── config.py
    ├── database.py
    ├── settings.py
    ├── shared_bootstrap.py
    ├── logging_config.py
    ├── adapters/
    ├── api/
    ├── metrics/
    ├── models/
    ├── observability/
    └── repositories/
```

## 3. Import Rewrite Map

### Relative Imports (No Change Required)
**Files using `from .` or `from ..` will work correctly after move:**
- `from .config import Settings` → Still valid (same package)
- `from ..settings import get_layer6_settings` → Still valid (parent package)
- `from ..models.benchmark_dataset import` → Still valid (sibling package)

**Reason:** Relative imports are package-relative, not path-relative. Moving entire tree preserves relative import semantics.

### Test Imports (Change Required)
**Old facade imports → New canonical imports:**

| Old Import | New Import | Files Affected |
|-----------|-----------|----------------|
| `import value_fabric.layer6.database as database` | `import layer6_benchmarks.database as database` | conftest.py, test_database_driver.py |
| `from value_fabric.layer6.api.main import app` | `from layer6_benchmarks.api.main import app` | test_benchmark_*.py, test_metrics_contract.py |
| `from value_fabric.layer6.api.schemas import` | `from layer6_benchmarks.api.schemas import` | test_api_schemas.py, test_scope_authorization.py |
| `from value_fabric.layer6.api.deps import` | `from layer6_benchmarks.api.deps import` | test_api_tenant_propagation.py |
| `from value_fabric.layer6.models.benchmark_dataset import` | `from layer6_benchmarks.models.benchmark_dataset import` | test_models_*.py, test_repository_*.py |
| `from value_fabric.layer6.metrics.prometheus_metrics import` | `from layer6_benchmarks.metrics.prometheus_metrics import` | test_metrics_prometheus.py |
| `from value_fabric.layer6.observability.metrics_contract import` | `from layer6_benchmarks.observability.metrics_contract import` | test_observability_metrics_contract.py |
| `from value_fabric.layer6.settings import` | `from layer6_benchmarks.settings import` | test_settings_validation.py |
| `from value_fabric.layer6.api.startup_logging import` | `from layer6_benchmarks.api.startup_logging import` | test_startup_logging.py |

### Dockerfile Imports (Change Required)
**Old:** `COPY services/layer6-benchmarks/src/ ./value_fabric/layer6/`  
**New:** `COPY services/layer6-benchmarks/src/ ./value_fabric/layer6/` (no change - facade still needed temporarily)

### pyproject.toml (Change Required)
**Old:** `packages = ["src"]`  
**New:** `packages = ["src/layer6_benchmarks"]` or keep `["src"]` with proper nesting

**Old pythonpath:** `pythonpath = [".", "src", "../..", "../../packages/shared/src"]`  
**New pythonpath:** `pythonpath = [".", "src", "../..", "../../packages/shared/src"]` (no change - still needed for local development)

## 4. Compatibility Strategy

### Temporary Facade Preservation
**Keep `value_fabric.layer6` facade during transition:**

1. **Update facade shim** to re-export from canonical package:
   ```python
   # value_fabric/layer6/__init__.py
   from layer6_benchmarks import *  # Re-export everything from canonical package
   ```

2. **Add deprecation warning** to facade imports:
   ```python
   import warnings
   warnings.warn(
       "value_fabric.layer6.* imports are deprecated. Use layer6_benchmarks.* instead.",
       DeprecationWarning,
       stacklevel=2
   )
   ```

3. **CI gate** to prevent new facade usage (after test migration complete)

4. **Documentation** in facade __init__.py explaining migration path

### Phase-Out Timeline
- **Phase 1:** Restructure package, keep facade with re-exports
- **Phase 2:** Migrate all test imports to canonical
- **Phase 3:** Add deprecation warnings to facade
- **Phase 4:** Enable CI gate against new facade usage
- **Phase 5:** Remove facade after all consumers migrated

## 5. Validation Plan

### Post-Restructuring Validation

**From service directory:**
```bash
cd services/layer6-benchmarks
python -m pip install -e .
python - <<'PY'
import layer6_benchmarks.database
import layer6_benchmarks.api.main
print("layer6 canonical imports ok")
PY
```

**From repo root:**
```bash
python - <<'PY'
import sys
sys.path.insert(0, 'services/layer6-benchmarks/src')
import layer6_benchmarks.database
import layer6_benchmarks.api.main
print("root canonical imports ok")
PY
```

**Test execution:**
```bash
cd services/layer6-benchmarks
python -m pytest \
  tests/test_models_benchmark_dataset.py \
  tests/test_api_schemas.py \
  tests/test_observability_metrics_contract.py \
  tests/test_metrics_prometheus.py \
  tests/test_repository_pures.py \
  tests/test_database_driver.py \
  tests/test_startup_logging.py \
  tests/test_metrics_contract.py \
  -q
```

**Compilation check:**
```bash
python -m compileall services/layer6-benchmarks/src
```

**Inventory check:**
```bash
python scripts/ci/inventory_value_fabric_facade.py
python scripts/ci/check_value_fabric_facade_imports.py
```

**Hygiene checks:**
```bash
make check-conflict-markers
make check-no-nul-bytes
```

### Post-Test-Migration Validation

**Same validation suite** after test imports are migrated to canonical.

**Additional validation:**
- Verify no `value_fabric.layer6` imports remain in L6 tests
- Verify facade deprecation warnings appear when using facade
- Verify CI gate catches new facade usage

## 6. Risk Assessment

### High Risks

1. **Dockerfile entrypoint changes**
   - **Risk:** Docker containers may fail to start if path assumptions change
   - **Mitigation:** Keep facade temporarily, test Docker builds after restructuring
   - **Validation:** `docker build -f services/layer6-benchmarks/Dockerfile.full .`

2. **CI path assumptions**
   - **Risk:** CI jobs may fail if they depend on flat structure
   - **Mitigation:** Review CI workflows for L6-specific path assumptions
   - **Validation:** Run CI pipeline after restructuring

3. **Tests requiring both old and new paths simultaneously**
   - **Risk:** Some tests may import from both facade and canonical during transition
   - **Mitigation:** Keep facade re-exports, migrate tests atomically
   - **Validation:** Ensure no mixed imports in single test file

4. **Package installation behavior**
   - **Risk:** `pip install -e .` may fail with new structure
   - **Mitigation:** Test editable install before committing
   - **Validation:** `cd services/layer6-benchmarks && pip install -e .`

### Medium Risks

5. **K8s command/module references**
   - **Risk:** K8s manifests may reference old module paths
   - **Mitigation:** Search K8s configs for L6 references, update if found
   - **Validation:** Grep K8s/ for layer6 references

6. **OpenAPI generation paths**
   - **Risk:** OpenAPI schema generation may depend on module structure
   - **Mitigation:** Regenerate OpenAPI specs after restructuring
   - **Validation:** Check OpenAPI generation in service

7. **Docs/import examples**
   - **Risk:** Documentation may show old import patterns
   - **Mitigation:** Update docs after migration complete
   - **Validation:** Grep docs/ for value_fabric.layer6

8. **Duplicate module shadowing**
   - **Risk:** Old flat modules may shadow new nested modules during transition
   - **Mitigation:** Complete file moves in single commit, no intermediate state
   - **Validation:** Ensure no duplicate module names after move

### Low Risks

9. **MyPy type checking**
   - **Risk:** MyPy may fail with new module paths
   - **Mitigation:** Update mypy config if needed
   - **Validation:** Run mypy after restructuring

10. **Coverage reporting**
    - **Risk:** Coverage paths may need updating
    - **Mitigation:** Update coverage config if needed
    - **Validation:** Run coverage after restructuring

## 7. PR Strategy

### PR 1 — L6 Package Restructuring Plan (CURRENT)
**Scope:** This document only
**Goal:** Get approval for restructuring approach
**Risk:** None (documentation only)

### PR 2 — L6 Package Restructuring
**Scope:** File moves only, no test migration
**Changes:**
- Move flat files to nested `layer6_benchmarks/` structure
- Update pyproject.toml packages config
- Update facade shim to re-export from canonical package
- Keep all test imports unchanged (still use facade)
**Validation:** All current tests still pass via facade re-exports
**Risk:** Medium (structural change, but facade provides compatibility)

### PR 3 — L6 Test Import Migration
**Scope:** Test import migration only
**Changes:**
- Migrate all L6 test imports from `value_fabric.layer6.*` to `layer6_benchmarks.*`
- Update conftest.py imports
**Validation:** All L6 tests pass with canonical imports
**Risk:** Low (import-only changes, structure already fixed)

### PR 4 — L6 Facade Deprecation
**Scope:** Facade cleanup
**Changes:**
- Add deprecation warnings to `value_fabric.layer6` facade
- Enable CI gate against new facade usage
- Update documentation
**Validation:** No new facade usage, deprecation warnings appear
**Risk:** Low (guardrails only, no breaking changes)

### Stop Conditions

**Stop before PR 2 if:**
- Dockerfile entrypoints depend on old flat paths
- CI imports depend on old paths
- pyproject cannot install package cleanly

**Stop before PR 3 if:**
- Tests require both old and new paths simultaneously
- Canonical imports fail after restructuring

**Stop before PR 4 if:**
- Any consumers still require facade imports
- Deprecation would break external workflows

## 8. Next Steps

1. **Review this plan** with team
2. **Approve PR 1** (this document)
3. **Execute PR 2** (package restructuring)
4. **Validate PR 2** (tests still pass via facade)
5. **Execute PR 3** (test import migration)
6. **Validate PR 3** (tests pass with canonical imports)
7. **Execute PR 4** (facade deprecation)
8. **Apply pattern** to other layers if they have similar issues
