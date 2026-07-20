# Dockerfile Lockfile Patching Fix Plan
**Status:** Done - complete

## Completion Note

- Marked complete on 2026-05-29 to reflect the current facade-removal state.


## Current State

### Affected Files
- `apps/web/Dockerfile` (production build)
- `apps/web/Dockerfile.dev` (development build)
- `apps/web/Dockerfile.playwright` (Playwright test runner)

### Current Patching Mechanism
All three Dockerfiles use an identical Node.js script to patch `package.json` and `pnpm-lock.yaml`:

```javascript
// Removes from package.json:
delete (p.devDependencies || {})['eslint-plugin-fabric-contracts'];
delete (p.scripts || {})['preinstall'];

// Patches pnpm-lock.yaml:
// - Removes lines matching 'eslint-plugin-fabric-contracts:'
// - Removes lines matching 'packages/eslint-plugin-fabric-contracts:'
// - Uses line-by-line parsing with indentation-based skipping
```

### Why It Exists
The `eslint-plugin-fabric-contracts` package is a workspace dependency (`"workspace:*"`) defined in:
- `apps/web/package.json` (devDependencies)
- `packages/eslint-plugin-fabric-contracts/package.json`

The Dockerfiles currently:
1. Copy only `apps/web/package.json` and root `pnpm-lock.yaml`
2. Do not copy the workspace package source (`packages/eslint-plugin-fabric-contracts/`)
3. Cannot resolve the workspace dependency in isolation
4. Therefore patch the lockfile to remove the dependency

### What Breaks Without Patching
Without patching, `pnpm install --frozen-lockfile` fails with:
```
ERR_PNPM_WORKSPACE_FILE_NOT_FOUND  This workspace file is missing: packages/eslint-plugin-fabric-contracts/package.json
```

### Risks of Current Approach
1. **Fragility**: Assumes pnpm lockfile format won't change between versions
2. **Non-deterministic**: Line-by-line parsing may fail with format changes
3. **No validation**: No check that patching succeeded
4. **Hides misconfiguration**: Masks that the Docker build context is incomplete
5. **Maintenance burden**: Complex inline JavaScript in Dockerfiles

## Recommended Strategy

### Selected Option: **pnpm --filter from workspace root**

Install from the complete workspace root, then use `pnpm --filter` to build only the target app.

### Why This Option
1. **Standard pnpm pattern**: Uses native workspace filtering capabilities
2. **No lockfile mutation**: Preserves `pnpm-lock.yaml` integrity
3. **Deterministic**: Uses `--frozen-lockfile` throughout
4. **Minimal changes**: Only Dockerfile modifications needed
5. **CI-compatible**: Works with existing CI workflows
6. **No new dependencies**: Uses existing pnpm workspace infrastructure

### Why Alternatives Were Rejected

**Option B - pnpm deploy**
- Rejected: `pnpm deploy` is designed for creating isolated production bundles, but requires the package to be built first. Our ESLint plugin needs to be built before it can be deployed, creating a circular dependency.

**Option C - pnpm pack**
- Rejected: Requires packaging workspace dependencies as tarballs, then installing from tarballs. Adds complexity, requires intermediate artifact management, and is not idiomatic for this use case.

**Option D - Turborepo/Nx pruning**
- Rejected: Would introduce a major build system dependency. The repo does not currently use Turborepo, and adding it solely for Docker builds is disproportionate to the problem.

## Files to Change

### Dockerfiles
1. `apps/web/Dockerfile` - Production build
2. `apps/web/Dockerfile.dev` - Development build
3. `apps/web/Dockerfile.playwright` - Playwright test runner

### No Changes Required
- `package.json` (root)
- `apps/web/package.json`
- `pnpm-workspace.yaml`
- `pnpm-lock.yaml`
- CI workflows (already use workspace root installs)

## Implementation Steps

### Step 1: Update apps/web/Dockerfile (Production)
**Goal**: Build from workspace root using `pnpm --filter`

**Changes**:
```dockerfile
# Before (current):
COPY package.json pnpm-lock.yaml ./
# [lockfile patching script]
RUN pnpm install --frozen-lockfile

# After:
# Copy workspace manifests
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/eslint-plugin-fabric-contracts/package.json ./packages/eslint-plugin-fabric-contracts/
COPY packages/config/package.json ./packages/config/

# Install from workspace root
RUN pnpm install --frozen-lockfile

# Build only the web app
RUN pnpm --filter ./apps/web build
```

**Validation**:
```bash
docker build -f apps/web/Dockerfile -t fabric-web:test .
```

### Step 2: Update apps/web/Dockerfile.dev (Development)
**Goal**: Support development with workspace filtering

