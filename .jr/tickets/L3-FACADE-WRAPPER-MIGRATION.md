# L3 Facade Wrapper Migration Strategy

**Status:** INVESTIGATION - Documented wrappers with removal target 2026-09-30

**Created:** 2026-05-29

## Problem

Layer 3 has 223 facade imports across runtime wrappers, tests, and documentation. L3 has documented service wrapper imports with a removal target of 2026-09-30. Migration requires careful classification and validation.

## Investigation Results

### L3 Facade Import Count

**Total L3 facade imports:** 223

### Classification by File Type

Based on inventory and grep analysis:

**Runtime/Service Wrappers (17 files):**
- `value_fabric/layer3/__init__.py` - Path-redirect shim
- `value_fabric/layer3/api/` - Compatibility shims
- `value_fabric/layer3/services/` - Service wrappers
- `value_fabric/layer3/repositories/` - Repository wrappers
- `packages/shared/src/value_fabric/shared/rate_limiting/admin_api.py` - Runtime dependency

**Test Files (150+):**
- `tests/security/` - Security tests using patch targets
- `tests/cache/` - Cache isolation tests
- `tests/contract/` - Contract tests with skip conditions
- `tests/ci/` - CI sentinel tests
- `tests/arch/` - Architecture contract tests
- `tests/layer3/` - Layer 3 specific tests

**CI Scripts (9):**
- `scripts/ci/check_layer3_imports.py` - Error message string
- `scripts/ci/check_layer3_settings_shim_drift.py` - Shim validation
- Other CI scripts with reference strings

**Documentation/Comments:**
- `tests/README.md` - Import path notes
- `spec.md` - Import topology documentation
- Inline comments in test files

### Documented Owner/Removal Target

From source code analysis:

**Service Wrappers (Intentional until 2026-09-30):**
- `services/layer3-knowledge/src/config.py` - Documented as "Allowed service-local exception for Layer 3 service wrapper" with "Removal/migration target: 2026-09-30"
- `services/layer3-knowledge/src/api/dependencies.py` - Similar documentation header

**Path-Redirect Shim:**
- `value_fabric/layer3/__init__.py` - Documented as path-redirect shim appending `services/layer3-knowledge/src/` to `__path__`

### Canonical Package Target

**Expected canonical import:** `layer3_knowledge.*`

**Source location:** `services/layer3-knowledge/src/`

**Package name:** `layer3-knowledge` (from service directory)

### Package/Import Blockers

**Blocker 1: Path-Redirect Shim Architecture**
- The `value_fabric.layer3` shim appends `services/layer3-knowledge/src/` to `__path__`
- This makes the service tree the canonical source
- Canonical source is `services/layer3-knowledge/src/api/models.py` (not under `value_fabric/layer3/`)
- Cannot use self-referential re-exports (would be circular)

**Blocker 2: Bare Intra-Package Imports**
- Tests use bare imports like `from api.dependencies import ...`
- These require the src root to be on `sys.path` directly
- The shim doesn't propagate path for sub-imports in pytest importlib mode
- Documented in `tests/security/conftest.py`

**Blocker 3: Pre-existing Test Blockers**
- Contract tests skip with "value_fabric.layer3 service stack not available (pre-existing blocker #1/#9)"
- Some tests skip via `[LAYER3_IMPORT_PATH]` marker due to logging_config conflicts
- These are not due to missing services but import path issues

**Blocker 4: Neo4j Driver Dependencies**
- Static contract tests import Layer 3 model modules which transitively import `value_fabric.layer3`
- Lightweight CI jobs avoid installing driver dependencies
- Requires shim for import-time type references


### 2026-05-29 Source Comment/Docstring Re-scan

Search target: `services/layer3-knowledge/src`
Search string: `value_fabric.layer3`

**Classified hits:**

