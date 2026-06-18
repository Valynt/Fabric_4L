# High-Risk Moves Requiring Review

**Generated:** 2026-05-02
**Repository:** Fabric_4L
**Phase:** 1 Inventory

## Overview

The following moves are classified as **HIGH RISK** due to:
- Active code dependencies
- Import path changes requiring updates
- Environment file preservation needs
- Potential service disruption

## Critical Risk Moves

### 1. Backend Service Migration (`services/` → `services/`)

**Risk Level:** CRITICAL
**Impact:** All 6 backend services

```
services/layer1-ingestion/     → services/layer1-ingestion/
services/layer2-extraction/    → services/layer2-extraction/
services/layer3-knowledge/     → services/layer3-knowledge/
services/layer4-agents/        → services/layer4-agents/
services/layer5-ground-truth/  → services/layer5-ground-truth/
services/layer6-benchmarks/    → services/layer6-benchmarks/
```

**Specific Concerns:**
- **Environment files**: `.env`, `.env.staging`, `.env.test`, `.env.production.example` must remain with services
- **Docker Compose**: `docker-compose.full.yml` references service paths
- **Migrations**: Database migration files must move with services
- **Import chains**: All `from value_fabric.layerX...` imports must be updated
- **Tests**: Internal service tests reference relative imports

**Required Actions:**
1. Preserve .env files in service directories during move
2. Update import statements in ALL Python files
3. Update docker-compose volume mounts
4. Update Makefile targets
5. Update CI workflow paths
6. Verify migration history remains intact

**Validation:**
```bash
pytest --collect-only -q
python -c "from value_fabric.layer1 import ..."  # Test imports
```

---

### 2. `value_fabric/` Junction Deletion

**Risk Level:** HIGH
**Impact:** Python import resolution

```
value_fabric/ (junction/symlink) → DELETE
```

**Specific Concerns:**
- Windows junctions currently provide `import value_fabric` compatibility
- Tests may reference these paths
- IDE configurations may reference junction paths

**Verification Steps:**
1. Check for any `import value_fabric` statements that rely on junction
2. Verify new `packages/shared/` provides same exports
3. Check `.windsurf/` agent configurations for hardcoded paths
4. Check IDE settings (`.vscode/settings.json`)

**Fallback Plan:**
If deletion breaks imports, recreate as proper Python package with `__init__.py` re-exports.

---

### 3. Root `shared/` → `packages/shared/`

**Risk Level:** HIGH
**Impact:** Cross-layer shared modules

```
shared/identity/      → packages/shared/src/value_fabric/shared/identity/
shared/audit/         → packages/shared/src/value_fabric/shared/audit/
shared/crypto/        → packages/shared/src/value_fabric/shared/crypto/
shared/governance/    → packages/shared/src/value_fabric/shared/governance/
shared/llm_safety/    → packages/shared/src/value_fabric/shared/llm_safety/
shared/models/        → packages/shared/src/value_fabric/shared/models/
shared/observability/ → packages/shared/src/value_fabric/shared/observability/
shared/rate_limiting/ → packages/shared/src/value_fabric/shared/rate_limiting/
shared/secrets/       → packages/shared/src/value_fabric/shared/secrets/
shared/security/      → packages/shared/src/value_fabric/shared/security/
shared/tracing/       → packages/shared/src/value_fabric/shared/tracing/
```

**Specific Concerns:**
- `shared/identity/` is critical for authentication - used by ALL layers
- `shared/security/` contains tenant isolation code
- Tests import from `shared.*` directly
- Services have `sys.path` hacks to access `shared/`

**Required Actions:**
1. Create proper Python package structure with `pyproject.toml`
2. Update all `from shared.X import ...` statements
3. Update `sys.path` manipulations in service entry points
4. Verify no circular import issues

**Critical Files:**
- `shared/identity/__init__.py`
- `shared/identity/middleware.py`
- `shared/audit/ledger.py`
- `shared/governance/abom.py`

---

### 4. Frontend Move (`frontend/client/` → `apps/web/`)

**Risk Level:** MEDIUM-HIGH
**Impact:** React application build system

```
frontend/client/ → apps/web/
```

**Specific Concerns:**
- 486 items in `frontend/client/src/`
- Vite configuration has hardcoded paths
- pnpm workspace references `frontend/`
- Import aliases (`@/components`, etc.) may break
- ESLint configuration references paths
- Playwright e2e tests use `frontend/` base URL

**Required Actions:**
1. Update `vite.config.ts` base paths
2. Update `pnpm-workspace.yaml`
3. Update `package.json` scripts
4. Update import aliases in `tsconfig.json`
5. Update ESLint config
6. Update Playwright config base URLs
7. Verify build works: `cd apps/web && pnpm build`

**Validation:**
```bash
cd apps/web
pnpm install
pnpm build
pnpm test
```

---

### 5. UI Prototype Separation (`_ui-prototype/` → `prototypes/ui/`)

**Risk Level:** MEDIUM
**Impact:** Prototype isolation

```
_ui-prototype/ → prototypes/ui/
```

**Specific Concerns:**
- 133 items including research documents
- Contains `.docx` files (whitepapers)
- May have code that imports from `frontend/`
- `non-production/` subdirectory may reference production paths

**Required Actions:**
1. Add `prototypes/ui/README.md` with clear isolation notice
2. Verify no imports from `apps/web/` (after move)
3. Check for absolute path references

---

## Medium Risk Moves

### 6. Script Reorganization (`scripts/` → categorized)

**Risk Level:** MEDIUM
**Impact:** Makefile and CI references

```
scripts/*health*.ps1       → scripts/dev/
scripts/*seed*.ts          → scripts/db/
scripts/*security*.py      → scripts/security/
```

**Required Actions:**
1. Update `Makefile` command references
2. Update `.github/workflows/*.yml` script paths
3. Update documentation references

---

### 7. Infrastructure Consolidation (`k8s/` → `infra/k8s/`)

**Risk Level:** MEDIUM
**Impact:** Deployment manifests

```
k8s/           → infra/k8s/
monitoring/    → infra/monitoring/
docker-compose.*.yml → infra/docker/
```

**Required Actions:**
1. Update Kustomize base paths
2. Update CI deployment workflows
3. Verify no absolute paths in manifests

---

## Low Risk Moves

### 8. Documentation Consolidation

**Risk Level:** LOW
**Impact:** Documentation links

```
docs/explanations/adr/ → docs/adr/
docs/ → docs/layer-docs/
```

**Required Actions:**
1. Update internal documentation links
2. Update README.md references

---

## Pre-Move Checklist for Each High-Risk Move

Before executing any HIGH risk move:

- [ ] Create backup branch: `git checkout -b cleanup/phase-X-backup`
- [ ] Run full test suite and record results
- [ ] Identify all import references using grep
- [ ] Identify all path references in configs
- [ ] Document rollback procedure
- [ ] Verify no uncommitted changes
- [ ] Have working directory snapshot

## Rollback Strategy

If any move fails:

1. **Immediate**: `git checkout -- .` to restore from backup branch
2. **Git reset**: `git reset --hard HEAD` if no backup branch
3. **Partial fix**: Revert specific file moves with `git checkout`
4. **Communication**: Document failure in `ROLLBACK-YYYY-MM-DD.md`

## Validation After Each Risk Tier

After HIGH risk moves:
```bash
make verify  # or equivalent verification
pytest --collect-only -q
```

After MEDIUM risk moves:
```bash
make test-smoke
```

After LOW risk moves:
```bash
ls -la  # Visual verification
```
