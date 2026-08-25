## Summary

🎯 **What:** Removed the unused `MissingTenantContextError` import from `services/api/app/core/database.py`. Updated vulnerable dependencies (`astro`, `axios`, `postcss`) in templates and archives which was failing the `Dependency Review` action.
💡 **Why:** To improve code maintainability and resolve the unused import linting issue. To resolve the `Scan Node.js Dependencies (web)` check run failure.
✅ **Verification:** Verified via `ruff check` that the file no longer reports unused imports.

## Governance Impact
- **Contract shape impact:** No API contract changes.
- **Tenant isolation impact:** No change.
- **Compatibility shim impact:** No change.

## Why overlap is expected
The overlap is expected because this PR updates the same files and fixes unused imports/dependencies like other PRs.