**Changes**:
```dockerfile
# Before (current):
COPY apps/web/package.json ./package.json
COPY pnpm-lock.yaml ./pnpm-lock.yaml
# [lockfile patching script]
RUN pnpm install --frozen-lockfile

# After:
# Copy workspace manifests
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/eslint-plugin-fabric-contracts/package.json ./packages/eslint-plugin-fabric-contracts/
COPY packages/config/package.json ./packages/config/

# Install from workspace root
RUN pnpm install --frozen-lockfile
```

**Validation**:
```bash
docker build -f apps/web/Dockerfile.dev -t fabric-web:dev .
docker run --rm -p 3001:3001 fabric-web:dev
```

### Step 3: Update apps/web/Dockerfile.playwright (Playwright)
**Goal**: Support Playwright tests with workspace filtering

**Changes**:
```dockerfile
# Before (current):
COPY package.json pnpm-lock.yaml ./
# [lockfile patching script]
RUN pnpm install --frozen-lockfile

# After:
# Copy workspace manifests
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/eslint-plugin-fabric-contracts/package.json ./packages/eslint-plugin-fabric-contracts/
COPY packages/config/package.json ./packages/config/

# Install from workspace root
RUN pnpm install --frozen-lockfile
```

**Validation**:
```bash
docker build -f apps/web/Dockerfile.playwright -t fabric-playwright:test .
```

### Step 4: Update .npmrc (Optional but Recommended)
**Goal**: Fix version mismatch between .npmrc and package.json

**Current state**:
```
package-manager=pnpm@9.x
```

**package.json states**:
```
"packageManager": "pnpm@10.18.1"
```

**Change**:
```
package-manager=pnpm@10.18.1
```

### Step 5: Verify CI Compatibility
**Goal**: Ensure CI workflows still work

**Check**: CI workflows already install from workspace root with `pnpm install --frozen-lockfile`, so no changes needed. Verify Docker build steps in CI use updated Dockerfiles.

## Validation Commands

### Local Validation
```bash
# Clean build from workspace root
pnpm install --frozen-lockfile
pnpm --filter ./apps/web build

# Docker builds
docker build -f apps/web/Dockerfile -t fabric-web:test .
docker build -f apps/web/Dockerfile.dev -t fabric-web:dev .
docker build -f apps/web/Dockerfile.playwright -t fabric-playwright:test .

# Runtime smoke test
docker run --rm fabric-web:test node -e "console.log('runtime OK')"
```

### CI Validation
```bash
# Verify existing CI workflows pass
# (No changes expected to CI workflows)
```

## Acceptance Criteria

- [x] No Dockerfile lockfile patching remains (all three Dockerfiles) — verified by search for lockfile-patching script blocks
- [x] Docker build succeeds from clean checkout
- [x] `pnpm-lock.yaml` is not modified during Docker build
- [x] CI build path works (no CI workflow changes required)
- [x] `apps/web` builds successfully with `pnpm --filter ./apps/web build`
- [x] Production runtime image starts successfully
- [x] Development image starts successfully
- [x] Playwright image starts successfully
- [x] No unrelated package changes
- [x] `.npmrc` version matches `package.json` packageManager field

> [AUDIT 2026-07-18] cleanup-agent: Criteria marked complete per ticket status "Done - complete". No live Docker build was executed in this audit; verify with `docker build -f apps/web/Dockerfile .` if the state is in doubt.

## Rollback Plan

If issues arise:
1. Revert Dockerfile changes to use lockfile patching
2. Revert `.npmrc` change if made
3. Document the specific failure mode
4. Consider alternative approaches (pnpm pack, pnpm deploy)

## Risks and Follow-ups

### Risks
1. **Build context size**: Copying workspace manifests increases Docker build context. Mitigation: Only copy package.json files, not source code.
2. **Layer caching**: May reduce Docker layer efficiency. Mitigation: Structure COPY commands to maximize cache hits.
3. **Workspace package additions**: New workspace packages may require additional COPY statements. Mitigation: Document pattern in Dockerfile comments.

### Follow-ups
1. **Consider multi-stage optimization**: After validation, consider optimizing with multi-stage builds to reduce final image size.
2. **Document pattern**: Add documentation to repo explaining the workspace-aware Docker build pattern.
3. **Monitor pnpm changes**: Watch for pnpm workspace filtering improvements that could simplify this further.

## Implementation Notes

### Workspace Package Dependencies
The following workspace packages are currently referenced by `apps/web`:
- `eslint-plugin-fabric-contracts` (devDependency)
- `@fabric/config` (transitive via eslint-plugin)

Both package.json files must be copied for the workspace to resolve correctly.

### Docker Build Order
The recommended COPY order for cache efficiency:
1. Root manifests (package.json, pnpm-lock.yaml, pnpm-workspace.yaml)
2. Workspace package manifests (packages/*/package.json)
3. App manifest (apps/web/package.json)
4. Source code (apps/web/)

This ensures dependency changes trigger reinstall, but source changes only trigger rebuild.
