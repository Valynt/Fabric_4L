# L3 Facade Wrapper Migration Strategy

<<<<<<< HEAD
**Status:** POST-NEUTRALIZATION TRACKING - L3 service wrappers intentionally retained with removal target 2026-09-30

**Created:** 2026-05-29  
**Target removal date:** 2026-09-30

## Current Facade-Removal State

Layer 3 is now in the post-neutralization state for repository-level facade removal:

- **Layer shims are neutralized.** `value_fabric/layer3/__init__.py` no longer appends the Layer 3 service source path or acts as a runtime path redirect. It is retained only as an empty namespace placeholder with guidance to use canonical Layer 3 service modules.
- **L3 service wrappers are intentionally retained.** The remaining Layer 3 service-local wrappers and compatibility surfaces are not accidental facade drift. They are retained to preserve service startup behavior, historical bare-module imports inside `services/layer3-knowledge/src/`, and wrapper compatibility while the service continues its own migration.
- **Target removal date remains 2026-09-30.** No change to the documented wrapper-removal target is made by the facade-neutralization work.

## Problem

Layer 3 previously had 223 facade imports across runtime wrappers, tests, CI scripts, and documentation. Repository-level facade neutralization has now changed the migration problem:

- The old `value_fabric.layer3` path-bootstrap shim is no longer an active runtime bridge.
- The remaining work is not to reintroduce that shim.
- The remaining work is to track, validate, and eventually remove or replace the intentionally retained Layer 3 service-local wrapper surface.

This ticket therefore tracks the retained wrapper surface and its removal readiness, not the already-neutralized namespace placeholder.

## Scope

### In Scope

- Maintain documentation for retained Layer 3 service wrappers.
- Track wrapper drift against the 2026-09-30 removal target.
- Migrate or remove service wrappers only when Layer 3 startup, tests, and contract behavior no longer depend on them.
- Preserve explicit compatibility notes for service-local bare imports until those imports are normalized.
- Keep CI/import-topology checks aligned so new `value_fabric.layer3` runtime imports are not introduced.

### Out of Scope

- Reintroducing `value_fabric.layer3` path bootstrapping.
- Treating neutralized layer shim placeholders as canonical runtime imports.
- Moving Layer 3 runtime logic out of `services/layer3-knowledge/src/`.
- Treating intentionally retained wrappers as accidental facade drift without a validated replacement plan.

## Investigation Results

### Original L3 Facade Import Count

**Total L3 facade imports identified before neutralization:** 223
=======
**Status:** INVESTIGATION - Documented wrappers with removal target 2026-09-30

**Created:** 2026-05-29

## Problem

Layer 3 has 223 facade imports across runtime wrappers, tests, and documentation. L3 has documented service wrapper imports with a removal target of 2026-09-30. Migration requires careful classification and validation.

## Investigation Results

### L3 Facade Import Count

**Total L3 facade imports:** 223
>>>>>>> f43ab27b (```)

### Classification by File Type

Based on inventory and grep analysis:

<<<<<<< HEAD
**Runtime / Service Wrappers**

- `value_fabric/layer3/__init__.py` - now neutralized; no longer path-redirects into the service tree.
- `value_fabric/layer3/api/` - compatibility surface requiring careful review before removal.
- `value_fabric/layer3/services/` - service wrapper surface requiring owner-approved replacement/removal plan.
- `value_fabric/layer3/repositories/` - repository wrapper surface requiring owner-approved replacement/removal plan.
- `packages/shared/src/value_fabric/shared/rate_limiting/admin_api.py` - no additional L3 facade migration required. `_get_tenant_tier_from_db` already uses the service-local soft import `from db.driver import get_driver as _get_driver` inside the lookup function.

**Test Files**

- `tests/security/` - security tests using legacy patch targets.
- `tests/cache/` - cache isolation tests using legacy patch targets.
- `tests/contract/` - contract tests with skip conditions tied to Layer 3 import availability.
- `tests/ci/` - CI sentinel tests.
- `tests/arch/` - architecture contract tests.
- `tests/layer3/` - Layer 3 specific tests.

**CI Scripts**

- `scripts/ci/check_layer3_imports.py` - import-topology enforcement / error message strings.
- `scripts/ci/check_layer3_settings_shim_drift.py` - shim validation.
- Other CI scripts with Layer 3 reference strings.

**Documentation / Comments**

- `tests/README.md` - import path notes.
- `spec.md` - import topology documentation.
- Inline comments in tests and service files.

## Current Decisions

1. `value_fabric/layer3/__init__.py` remains neutralized and must not append service paths.
2. Canonical Layer 3 runtime code remains under `services/layer3-knowledge/src/`.
3. Layer 3 service wrappers remain intentional until the 2026-09-30 target unless a separate migration proves they can be removed safely earlier.
4. Wrapper cleanup must be validated through Layer 3 startup/import tests and the relevant contract/security suites.
5. New runtime imports should use service-local or canonical Layer 3 module paths, not `value_fabric.layer3`.
6. Existing test patch targets may be migrated in batches only after the equivalent canonical targets are proven stable.

## Canonical Package Target
=======
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
>>>>>>> f43ab27b (```)

