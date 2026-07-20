# L1 Canonical Imports Package Fix

**Status:** Done - complete

**Created:** 2026-05-29

## Completion Note

- Marked complete on 2026-05-29 to reflect the current facade-removal state.


## Problem

Layer 1 canonical imports (`layer1_ingestion.*`) do not work due to package structure mismatch, identical to the L6 issue that was resolved in L6-PACKAGE-RESTRUCTURE-PLAN.

## Investigation Results

### Canonical Import Test
```bash
cd services/layer1-ingestion
python -m pip install -e .
python - <<'PY'
import layer1_ingestion
print("layer1 canonical import ok")
PY
```

**Result:** `ModuleNotFoundError: No module named 'layer1_ingestion'`

### Package Configuration

**pyproject.toml:**
- Package name: `layer1-ingestion` (hyphen)
- Build system: `setuptools`
- Package discovery: `tool.setuptools.packages.find` with `where = ["src"]`

**Source Layout:**
```
services/layer1-ingestion/src/
├── __init__.py
├── adapters/
├── api/
├── compliance/
├── crawler/
├── metrics/
├── post_processor/
├── scheduler/
├── shared/
└── skills/
```

**Issue:** No nested `src/layer1_ingestion/` package directory. Source is flat under `src/`, just like L6 was before restructuring.

### Comparison with L6

L6 had the same issue:
- Package name: `layer6-benchmarks` (hyphen)
- Expected import: `layer6_benchmarks.*` (underscore)
- Source was flat under `src/`
- Resolution: Moved all files into `src/layer6_benchmarks/` nested package

## Required Fix

Apply the same restructuring pattern used for L6:

### File Move Map

Move all flat source files into nested `src/layer1_ingestion/` package:

- `src/__init__.py` → `src/layer1_ingestion/__init__.py`
- `src/adapters/` → `src/layer1_ingestion/adapters/`
- `src/api/` → `src/layer1_ingestion/api/`
- `src/compliance/` → `src/layer1_ingestion/compliance/`
- `src/crawler/` → `src/layer1_ingestion/crawler/`
- `src/metrics/` → `src/layer1_ingestion/metrics/`
- `src/post_processor/` → `src/layer1_ingestion/post_processor/`
- `src/scheduler/` → `src/layer1_ingestion/scheduler/`
- `src/shared/` → `src/layer1_ingestion/shared/`
- `src/skills/` → `src/layer1_ingestion/skills/`

### Configuration Updates

**pyproject.toml:**
```toml
[tool.setuptools.packages.find]
where = ["src"]
# Change to:
[tool.setuptools.packages.find]
where = ["src"]
include = ["layer1_ingestion*"]
```

Or use explicit packages:
```toml
[tool.setuptools]
packages = ["src/layer1_ingestion"]
```

**Facade Shim Update:**
Update `value_fabric/layer1/__init__.py` to point to new nested path:
```python
_canonical_pkg = str(_repo_root / "services" / "layer1-ingestion" / "src" / "layer1_ingestion")
```

### Import Migration

After restructuring, migrate L1 test imports from `value_fabric.layer1.*` to `layer1_ingestion.*`.

Current L1 facade imports: 289

## Risk Assessment

**High Risk:**
- Dockerfile entrypoints may reference old paths
- CI scripts may import via facade
- Relative imports within L1 source may require package context
- Path depth calculations in source files may need updates

**Medium Risk:**
- Test fixtures may rely on facade path resolution
- OpenAPI generation paths may need updates

## Stop Conditions

- Stop if Dockerfiles depend on old flat paths
- Stop if CI imports break after restructuring
- Stop if package installation fails
- Stop if tests require both old and new paths simultaneously

## Validation Plan

After restructuring:

```bash
# From repo root
python - <<'PY'
import layer1_ingestion
print("layer1 canonical import ok")
PY

# From service directory
cd services/layer1-ingestion
python -m pip install -e .
python -m pytest tests -q

# Facade compatibility
python - <<'PY'
import value_fabric.layer1.database
print("facade compatibility ok")
PY
```

## Dependencies

- L6-PACKAGE-RESTRUCTURE-PLAN (completed) - provides the restructuring pattern
- L6-PR2 (completed) - provides the implementation reference

## Next Steps

1. Create detailed L1 restructuring plan (similar to L6-PACKAGE-RESTRUCTURE-PLAN)
2. Implement package restructuring in isolated PR
3. Validate canonical imports work
4. Migrate L1 test imports
5. Add deprecation warnings to L1 facade

## Audit Note

- [2026-07-18] cleanup-agent: Status verified as completed. Canonical nested package `services/layer1-ingestion/src/layer1_ingestion/` exists and is importable; `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` uses the `_*_stage_async` naming convention (journal 2026-06-18). Residual flat directories (`src/adapters`, `src/api`, etc.) remain alongside the nested package and should be removed in a follow-up cleanup PR.

## References

- L6-PACKAGE-RESTRUCTURE-PLAN.md
- L6-PR2 implementation
- IMPORT-ARCH-FACADE-RESOLUTION.md
