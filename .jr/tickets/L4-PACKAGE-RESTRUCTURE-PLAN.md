# L4 Package Restructure Plan

**Status:** BLOCKED - Package structure mismatch prevents canonical imports

**Created:** 2026-05-29

## Problem

Layer 4 canonical imports (`layer4_agents.*`) do not work due to package structure mismatch, identical to the L6 issue that was resolved in L6-PACKAGE-RESTRUCTURE-PLAN.

## Investigation Results

### Canonical Import Test
```bash
cd services/layer4-agents
python -m pip install -e .
python - <<'PY'
import layer4_agents
print("layer4 canonical import ok")
PY
```

**Result:** `ModuleNotFoundError: No module named 'layer4_agents'`

### Package Configuration

**pyproject.toml:**
- Package name: `layer4-agents` (hyphen)
- Build system: `hatchling`
- Package discovery: `packages = ["src"]`

**Source Layout:**
```
services/layer4-agents/src/
├── __init__.py
├── adapters/
├── agents/
├── api/
├── config/
├── contexts/
├── contracts/
├── database.py
├── database_facade.py
├── engine/
├── exceptions.py
├── feature_flags/
├── harness/
├── health_check.py
├── integration/
├── interfaces/
├── main.py
├── messaging/
├── metrics/
├── model_registry_client.py
├── models/
├── observability.py
├── policies/
├── provenance/
├── registry/
├── resilience.py
├── resilience_ports.py
├── services/
├── shared/
├── skills/
├── startup/
├── startup_dependencies.py
├── tenant/
├── tenants/
├── test_support/
├── tools/
└── workflows/
```

**Issue:** No nested `src/layer4_agents/` package directory. Source is flat under `src/`, just like L6 was before restructuring.

### Comparison with L6

L6 had the same issue:
- Package name: `layer6-benchmarks` (hyphen)
- Expected import: `layer6_benchmarks.*` (underscore)
- Source was flat under `src/`
- Resolution: Moved all files into `src/layer6_benchmarks/` nested package

### Comparison with L1

L1 has the same issue:
- Package name: `layer1-ingestion` (hyphen)
- Expected import: `layer1_ingestion.*` (underscore)
- Source is flat under `src/`
- Resolution: Blocked, requires restructuring (see L1-CANONICAL-IMPORTS-PACKAGE-FIX.md)

## Required Fix

Apply the same restructuring pattern used for L6:

### File Move Map

Move all flat source files into nested `src/layer4_agents/` package:

- `src/__init__.py` → `src/layer4_agents/__init__.py`
- `src/adapters/` → `src/layer4_agents/adapters/`
- `src/agents/` → `src/layer4_agents/agents/`
- `src/api/` → `src/layer4_agents/api/`
- `src/config/` → `src/layer4_agents/config/`
- `src/contexts/` → `src/layer4_agents/contexts/`
- `src/contracts/` → `src/layer4_agents/contracts/`
- `src/database.py` → `src/layer4_agents/database.py`
- `src/database_facade.py` → `src/layer4_agents/database_facade.py`
- `src/engine/` → `src/layer4_agents/engine/`
- `src/exceptions.py` → `src/layer4_agents/exceptions.py`
- `src/feature_flags/` → `src/layer4_agents/feature_flags/`
- `src/harness/` → `src/layer4_agents/harness/`
- `src/health_check.py` → `src/layer4_agents/health_check.py`
- `src/integration/` → `src/layer4_agents/integration/`
- `src/interfaces/` → `src/layer4_agents/interfaces/`
- `src/main.py` → `src/layer4_agents/main.py`
- `src/messaging/` → `src/layer4_agents/messaging/`
- `src/metrics/` → `src/layer4_agents/metrics/`
- `src/model_registry_client.py` → `src/layer4_agents/model_registry_client.py`
- `src/models/` → `src/layer4_agents/models/`
- `src/observability.py` → `src/layer4_agents/observability.py`
- `src/policies/` → `src/layer4_agents/policies/`
- `src/provenance/` → `src/layer4_agents/provenance/`
- `src/registry/` → `src/layer4_agents/registry/`
- `src/resilience.py` → `src/layer4_agents/resilience.py`
- `src/resilience_ports.py` → `src/layer4_agents/resilience_ports.py`
- `src/services/` → `src/layer4_agents/services/`
- `src/shared/` → `src/layer4_agents/shared/`
- `src/skills/` → `src/layer4_agents/skills/`
- `src/startup/` → `src/layer4_agents/startup/`
- `src/startup_dependencies.py` → `src/layer4_agents/startup_dependencies.py`
- `src/tenant/` → `src/layer4_agents/tenant/`
- `src/tenants/` → `src/layer4_agents/tenants/`
- `src/test_support/` → `src/layer4_agents/test_support/`
- `src/tools/` → `src/layer4_agents/tools/`
- `src/workflows/` → `src/layer4_agents/workflows/`