**Expected canonical import:** `layer3_knowledge.*`

**Source location:** `services/layer3-knowledge/src/`

<<<<<<< HEAD
**Package name:** `layer3-knowledge`

## Package / Import Blockers

### Blocker 1: Historical Path-Redirect Shim Architecture

The previous `value_fabric.layer3` shim appended `services/layer3-knowledge/src/` to `__path__`, making the service tree reachable through the legacy namespace. That behavior has now been neutralized and must not be reintroduced.

Implication:

- Any import still relying on the old path-redirect behavior must be migrated or intentionally documented as a retained compatibility surface.
- Self-referential re-exports remain risky because they can create circular imports.

### Blocker 2: Bare Intra-Package Imports

Some service code and tests use bare imports such as:

```python
from api.dependencies import ...
```

These imports require the service `src` root to be on `sys.path` directly. The old namespace shim did not reliably propagate paths for sub-imports in pytest importlib mode.

Implication:

- Wrapper removal should not proceed until service-local bare imports are normalized or validated under the intended test/runtime import mode.
- `tests/security/conftest.py` import-path handling should remain part of the migration review.

### Blocker 3: Pre-Existing Test Blockers

Some contract/security tests historically skipped with messages such as:

```text
value_fabric.layer3 service stack not available (pre-existing blocker #1/#9)
```

Some tests also skip via the `[LAYER3_IMPORT_PATH]` marker due to logging/config conflicts.

Implication:

- These blockers should be treated as import-path and service-startup issues, not proof that wrappers are safe to remove.
- Wrapper removal requires test evidence, not only static grep cleanup.

### Blocker 4: Neo4j Driver Dependencies

Static contract tests may import Layer 3 model modules that transitively require Neo4j driver dependencies. Lightweight CI jobs may not install those dependencies.

Implication:

- Import-time dependency behavior must be accounted for before removing compatibility wrappers.
- CI jobs should distinguish between full Layer 3 validation and lightweight import-topology validation.

## 2026-05-29 Source Comment / Docstring Re-Scan

Search target: `services/layer3-knowledge/src`  
Search string: `value_fabric.layer3`

### Classified Hits

- `services/layer3-knowledge/src/services/cypher_scope_guard.py` - stale canonical-path wording; updated to point at the service-local `utils.cypher_security` implementation while preserving the wrapper note.
- `services/layer3-knowledge/src/api/app_monolith.py` - stale canonical-path wording inside intentional compatibility-wrapper documentation; updated to point at service-local `api.services.tenant_resolution.resolve_ingest_tenant_id` while preserving the 2026-09-30 wrapper target.
- `services/layer3-knowledge/src/api/routes/entity_compat.py` - stale canonical-path wording inside intentional compatibility-wrapper documentation; updated to point at service-local `api.routes.entities` while preserving the 2026-09-30 wrapper target.
- `services/layer3-knowledge/src/api/auth_context.py` - intentional compatibility-wrapper/test-path documentation; preserve until the `value_fabric.layer3` wrapper target because it documents the legacy test import path being bridged by `_get_tenant_context`.
- `services/layer3-knowledge/src/api/routes/models.py` - intentional compatibility-wrapper documentation; preserve until the `value_fabric.layer3` wrapper target because the module exists to bridge the legacy `value_fabric.layer3.api.routes.models` import path.
- `services/layer3-knowledge/src/api/main.py` - intentional compatibility-wrapper documentation; preserve until the `value_fabric.layer3` wrapper target because `__all__` is consumed by the namespace shim and tests.

No unrelated historical-context hits were found inside `services/layer3-knowledge/src` for this search string.

### Sprint-Plan Inventory Correction

Do not track `services/layer3-knowledge/src/api/routes/billing_webhook_security.py` in the L3 migration file list. The file is absent from the current Layer 3 service tree, and no relocation was found during the scan. Re-add it only if the file is restored or a concrete relocated L3 path is identified.

## Current Import Patterns

### Runtime / Service Wrappers

=======
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

### Current Import Patterns

