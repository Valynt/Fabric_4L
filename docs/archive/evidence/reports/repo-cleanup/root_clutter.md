# Root Clutter Analysis

**Generated:** 2026-05-02  
**Repository:** Fabric_4L  
**Analysis:** Phase 1 Inventory

## Summary

The repository root contains **22 markdown/text files** and **2 temporary artifacts** that should be relocated to establish a clean enterprise SaaS structure.

## Files Requiring Relocation

### Documentation Files → `docs/`

| File | Size | Destination | Notes |
|------|------|-------------|-------|
| AGENTS.md | 8.5 KB | docs/AGENTS.md | Agent documentation |
| Architecture.md | 32 KB | docs/architecture/system-overview.md | Main architecture doc |
| CHANGES.md | 8.3 KB | docs/CHANGES.md | Change log supplement |
| contract.md | 24.5 KB | docs/contract.md | Platform contract |
| DEPRECATIONS.md | 11.7 KB | docs/DEPRECATIONS.md | Deprecation tracking |
| Providers.md | 11.8 KB | docs/Providers.md | Provider documentation |
| VERSIONING.md | 3.4 KB | docs/VERSIONING.md | Version policy |

### Report Files → `reports/`

| File | Size | Destination | Notes |
|------|------|-------------|-------|
| ASSURANCE_REMEDIATION_REPORT.md | 12.5 KB | reports/ASSURANCE_REMEDIATION_REPORT.md | Audit report |
| audit_violations.txt | 267 KB | reports/audit_violations.txt | Contract violations |
| DEAD_CODE_SWEEP_REPORT.md | 2.7 KB | reports/DEAD_CODE_SWEEP_REPORT.md | Dead code analysis |
| SECURITY_FIXES_IMPLEMENTED.md | 6.9 KB | reports/SECURITY_FIXES_IMPLEMENTED.md | Security fixes log |

### Testing Files → `docs/testing/` or `tests/`

| File | Size | Destination | Notes |
|------|------|-------------|-------|
| TEST_CATALOG.md | 20.8 KB | docs/testing/TEST_CATALOG.md | Test documentation |
| test_search_debug.py | 2 KB | tests/debug/ | Debug script |

### Generated Files → `generated/`

| File | Size | Destination | Notes |
|------|------|-------------|-------|
| build.log | 15.4 KB | generated/logs/build-2026-05-02.log | Build output |
| build-progress.log | 8.4 KB | generated/logs/build-progress-2026-05-02.log | Build progress |
| e2e-results.log | 0.1 KB | generated/logs/ | Test output |
| e2e-test-output.log | 0.1 KB | generated/logs/ | Test output |
| valuepacks_output.txt | 344 KB | generated/valuepacks_output-2026-05-02.txt | Generated data |

### Legacy/Archive → `archive/`

| File | Size | Destination | Notes |
|------|------|-------------|-------|
| 4 layer | 14 KB | archive/4-layer-legacy.md | Old documentation |

### Delete (Temporary Artifacts)

| File/Dir | Action | Reason |
|----------|--------|--------|
| C:UsersBBBAppDataLocalTemptmpf7egnv3erelease | Delete | Windows temp folder |
| C:UsersBBBAppDataLocalTemptmpflqqs5kprelease | Delete | Windows temp folder |

## Files to Keep in Root

These files serve as the "front door" to the repository and should remain at the root:

- **README.md** - Main project documentation
- **CHANGELOG.md** - Version history
- **CONTRIBUTING.md** - Contributor guidelines
- **SECURITY.md** - Security policy
- **ROADMAP.md** - Project roadmap (large file - 209 KB)
- **Makefile** - Build automation
- **pyproject.toml** - Python project config
- **pytest.ini** - Test configuration
- **package.json** - Node.js dependencies
- **pnpm-workspace.yaml** - Workspace config
- **.gitignore** - Git exclusions
- **.gitattributes** - Git attributes
- **.pre-commit-config.yaml** - Pre-commit hooks
- **.tool-versions** - Tool versions (asdf/mise)
- **.npmrc** - npm configuration
- **.env.dev.example** - Environment template

## Cache/Generated Directories to Clean

These should be deleted and added to `.gitignore`:

| Directory | Location | Count |
|-----------|----------|-------|
| `__pycache__/` | Multiple (recursive) | Many |
| `.pytest_cache/` | Root | 8 items |
| `.mypy_cache/` | Root | 4 items |
| `.ruff_cache/` | Root | 44 items |
| `node_modules/` | Root | 8 items |
| `.vite/` | Root | 2 items |
| `test-results/` | Root | 1 item |

## Statistics

| Category | Count | Total Size |
|----------|-------|------------|
| Documentation files | 7 | ~90 KB |
| Report files | 4 | ~289 KB |
| Testing files | 2 | ~23 KB |
| Generated files | 5 | ~368 KB |
| Cache directories | 7+ | ~10 MB+ |
| Legacy/archive | 1 | 14 KB |
| **Total to relocate** | **~30 items** | **~10.7 MB** |

## Recommended Action Order

1. **Phase 2**: Delete cache dirs and temp folders first (safest)
2. **Phase 3**: Move generated files to `generated/`
3. **Phase 3**: Move report files to `reports/`
4. **Phase 3**: Move documentation to `docs/`
5. **Phase 5+**: Execute major structural moves (frontend, services)