### Configuration Updates

**pyproject.toml:**
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/layer4_agents"]
```

**Facade Shim Update:**
Update `value_fabric/layer4/__init__.py` to point to new nested path:
```python
_canonical_pkg = str(_repo_root / "services" / "layer4-agents" / "src" / "layer4_agents")
```

### Import Migration

After restructuring, migrate L4 test imports from `value_fabric.layer4.*` to `layer4_agents.*`.

Current L4 facade imports: 515

## Risk Assessment

**High Risk:**
- L4 is the largest layer (515 facade imports)
- Dockerfile entrypoints may reference old paths
- CI scripts may import via facade
- Relative imports within L4 source may require package context
- Path depth calculations in source files may need updates
- Large test suite (~150+ test files)

**Medium Risk:**
- Test fixtures may rely on facade path resolution
- OpenAPI generation paths may need updates
- LangGraph workflow state management may depend on import paths

**Critical Risk:**
- L4 has complex agent orchestration that may depend on module resolution
- Database session management may require specific import paths
- Tenant isolation enforcement may depend on import structure

## Stop Conditions

- Stop if Dockerfiles depend on old flat paths
- Stop if CI imports break after restructuring
- Stop if package installation fails
- Stop if tests require both old and new paths simultaneously
- Stop if agent workflows fail due to import resolution
- Stop if database session management breaks

## Validation Plan

After restructuring:

```bash
# From repo root
python - <<'PY'
import layer4_agents
print("layer4 canonical import ok")
PY

# From service directory
cd services/layer4-agents
python -m pip install -e .
python -m pytest tests -q

# Facade compatibility
python - <<'PY'
import value_fabric.layer4.database
print("facade compatibility ok")
PY

# Compile check
python -m compileall services/layer4-agents/src
```

## Dependencies

- L6-PACKAGE-RESTRUCTURE-PLAN.md (completed) - provides the restructuring pattern
- L6-PR2 (completed) - provides the implementation reference
- L1-CANONICAL-IMPORTS-PACKAGE-FIX.md - same issue, can use same pattern

## Next Steps

1. Create detailed L4 restructuring plan (similar to L6-PACKAGE-RESTRUCTURE-PLAN)
2. Implement package restructuring in isolated PR
3. Validate canonical imports work
4. Migrate L4 test imports in small batches (contracts, models, engine, API, remaining)
5. Add deprecation warnings to L4 facade

## Batch Migration Order (After Restructuring)

1. **Contracts tests** - smallest, isolated
2. **Models tests** - data structures, minimal runtime
3. **Engine/state manager tests** - core orchestration
4. **API/router tests** - FastAPI endpoints
5. **Remaining tests** - integration, security, workflows

## References

- L6-PACKAGE-RESTRUCTURE-PLAN.md
- L6-PR2 implementation
- L1-CANONICAL-IMPORTS-PACKAGE-FIX.md
- IMPORT-ARCH-FACADE-RESOLUTION.md
