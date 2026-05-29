# IMPORT-ARCH-FACADE-RESOLUTION — Replace value_fabric facade path bootstrapping

**Status:** Investigation in progress  
**Created:** 2026-05-28  
**Priority:** HIGH  
**Blocks:** All value_fabric.layer* import migration, facade removal

## Problem Statement

The `value_fabric/` facade provides critical Python path resolution by appending service source paths to package `__path__`. Direct canonical imports (e.g., `layer6_benchmarks.database`) fail without this path bootstrapping, preventing facade removal.

## Investigation Findings

### 1. Facade Path Bootstrapping Mechanism

**Root facade** (`value_fabric/__init__.py`):
- Appends `packages/shared/src/value_fabric` to `__path__` with priority
- Enables `value_fabric.shared.*` imports without sys.path mutation
- Does NOT append layer service paths (delegated to layer shims per ADR-027)

**Layer shims** (`value_fabric/layerX/__init__.py`):
- **L1:** Appends `services/layer1-ingestion/src` to `__path__`
- **L3:** Appends `services/layer3-knowledge/src` to `__path__`
- **L4:** Appends `services/layer4-agents/src` to `__path__`
- **L6:** Appends `services/layer6-benchmarks/src` to `__path__`

Each shim fails fast if canonical path doesn't exist.

### 2. Service Package Layout

**Canonical package structures:**

| Layer | Service Source Path | Package Name | Egg-Info Present | Structure |
|-------|-------------------|--------------|------------------|-----------|
| L1 | `services/layer1-ingestion/src` | `layer1_ingestion` | Yes | Nested |
| L3 | `services/layer3-knowledge/src` | `layer3_knowledge` | Yes | Nested |
| L4 | `services/layer4-agents/src` | (flat structure) | No | Flat |
| L6 | `services/layer6-benchmarks/src` | `layer6_benchmarks` | No | **Flat (mismatch)** |

**L6 CRITICAL FINDING - Package Structure Mismatch:**
- pyproject.toml declares package name: `layer6-benchmarks`
- pyproject.toml: `[tool.hatch.build.targets.wheel] packages = ["src"]`
- **Actual structure:** Flat at `services/layer6-benchmarks/src/` (database.py, api/main.py, etc.)
- **Expected structure:** Nested at `services/layer6-benchmarks/src/layer6_benchmarks/`
- **Files use relative imports:** `from .config import Settings` in database.py
- **Result:** Cannot import as `layer6_benchmarks.database` because package structure doesn't exist
- **Facade workaround:** Appends entire `src/` to `__path__`, making it a namespace package

**PYTHONPATH fix attempt FAILED:**
- Added `services/layer6-benchmarks/src` to root pytest.ini pythonpath
- Direct import `import database` fails with `ImportError: attempted relative import with no known parent package`
- This confirms the flat structure with relative imports requires package context

### 3. Test Runner Path Configuration

**Root pytest.ini pythonpath:**
```
pythonpath = . services/layer3-knowledge/src packages/shared/src services/layer5-ground-truth/src services/api services/layer4-agents/src
```

**NOTABLE OMISSIONS:**
- `services/layer1-ingestion/src` - NOT in root pythonpath
- `services/layer6-benchmarks/src` - NOT in root pythonpath
- `services/layer2-extraction/src` - NOT in root pythonpath

**L6 pyproject.toml:**
- Has local pytest config but no explicit pythonpath override
- Package structure suggests `src/` is the package root

### 4. Import Resolution Failure

**Attempted canonical import:**
```python
import layer6_benchmarks.database
```

**Error:** `ModuleNotFoundError: No module named 'layer6_benchmarks.database'`

**Root cause:** 
- Facade appends `services/layer6-benchmarks/src` to `__path__`
- But canonical package is actually at `services/layer6-benchmarks/src/layer6_benchmarks/`
- Without facade, Python can't find the nested package structure

## Canonical Fix Options

### Option A: Install packages in editable mode
```bash
pip install -e services/layer1-ingestion
pip install -e services/layer3-knowledge
pip install -e services/layer4-agents
pip install -e services/layer6-benchmarks
```
**Pros:** Standard Python packaging, imports work globally
**Cons:** Requires pip install for development, changes global Python environment

### Option B: Explicit PYTHONPATH per service
Add to each service's pytest.ini/pyproject.toml:
```ini
[tool.pytest.ini_options]
pythonpath = ["src"]
```
**Pros:** Local to each service, no global changes
**Cons:** Requires updating each service's config, may conflict with root pytest.ini

### Option C: Normalize package structure (REQUIRED for L6)
Restructure L6 to match pyproject.toml package declaration:
- Move flat files from `services/layer6-benchmarks/src/` to `services/layer6-benchmarks/src/layer6_benchmarks/`
- Update pyproject.toml: `packages = ["src/layer6_benchmarks"]` or keep `["src"]` with proper nesting
**Pros:** Matches package declaration, enables canonical imports
**Cons:** Major restructuring for L6, high risk, may affect other layers

### Option D: Minimal facade with deprecation
Keep facade as path resolver only:
- Add deprecation warnings to all facade imports
- Add CI gate preventing new facade usage
- Document as temporary compatibility layer
**Pros:** Low risk, gradual migration
**Cons:** Facade remains, doesn't fully solve problem

## Recommended Approach

**Short-term (immediate):**
1. **Option D** - Keep minimal facade with deprecation warnings
2. **PYTHONPATH fix FAILED** - Cannot work with L6 flat structure + relative imports
3. **Option C REQUIRED** - L6 package structure must be normalized to match pyproject.toml

**Medium-term:**
1. **Option C** - Restructure L6 to have proper nested package structure
2. Update all L6 imports to use canonical `layer6_benchmarks.*` after restructuring
3. Validate canonical imports work without facade
4. Apply same pattern to other layers if needed

**Long-term:**
1. **Option A** - Move to editable package installs for development
2. Remove facade entirely once all imports are canonical and packages are properly installed

## Next Steps

1. **L6-CANONICAL-IMPORTS-PYTHONPATH** - Add L6 src to root pytest.ini and validate
2. Test canonical imports from repo root and service directory
3. Add deprecation warnings to facade shims
4. Create service package installation script for development
5. Migrate L6 test imports once canonical imports work

## Validation Target

From repo root and from `services/layer6-benchmarks`, this should work without importing `value_fabric.layer6`:

```bash
python - <<'PY'
import layer6_benchmarks.database
import layer6_benchmarks.api.main
print("layer6 canonical imports ok")
PY
```

## Related Tickets

- `L6-PACKAGE-RESTRUCTURE` - Restructure L6 to match pyproject.toml package declaration
- `FACADE-DEPRECATION-GATE` - Add deprecation warnings and enforcement
