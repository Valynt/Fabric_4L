# Sub-plan G: Remove Root/Namespace Shims (#3)

**Goal:** Delete the `value_fabric/` root shim and layer-specific re-exports, replacing all internal imports with canonical paths.

**Canonical paths**
- Shared code: `packages/shared/src/value_fabric/shared/`
- Layer runtime code: `services/layerN-*/src/<layerN_*/>`
- Platform contract: `packages/platform-contract/src/`

**Files to inspect / modify**
- `value_fabric/` (root shim)
- `packages/shared/src/value_fabric/layer2/`
- `config/ci/facade-import-allowlist.yaml`
- `scripts/ci/check_value_fabric_facade_imports.py`
- `scripts/ci/check_value_fabric_public_imports.py`
- `docs/governance/compatibility-debt-registry.md`
- All Python files importing `from value_fabric.layer*` or `import value_fabric.layer*`

**Approach**
1. Run a global import census and migrate every `value_fabric.layer*` import to the canonical service/package path.
2. Delete root `value_fabric/` and `packages/shared/src/value_fabric/layer2/`.
3. Remove the facade allowlist and the dedicated CI checks (or convert them to a generic import-policy check).
4. Update the compatibility-debt registry to mark the shim resolved.

**Validation**
- `grep -R 'from value_fabric\.' --include='*.py' .` returns no hits.
- `make lint` passes.
- `pytest tests/contract` passes.
- `make check-value-fabric-public-imports` (if kept) passes or is removed.

**Rollback**
Restore the shim directory and allowlist from git history if external consumers still need it.

**Risks**
- External integrations or stale notebooks may still import via `value_fabric.layer*`.
- Some `value_fabric.shared.*` imports must remain; only layer shims are targeted.
