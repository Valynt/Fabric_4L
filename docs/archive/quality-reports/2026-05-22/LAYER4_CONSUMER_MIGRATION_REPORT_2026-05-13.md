# Layer 4 Consumer Migration Report

**Date:** 2026-05-13
**ADR:** ADR-027 (Accepted) — Service-First Canonical Path Model
**Scope:** Audit and migrate consumers of `value_fabric.layer4.*` imports

## Executive Summary

Layer 4 implementation already lives in `services/layer4-agents/src/` and production code within the service uses relative imports. No production/runtime consumers outside the service needed migration.

**Key finding:** Direct service imports from `services/layer4-agents/src/` do not work because Layer 4 source code uses relative imports (e.g. `from ..models.tool_schemas import ...`) that depend on the `value_fabric.layer4` namespace package hierarchy. Restructuring the service package (e.g. moving `src/*` to `src/layer4_agents/*`) is required before true direct imports can work.

## Discovery Results

### Imports Found (by category)

| Category | Count | Files |
| :------- | :---- | :---- |
| Tests | 4 | `tests/tools/test_tool_tenant_boundaries.py`, `tests/tools/test_tool_result_contract.py`, `tests/security/test_competitive_tools_tenant_isolation.py`, `tests/security/test_cross_layer_tenant_isolation_matrix.py` |
| Scripts | 2 | `scripts/validation/generate_live_llm_provider_evidence.py`, `scripts/generate_openapi.py` |
| Shim verification | 2 | `scripts/verify_layer4_shim.py`, `scripts/verify_layer4_imports.py` |
| Production/runtime | 0 | None |

### Imports Intentionally Left in Place

All test and script imports remain as `value_fabric.layer4.*` because:

1. **Relative import dependency:** Layer 4 modules use `from ..models...` which requires the namespace package parent. Changing imports to direct service paths breaks with `ImportError: attempted relative import beyond top-level package`.
2. **No production impact:** These are tests and build scripts, not production runtime code.
3. **Backward compatibility:** The shim must remain functional during the transition window.

## Changes Made

### ADR-027 Ratification
- **Status:** Updated from "Proposed" to "Accepted"
- **Decision:** Service-first canonical path model
- **Layer 4 note:** Added documented constraint that relative imports block direct service imports pending package restructuring

### CI Fixes (PR #347)
- `.github/workflows/launch-readiness.yml`: Added `python -m pip install pyyaml` before Stage 1 validators
- `.github/workflows/launch-readiness.yml`: Fixed Stage 3 requirements path from `requirements-test.txt` to `tests/requirements-test.txt`
- `tests/requirements-test.txt`: Added `pyyaml>=6.0`
- `tests/ci/test_launch_readiness_workflow.py`: Added regression tests for both fixes

### Layer 4 Regression Test
- `tests/ci/test_layer4_canonical_service_imports.py`: New test file documenting the current state:
  - Verifies shim path appends service source tree
  - Verifies canonical source files exist in service tree
  - Verifies shim file is a thin path appender (no business logic)
  - Verifies no production runtime code imports from its own shim
  - Documents the direct import blocker (relative imports fail)

### Documentation Updates
- `docs/architecture/adr-027-layer3-canonical-path.md`: Updated status, decision, options, consequences, migration status
- `docs/reference/layer-runtime-path-governance.md`: Updated layer path matrix to service-first canonical model

## Test Results

| Test Suite | Result |
| :--------- | :----- |
| `tests/ci/test_launch_readiness_workflow.py` | 7 passed |
| `tests/ci/test_layer4_canonical_service_imports.py` | 5 passed |

## Risks and Follow-up

| Risk | Mitigation |
| :--- | :--------- |
| Direct service imports for Layer 4 don't work yet | Restructure `services/layer4-agents/src/*` into `services/layer4-agents/src/layer4_agents/*` so the service is a proper Python package with no relative-import dependency on namespace parent |
| `value_fabric.layer4` shim continues to be used by tests | Acceptable during transition; regression test ensures shim stays thin |
| CI gate `check_layer4_canonical_imports.py` may timeout on large directories | Script runs quickly in normal conditions; if timeouts recur, consider narrowing scan roots or caching file list |

## Acceptance Criteria Checklist

- [x] No production/runtime code imports `value_fabric.layer4.*` (verified by regression test)
- [x] Layer 4 shim remains available for backward compatibility
- [x] ADR-027 ratified with documented constraints
- [x] CI fixes for PR #347 implemented and tested
- [x] New regression test documents current import topology
- [x] No behavior changes — documentation and test-only changes