- `services/layer3-knowledge/src/services/cypher_scope_guard.py` — stale canonical-path wording; updated to point at the service-local `utils.cypher_security` implementation while preserving the wrapper note.
- `services/layer3-knowledge/src/api/app_monolith.py` — stale canonical-path wording inside intentional compatibility-wrapper documentation; updated to point at service-local `api.services.tenant_resolution.resolve_ingest_tenant_id` while preserving the 2026-09-30 wrapper target.
- `services/layer3-knowledge/src/api/routes/entity_compat.py` — stale canonical-path wording inside intentional compatibility-wrapper documentation; updated to point at service-local `api.routes.entities` while preserving the 2026-09-30 wrapper target.
- `services/layer3-knowledge/src/api/auth_context.py` — intentional compatibility-wrapper/test-path documentation; preserve until the `value_fabric.layer3` wrapper target because it documents the legacy test import path being bridged by `_get_tenant_context`.
- `services/layer3-knowledge/src/api/routes/models.py` — intentional compatibility-wrapper documentation; preserve until the `value_fabric.layer3` wrapper target because the module exists to bridge the legacy `value_fabric.layer3.api.routes.models` import path.
- `services/layer3-knowledge/src/api/main.py` — intentional compatibility-wrapper documentation; preserve until the `value_fabric.layer3` wrapper target because `__all__` is consumed by the namespace shim and tests.

No unrelated historical-context hits were found inside `services/layer3-knowledge/src` for this search string.

**Sprint-plan inventory correction:**

- Do not track `services/layer3-knowledge/src/api/routes/billing_webhook_security.py` in the L3 migration file list: the file is absent from the current Layer 3 service tree and no relocation was found during this scan. Re-add it only if the file is restored or a concrete relocated L3 path is identified.

### Current Import Patterns

**Runtime Wrappers (Intentional):**
```python
# services/layer3-knowledge/src/config.py
from value_fabric.layer3.config import Settings as L3Settings

# services/layer3-knowledge/src/api/dependencies.py
from value_fabric.layer3.api.dependencies import get_graph_rag
```

**Test Patch Targets:**
```python
# tests/security/test_graph_tenant_hostile_regression.py
monkeypatch.setattr(
    'value_fabric.layer3.services.product_service.require_context',
    lambda: (_ for _ in ()).throw(RuntimeError('no context')),
)

# tests/cache/test_redis_tenant_isolation.py
with patch("value_fabric.layer3.api.cache.get_redis_client", new=AsyncMock(return_value=mock_redis)):
```

**Compatibility Shims:**
```python
# services/layer3-knowledge/src/api/routes/compat_aliases.py
# Delegates to query_search (relative import within same routes package)
# Absolute value_fabric.layer3.* import would be circular

# services/layer3-knowledge/src/api/routes/entity_compat.py
# Must re-export from canonical entities module
```

## Migration Strategy

### Phase 1: Classification and Documentation

**Action:** Create detailed inventory of all 223 L3 facade imports

**Categories:**
1. **Runtime service wrappers** (intentional, documented, removal target 2026-09-30)
2. **Test patch targets** (need canonical import mapping)
3. **Test imports** (need canonical import migration)
4. **CI script strings** (update to canonical names)
5. **Documentation/comments** (update to canonical names)
6. **Compatibility shims** (may need restructuring)

### Phase 2: Canonical Import Verification

**Action:** Verify `layer3_knowledge.*` imports work

```bash
cd services/layer3-knowledge
python -m pip install -e .
python - <<'PY'
import layer3_knowledge
print("layer3 canonical import ok")
PY
```

**Expected Result:** May fail due to package structure (similar to L1/L4)

**If Fails:** Create L3-PACKAGE-RESTRUCTURE-PLAN

### Phase 3: Service Wrapper Migration

**Scope:** Migrate documented service wrappers from `value_fabric.layer3.*` to `layer3_knowledge.*`

**Files:**
- `services/layer3-knowledge/src/config.py`
- `services/layer3-knowledge/src/api/dependencies.py`
- Any other documented wrappers

**Validation:**
- Service starts correctly
- Imports resolve
- No circular dependencies

### Phase 4: Test Import Migration

**Scope:** Migrate test imports from `value_fabric.layer3.*` to `layer3_knowledge.*`

**Batch Order:**
1. **CI sentinel tests** - Architecture contract tests
2. **Security tests** - Tenant isolation tests
3. **Cache tests** - Redis isolation tests
4. **Contract tests** - API contract tests
5. **Layer 3 tests** - Service-specific tests

**Special Handling:**
- Patch targets need canonical import mapping
- Bare intra-package imports may need `sys.path` manipulation
- Tests with pre-existing blockers need investigation