**Runtime Wrappers (Intentional):**
>>>>>>> f43ab27b (```)
```python
# services/layer3-knowledge/src/config.py
from value_fabric.layer3.config import Settings as L3Settings

# services/layer3-knowledge/src/api/dependencies.py
from value_fabric.layer3.api.dependencies import get_graph_rag
```

<<<<<<< HEAD
These wrappers are intentional compatibility surfaces until replacement is validated.

### Test Patch Targets

```python
# tests/security/test_graph_tenant_hostile_regression.py
monkeypatch.setattr(
    "value_fabric.layer3.services.product_service.require_context",
    lambda: (_ for _ in ()).throw(RuntimeError("no context")),
)

# tests/cache/test_redis_tenant_isolation.py
with patch(
    "value_fabric.layer3.api.cache.get_redis_client",
    new=AsyncMock(return_value=mock_redis),
):
    ...
```

These should be migrated only after canonical patch targets are confirmed equivalent.

### Compatibility Shims

```python
# services/layer3-knowledge/src/api/routes/compat_aliases.py
# Delegates to query_search by relative import within the same routes package.
# Absolute value_fabric.layer3.* import would be circular.

# services/layer3-knowledge/src/api/routes/entity_compat.py
# Re-exports from the canonical entities module.
```

These shims require careful sequencing because naive replacement can introduce circular imports.

=======
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

>>>>>>> f43ab27b (```)
## Migration Strategy

### Phase 1: Classification and Documentation

<<<<<<< HEAD
**Status:** Complete

Actions completed:

- Completed detailed inventory of all 223 original L3 facade imports.
- Categorized imports into runtime wrappers, test patch targets, test imports, CI strings, documentation/comments, and compatibility shims.
- Confirmed `packages/shared/src/value_fabric/shared/rate_limiting/admin_api.py` no longer uses the deprecated `from value_fabric.layer3.db.driver import get_driver` facade import.
- Confirmed the tenant tier lookup keeps the shared-layer boundary as a soft runtime dependency by importing `from db.driver import get_driver as _get_driver` inside `_get_tenant_tier_from_db`.
- Removed the rate-limiting admin utility from the planned L3 facade replacement work; no additional migration is needed for that file.

### Phase 2: Canonical Import Verification

**Goal:** Verify whether `layer3_knowledge.*` imports work reliably in the intended execution contexts.

Validation command:
=======
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
>>>>>>> f43ab27b (```)

```bash
cd services/layer3-knowledge
python -m pip install -e .
python - <<'PY'
import layer3_knowledge
print("layer3 canonical import ok")
PY
```

<<<<<<< HEAD
Expected result:

- May fail if the package structure still mirrors the L1/L4 restructuring issue.
- If it fails, create `L3-PACKAGE-RESTRUCTURE-PLAN.md` before attempting broad migration.

Acceptance for this phase:

- `import layer3_knowledge` works from the repo root.
- `import layer3_knowledge` works from the service directory.
- Package installation succeeds without relying on `value_fabric.layer3` path bootstrapping.
- Lightweight CI behavior is documented separately from full Layer 3 service validation.

### Phase 3: Service Wrapper Replacement Plan

**Goal:** Produce an owner-approved plan for replacing or removing retained service wrappers.

Candidate files:

- `services/layer3-knowledge/src/config.py`
- `services/layer3-knowledge/src/api/dependencies.py`
- Other documented wrappers identified by the drift check.

Required validation before migration:

- Layer 3 service starts correctly.
- Imports resolve without legacy path bootstrapping.
- No circular dependencies are introduced.
- Relevant contract/security tests pass or have explicitly documented pre-existing blockers.

### Phase 4: Test Import / Patch Target Migration

**Goal:** Migrate tests from legacy `value_fabric.layer3.*` patch targets to canonical or service-local targets in controlled batches.

Recommended batches:

1. Static CI/import-topology tests.
2. Cache tests.
3. Security tests.
4. Contract tests.
5. Layer 3 service-specific tests.

Rules:

- Do not bulk-replace patch strings until the canonical target object is proven to be the object actually used at runtime.
- Prefer targeted migration with before/after assertions.
- Keep old-path compatibility tests only where the wrapper contract is still intentionally supported.

### Phase 5: Compatibility Shim Review

**Goal:** Remove or reduce compatibility shims only after canonical imports, service startup, and test patch target migration are stable.

Stop if:

- Shim restructuring creates circular imports.
- Tests require old and new targets simultaneously.
- Canonical package imports are not stable in CI.
- Service startup depends on service-local bare imports that have not been normalized.

### Phase 6: Deprecation / Enforcement

**Goal:** Ensure retained compatibility surfaces are visible, tracked, and prevented from expanding.

Possible deprecation warning for retained legacy surfaces:

=======
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
>>>>>>> f43ab27b (```)
```python
warnings.warn(
    "value_fabric.layer3 is deprecated. Use canonical imports: layer3_knowledge.*",
    DeprecationWarning,
    stacklevel=2,
)
```

