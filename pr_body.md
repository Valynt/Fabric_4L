## Summary

🎯 **What:** Removed the unused `MissingTenantContextError` import from `services/api/app/core/database.py`.
💡 **Why:** To improve code maintainability and resolve the unused import linting issue.
✅ **Verification:** Verified via `ruff check` that the file no longer reports unused imports.

## Governance Impact
- **Contract shape impact:** No API contract changes.
- **Tenant isolation impact:** No change.
- **Compatibility shim impact:** No change.
