# Sub-plan J: Complete Legacy/Archive/Scratch Pruning (#10)

**Goal:** Finish the cleanup started in Phase 1 by removing stale compatibility shims, archived prototypes, overdue deprecations, and generated artifacts.

**Files to inspect / modify**
- `archive/legacy-shims/`
- `archive/prototypes/`
- `artifacts/` (stale subdirs only; preserve `.gitkeep` skeletons)
- `docs/governance/compatibility-debt-registry.md`
- `contracts/deprecations/generated-contract-deprecations.json`
- `config/ci/facade-import-allowlist.yaml`
- Root-level scratch files missed in Phase 1

**Approach**
1. Enforce overdue removal targets in the compatibility-debt registry and deprecation JSON.
2. Delete `archive/legacy-shims/` directories that are no longer imported.
3. Remove or relocate stale prototypes under `archive/prototypes/`.
4. Clean stale generated artifacts under `artifacts/` while preserving the directory skeleton and `.gitkeep` files.
5. Update allowlists and registries to remove resolved entries.
6. Run a final pass for empty files and scratch scripts at root.

**Validation**
- `make check-legacy-debt` passes.
- `make check-deprecations` passes.
- `make check-conflict-markers` passes.
- `git status` shows only intended deletions and registry updates.

**Rollback**
Restorable from git history. Archive anything with compliance value before deletion.

**Risks**
- Compliance/audit evidence may be lost if archived files are deleted instead of moved to long-term storage.
- Allowlist updates can break CI gates if stale entries are still referenced.
