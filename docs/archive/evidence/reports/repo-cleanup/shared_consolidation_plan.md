# Shared Package Consolidation Plan

**Date:** 2026-05-02
**Status:** Completed 2026-05-13 — root `value_fabric/shared/` removed
**Target:** `packages/shared/src/value_fabric/shared/`

---

## Executive Summary

The repository currently has two `shared/` packages that shadow each other at runtime:
- `shared/` (root) — 57 tracked files, 11 modules
- `packages/shared/src/value_fabric/shared/` — 72 tracked files, 14 modules

Pytest collection is **already broken** due to this shadowing:
```
ModuleNotFoundError: No module named 'shared.error_handling'
```

`shared.error_handling` exists only in `packages/shared/src/value_fabric/shared/`, but `import shared` resolves to root `shared/` in some contexts.

All 500+ imports use the bare `from shared.X` pattern; none use `from value_fabric.shared.X`.

---

## Inventory

### Root-only Modules (not in packages/shared/src/value_fabric/shared/)

| Module | Files | Import Refs | Notes |
|--------|-------|-------------|-------|
| `crypto` | 2 | 12 | Canonical crypto utilities |
| `governance` | 7 | 3 | Gate/policy engine |
| `llm_safety` | 7 | 0 | LLM guardrails |
| `observability` | 3 | 1 | Metrics access |
| `rate_limiting` | 4 | 2 | Tenant rate limiter |
| `tracing` | 2 | 0 | Config only (non-Python) |

### packages/shared/src/value_fabric/shared/-only Modules (not in root shared/)

| Module | Files | Import Refs | Notes |
|--------|-------|-------------|-------|
| `boundaries` | 2 | 1 | Tenant boundary enforcement |
| `error_handling` | 7 | 8 | Structured error handling + middleware |
| `mcp_gateway` | 19 | 12 | MCP gateway + tests |
| `testability` | 6 | 4 | Test clocks, ID generators |

### Overlapping Modules

| Module | Root Files | VF Files | Overlap Status |
|--------|-----------|----------|----------------|
| `audit` | 4 | 5 | `__init__.py` DIFF, `emitter.py` DIFF, `models.py` DIFF, `ledger.py` ROOT_ONLY, tests VF_ONLY |
| `identity` | 20 | 18 | Most files DIFF; root has `api_key_cache.py`, `dev_bypass.py`, `governance_core.py`, `session_cache.py`, `tool_contract.py`; VF has `isolation.py`, `rate_limiting.py`, tests |
| `models` | 1 | 2 | `typed_dict.py` DIFF; VF has `__init__.py` |
| `secrets` | 3 | 6 | Completely different modules |
| `security` | 3 | 3 | `middleware.py` DIFF (root=non-auth, VF=auth); root has `config.py`, VF has `dil_auth.py` |

---

## Import Reference Summary

| Module | `from shared.X` refs | `from value_fabric.shared.X` refs | Total |
|--------|---------------------|-----------------------------------|-------|
| `models` | 332 | 0 | 332 |
| `identity` | 112 | 0 | 112 |
| `audit` | 40 | 0 | 40 |
| `security` | 28 | 0 | 28 |
| `mcp_gateway` | 12 | 0 | 12 |
| `crypto` | 12 | 0 | 12 |
| `secrets` | 8 | 0 | 8 |
| `error_handling` | 8 | 0 | 8 |
| `testability` | 4 | 0 | 4 |
| `governance` | 3 | 0 | 3 |
| `rate_limiting` | 2 | 0 | 2 |
| `observability` | 1 | 0 | 1 |
| `boundaries` | 1 | 0 | 1 |
| `tracing` | 0 | 0 | 0 |
| `llm_safety` | 0 | 0 | 0 |

**Grand total: 568 import references across the codebase.**

---

## Merge Strategy

### Principle
Take the **union** of all files from both locations. For files that exist in both but differ, merge them to preserve the **superset of exported APIs**. This ensures zero breakage of existing callers during the migration.

### Module-by-Module Decisions

#### audit
- **Base:** packages/shared/src/value_fabric/shared/audit/ (has tests)
- **Merge in:** `shared/audit/ledger.py` (root-only, imported)
- **Merge `__init__.py`:** Export symbols from both versions (`AuditAction`, `AuditOutcome`, `AuditEvent`, `AuditEmitter`, `emit_audit_event`, `TenantResolvedDetails`, `TenantContextSetDetails`)
- **Merge `emitter.py`:** Combine implementations preserving all public functions
- **Merge `models.py`:** Combine model definitions