### Phase 5: Compatibility Shim Restructuring

**Scope:** Restructure compatibility shims to avoid circular imports

**Files:**
- `services/layer3-knowledge/src/api/routes/compat_aliases.py`
- `services/layer3-knowledge/src/api/routes/entity_compat.py`

**Strategy:**
- Use relative imports within service tree
- Avoid absolute `value_fabric.layer3.*` imports
- Maintain API compatibility

### Phase 6: Facade Deprecation

**Action:** Add deprecation warnings to `value_fabric/layer3/__init__.py`

**Warning Message:**
```python
warnings.warn(
    "value_fabric.layer3 is deprecated. Use canonical imports: layer3_knowledge.*",
    DeprecationWarning,
    stacklevel=2,
)
```

## Validation Plan

### Per-Phase Validation

**Phase 1 (Classification):**
- Inventory complete
- All imports categorized
- Blockers documented

**Phase 2 (Canonical Import Verification):**
- `import layer3_knowledge` works from repo root
- `import layer3_knowledge` works from service directory
- Package install successful

**Phase 3 (Service Wrapper Migration):**
- Service starts: `python -m layer3_knowledge.api.main`
- Imports resolve without errors
- No circular dependencies

**Phase 4 (Test Import Migration):**
- `python -m pytest tests/layer3/ -q`
- `python -m pytest tests/security/ -k layer3 -q`
- `python -m pytest tests/cache/ -q`
- `python -m pytest tests/contract/ -k layer3 -q`

**Phase 5 (Compatibility Shim Restructuring):**
- `python -m compileall services/layer3-knowledge/src`
- Import tests pass
- No circular import errors

**Phase 6 (Facade Deprecation):**
- Facade warns on import
- Canonical imports work without warnings
- Tests still pass

### Final Validation

```bash
python scripts/ci/inventory_value_fabric_facade.py
python scripts/ci/check_value_fabric_facade_imports.py
make check-conflict-markers
make check-no-nul-bytes
git diff --check
```

## Risk Assessment

**High Risk:**
- L3 has complex Neo4j dependency
- Path-redirect shim architecture is critical
- Bare intra-package imports require sys.path manipulation
- Pre-existing test blockers (#1/#9)
- Compatibility shims may cause circular imports

**Medium Risk:**
- 223 imports across many files
- Test patch targets need careful mapping
- CI sentinel tests enforce shim discipline

**Low Risk:**
- Documented removal target (2026-09-30)
- Service wrappers are intentional and documented
- Canonical package structure may already work

## Stop Conditions

- Stop if canonical imports fail and package restructuring is needed
- Stop if service wrapper migration breaks startup
- Stop if test migration requires both old and new paths simultaneously
- Stop if compatibility shim restructuring causes circular imports
- Stop if pre-existing test blockers cannot be resolved

## Dependencies

- L6-PACKAGE-RESTRUCTURE-PLAN.md (completed) - provides restructuring pattern if needed
- L1-CANONICAL-IMPORTS-PACKAGE-FIX.md - similar issue, may need same pattern
- L4-PACKAGE-RESTRUCTURE-PLAN.md - similar issue, may need same pattern

## Next Steps

1. **Phase 1:** Complete detailed inventory of all 223 L3 facade imports
2. **Phase 2:** Verify canonical imports work (may require package restructuring)
3. **Phase 3:** Migrate documented service wrappers
4. **Phase 4:** Migrate test imports in batches
5. **Phase 5:** Restructure compatibility shims
6. **Phase 6:** Add deprecation warnings to facade

## Timeline

**Target:** Complete before 2026-09-30 (documented removal target)

**Recommended:**
- Phase 1-2: Immediate (investigation)
- Phase 3: After canonical imports verified
- Phase 4: After service wrappers migrated
- Phase 5-6: After test imports migrated

## References

- `services/layer3-knowledge/src/config.py` - Documented service wrapper
- `services/layer3-knowledge/src/api/dependencies.py` - Documented service wrapper
- `tests/security/conftest.py` - Path manipulation documentation
- `tests/README.md` - Import path notes
- `spec.md` - Import topology documentation
- L6-PACKAGE-RESTRUCTURE-PLAN.md
- IMPORT-ARCH-FACADE-RESOLUTION.md
