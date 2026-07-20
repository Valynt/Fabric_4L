# Facade Compatibility Shims

## Overview

The `value_fabric.layer*` facade provides critical Python path resolution by appending service source paths to package `__path__`. This document documents intentionally retained compatibility shims.

## Critical Path Resolution

The facade cannot be removed until canonical package import resolution is solved. The facade appends service source paths to `__path__` to enable imports like `value_fabric.layer3.api.main` to resolve to the canonical service tree at `services/layer3-knowledge/src/`.

See `.jr/tickets/IMPORT-ARCH-FACADE-RESOLUTION.md` for details on the path resolution architecture and blockers to facade removal.

## Retained Shims

### L3 Facade (value_fabric.layer3)
- **Owner:** Layer 3 Maintainers
- **Removal Target:** 2026-09-30
- **Reason:** Complex wrapper migration with path-redirect shim architecture
- **Documentation:** `.jr/tickets/L3-FACADE-WRAPPER-MIGRATION.md`
- **Blockers:** Path-redirect shim, bare intra-package imports, Neo4j dependencies
- **Status:** 223 facade imports intentionally retained
- **Deprecation:** Added - warns on import with reference to L3-FACADE-WRAPPER-MIGRATION.md

### L4 Billing Shims (value_fabric.layer4.billing.*)
- **Owner:** Layer 4 Maintainers
- **Removal Target:** Indefinite (compatibility shim)
- **Reason:** Billing service compatibility for external consumers
- **Files:**
  - `value_fabric/layer4/billing/services/__init__.py`
  - `value_fabric/layer4/billing/schemas.py`
  - `value_fabric/layer4/billing/models.py`
- **Status:** Intentionally retained for external API compatibility

### L5 Facade (value_fabric.layer5)
- **Owner:** Layer 5 Maintainers
- **Removal Target:** 2026-09-30
- **Reason:** Zero production imports found, retained for backward compatibility
- **Documentation:** `docs/reference/layer5/source-of-truth.md`
- **Status:** 1 facade import (test docstring)
- **Deprecation:** Added - warns on import with reference to ADR-027

### L1, L4, L6 Facades
- **Owner:** Platform Team
- **Removal Target:** Indefinite (until canonical import resolution solved)
- **Reason:** Package restructuring complete, but facade provides critical path resolution
- **Status:** Deprecated with warnings, retained for path resolution
- **Deprecation:** Added to all three facades

## CI Infrastructure References

The following files contain facade import references for CI infrastructure:
- Error message strings in CI gate scripts (`scripts/ci/check_layer*_imports.py`)
- Migration script docstrings documenting old-to-new mappings (`scripts/migrate_l*_test_imports_canonical.py`)
- Test patch targets in security/integration tests
- Contract tests verifying facade path resolution
- Facade shim docstrings (self-referential)

These are intentionally retained and documented in `config/ci/facade-import-allowlist.yaml`.

## Allowlist Configuration

The `config/ci/facade-import-allowlist.yaml` file defines all intentionally retained facade imports with:
- `reason`: Why the import is retained
- `owner`: Team responsible for the import
- `removal_target`: Date when the import should be removed (or "indefinite")

## Enforcement

The `scripts/ci/check_value_fabric_facade_imports.py` script enforces the allowlist:
- New facade imports are blocked
- Only allowlisted references are permitted
- Run with `--fail` flag for enforcement mode
- Currently runs in non-failing mode (report only)

## Deprecation Warnings

All facade shims now emit deprecation warnings on import:
- **L1:** "value_fabric.layer1 is deprecated. Use canonical imports: layer1_ingestion.*"
- **L3:** "value_fabric.layer3 is deprecated. Use canonical imports: layer3_knowledge.*. This facade will be removed after 2026-09-30 per L3-FACADE-WRAPPER-MIGRATION.md"
- **L4:** "value_fabric.layer4 is deprecated. Use canonical imports: layer4_agents.*"
- **L5:** "value_fabric.layer5 is deprecated. Use canonical imports: layer5_ground_truth.*. This facade will be removed after 2026-09-30 per ADR-027"
- **L6:** "value_fabric.layer6 is deprecated. Use canonical imports: layer6_benchmarks.*"

## Dockerfiles and CI Configs

Dockerfiles and CI configs do not have direct facade path dependencies. They use standard service source paths (e.g., `PYTHONPATH=/app:/app/src`), and the facade provides path resolution at import time. No changes needed to Dockerfiles or CI configs.

## Removal Process

To remove a facade shim:
1. Migrate all consumers to canonical imports
2. Solve canonical package import resolution (see IMPORT-ARCH-FACADE-RESOLUTION.md)
3. Update allowlist to remove entry
4. Validate tests pass
5. Remove facade code
6. Update documentation

## Current Inventory

- **Total facade imports:** 253
- **Allowlisted imports:** 253 (100%)
- **Unallowlisted imports:** 0
- **By layer:**
  - L1: 7 (CI infrastructure)
  - L3: 223 (intentionally retained until 2026-09-30)
  - L4: 17 (compatibility shims and test patch targets)
  - L5: 1 (CI infrastructure)
  - L6: 5 (CI infrastructure)

## Next Steps

1. Enable enforcement in CI (add to `.github/workflows/pr-checks.yml`)
2. Monitor for new facade imports (blocked by allowlist)
3. Proceed with L3 wrapper migration per L3-FACADE-WRAPPER-MIGRATION.md
4. Solve canonical package import resolution per IMPORT-ARCH-FACADE-RESOLUTION.md
5. Remove facades once canonical imports work without path bootstrapping