#### identity
- **Base:** packages/shared/src/value_fabric/shared/identity/ (comprehensive, has tests)
- **Merge in:** `api_key_cache.py`, `dev_bypass.py`, `governance_core.py`, `session_cache.py`, `tool_contract.py` (root-only)
- **Merge `__init__.py`:** Export superset of both versions
- **Individual file merges:** Most files are DIFF; prefer VF version where it is a clear superset. For files with unique root-only exports, ensure they remain importable.

#### models
- **Base:** packages/shared/src/value_fabric/shared/models/ (has `__init__.py`)
- **Merge `typed_dict.py`:** Combine both implementations:
  - Use `extra="allow"` (root) — callers may rely on permissive behavior
  - Add `__len__`, `KeyError` handling (VF)
  - Keep `keys()`, `values()`, `items()`, `__setitem__` (root)
  - Keep `__iter__` over `model_fields` (VF)
  - Keep `arbitrary_types_allowed=True` (root)

#### secrets
- **Union:** Both directories have completely different files
- Copy all files from both locations

#### security
- **Base:** packages/shared/src/value_fabric/shared/security/ (authoritative per inline comments)
- **Merge in:** `shared/security/config.py` (root-only)
- **Keep:** `dil_auth.py` (VF-only)
- **Use VF `middleware.py`** (516-line authoritative version)

#### crypto, governance, llm_safety, observability, rate_limiting, tracing
- **Copy as-is** from root shared/

#### boundaries, error_handling, mcp_gateway, testability
- **Copy as-is** from packages/shared/src/value_fabric/shared/

---

## Execution Steps

### Step 1: Create Target Structure
```
packages/shared/
  src/
    value_fabric/
      shared/
        __init__.py
        audit/
        boundaries/
        crypto/
        error_handling/
        governance/
        identity/
        llm_safety/
        models/
        mcp_gateway/
        observability/
        rate_limiting/
        secrets/
        security/
        testability/
        tracing/
```

### Step 2: File Copy & Merge
- Copy all files from both source directories into target
- For DIFF files, write merged versions
- For SAME files, copy either version

### Step 3: Import Updates (Batch)
- Replace `from shared.X` → `from value_fabric.shared.X` across all `.py` files
- Replace `import shared.X` → `from value_fabric.shared import X` (if any)
- Update imports **within** the shared package to use relative imports where appropriate

### Step 4: Update value_fabric Shim
- Modify `value_fabric/__init__.py` to add `packages/shared/src` to `sys.path`
- Ensure `value_fabric.shared` resolves correctly

### Step 5: Validation
- `python -c "import value_fabric.shared; print(value_fabric.shared.__file__)"`
- `python -c "import shared"` → should fail or not resolve to repo root
- `pytest --collect-only -q`
- `python scripts/ci/structural_preflight.py --strict`

### Step 6: Remove Old Packages (after stability)
- `git rm -r shared/`
- `git rm -r packages/shared/src/value_fabric/shared/`
- Remove NTFS junction `value_fabric/shared`

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Merged file breaks callers | Preserve superset of APIs; run pytest collection after each module merge |
| Import updates miss files | Use regex-based bulk replacement; verify with grep |
| Tests fail due to path changes | Run `pytest --collect-only` before and after; fix conftest.py paths |
| value_fabric shim breaks | Keep shim functional until final cleanup; update incrementally |
| Circular imports | Use relative imports within shared package; avoid `from value_fabric.shared import X` inside shared |

---

## Validation Criteria

- [ ] `python -c "import value_fabric.shared; print(value_fabric.shared.__file__)"` resolves to `packages/shared/src/value_fabric/shared/`
- [ ] `python -c "import shared"` does NOT resolve to repo root `shared/`
- [ ] `pytest --collect-only -q` shows zero import errors (baseline: 2 errors)
- [ ] `python scripts/ci/structural_preflight.py --strict` passes
- [ ] All 568 `from shared.X` imports are replaced with `from value_fabric.shared.X`
- [ ] Zero tracked files remain in `shared/` (root) or `packages/shared/src/value_fabric/shared/`