<<<<<<< HEAD
Rules:

- Do not add warnings that break tests unexpectedly.
- Add warnings only where import-time behavior is stable and intentional.
- CI should prevent new runtime imports from being introduced.

## Acceptance Criteria

- [x] `value_fabric.layer3` shim is neutralized and no longer performs path redirection.
- [x] Retained L3 service wrappers are documented as intentional compatibility surfaces.
- [x] Target removal date remains documented as 2026-09-30.
- [x] Rate-limiting admin utility is removed from the planned L3 facade migration scope.
- [ ] Canonical `layer3_knowledge.*` imports are verified from repo root and service directory.
- [ ] Service wrappers have an owner-approved removal or replacement plan.
- [ ] Layer 3 startup/import tests pass without relying on wrapper behavior before final wrapper removal.
- [ ] Test patch targets are migrated in validated batches.
- [ ] Contract/security tests pass after wrapper removal or replacement.
- [ ] CI/import-topology checks prevent new `value_fabric.layer3` runtime imports.

## Validation / Monitoring

Use targeted validation before changing retained wrappers:

```bash
pytest services/layer3-knowledge/tests -q
pytest tests/contract -q
pytest tests/security -q
```

Also keep CI/import-topology checks aligned so no new `value_fabric.layer3` runtime imports are introduced.

Recommended additional checks:

```bash
python scripts/ci/check_layer3_imports.py
python scripts/ci/check_layer3_settings_shim_drift.py
=======
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
>>>>>>> f43ab27b (```)
```

## Risk Assessment

<<<<<<< HEAD
### High Risk

- Layer 3 has complex Neo4j dependency behavior.
- Historical path-redirect architecture created implicit import behavior that may still be assumed by tests.
- Bare intra-package imports require `sys.path` manipulation.
- Pre-existing test blockers may hide migration regressions.
- Compatibility shim restructuring can cause circular imports.

### Medium Risk

- 223 original imports across many files.
- Test patch targets need careful object-equivalence mapping.
- CI sentinel tests enforce shim discipline.
- Some documentation strings may intentionally mention legacy paths and should not be blindly removed.

### Low Risk

- Documented removal target exists: 2026-09-30.
- Service wrappers are intentional and documented.
- Rate-limiting admin utility has already migrated away from the deprecated L3 facade import.
- The neutralized namespace placeholder reduces risk of accidental runtime path bootstrapping.

## Stop Conditions

Stop and create a focused plan if any of the following occur:

- Canonical imports fail and package restructuring is needed.
- Service wrapper migration breaks startup.
- Tests require both old and new patch targets simultaneously.
- Compatibility shim restructuring causes circular imports.
- Pre-existing test blockers cannot be separated from migration regressions.
- Lightweight CI cannot import required modules without Neo4j or service runtime dependencies.

## Dependencies

- `L6-PACKAGE-RESTRUCTURE-PLAN.md` - completed; provides restructuring pattern if needed.
- `L1-CANONICAL-IMPORTS-PACKAGE-FIX.md` - similar issue; may need same pattern.
- `L4-PACKAGE-RESTRUCTURE-PLAN.md` - similar issue; may need same pattern.

## Next Steps

1. **Phase 2:** Verify canonical imports work from both repo root and service directory.
2. **If canonical imports fail:** create `L3-PACKAGE-RESTRUCTURE-PLAN.md`.
3. **Phase 3:** Draft the owner-approved removal/replacement plan for retained service wrappers.
4. **Phase 4:** Migrate test imports and patch targets in batches.
5. **Phase 5:** Review and reduce compatibility shims.
6. **Phase 6:** Add deprecation warnings and CI enforcement only after import behavior is stable.

## Timeline

**Target:** Complete before 2026-09-30.

Recommended sequence:

- Phase 1 Step 1: Complete on 2026-05-29.
- Phase 2: Immediate; verify canonical import behavior.
- Phase 3: After canonical imports are verified or package restructuring plan is created.
- Phase 4: After service wrapper replacement plan is approved.
- Phase 5: After test import migration is stable.
- Phase 6: After retained compatibility surfaces are narrowed and warning behavior is safe.

## Notes

- [2026-05-29] coder: Updated to reflect current facade-removal state. Layer shims are neutralized; L3 service wrappers are intentionally retained; removal target remains 2026-09-30.
=======
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
>>>>>>> f43ab27b (```)
