# Backend-Integrated Stack Startup Issue

**Date:** 2026-05-04
**Sprint:** Sprint 3 - Backend-Integrated Product Confidence and Runtime Policy Checks

## Issue Summary

Attempted to start the backend-integrated stack using `docker-compose.backend-integrated.yml` but the build failed during the image build phase.

## Command Executed

```bash
docker compose -f docker-compose.backend-integrated.yml up --build -d
```

## Error Output

```text
Exit code: 1
Output:
[+] up 0/8
- Image fabric_4l-layer1-worker Building 0.1s
- Image fabric_4l-layer1 Building 0.1s
- Image fabric_4l-layer6 Building 0.1s
- Image fabric_4l-layer4 Building 0.1s
- Image fabric_4l-layer5 Building 0.1s
- Image fabric_4l-layer2 Building 0.1s
- Image fabric_4l-layer5-migrate Building 0.1s
- Image fabric_4l-layer3 Building 0.1s
```

## Root Cause Analysis

**Initial observed issue:** Docker network/download error during package installation

- Error occurs while downloading packages from debian repositories
- `failed to receive status: rpc error: code = Unavailable desc = error reading from server: EOF`
- This remains a valid observed failure mode, but it is no longer sufficient to classify the blocker as purely environmental

**Validation performed:**

- Docker Compose YAML syntax valid (`docker compose config` succeeded)
- All service directories exist with valid Dockerfiles
- Volume mount paths correct (`./packages/shared/src/value_fabric/shared` exists)
- Init script path correct (`./scripts/db/init-multiple-dbs.sh` exists)
- Build contexts valid for all services

## Follow-up Repo Hardening Applied on 2026-05-05

Two backend-integrated compose fixes were applied after the initial report to remove avoidable repo-local fragility from the validation path:

1. **Layer 2 persistence wiring fixed**
   - Added `layer2_extraction` to `POSTGRES_MULTIPLE_DATABASES`
   - Set `layer2` `POSTGRES_DB=layer2_extraction`
   - Added explicit `LAYER2_DATABASE_URL=postgresql://postgres:postgres@postgres:5432/layer2_extraction`
   - Rationale: the backend-integrated stack should exercise Layer 2 against dedicated PostgreSQL-backed persistence rather than silently falling back to SQLite in development mode.

2. **Layer 1 build surface reduced for backend-integrated validation**
   - Set `INSTALL_PLAYWRIGHT_BROWSERS=false` for `layer1` and `layer1-worker` image builds in `docker-compose.backend-integrated.yml`
   - Rationale: the backend-integrated validation harness uses the Layer 1 ingestion compatibility API (`/api/v1/ingestion/sources`) and does not require browser-crawling binaries during stack startup. This removes a large optional download step from the build path that was implicated in the original failure.

These changes improve the odds that a rerun will distinguish transient network issues from actual backend-integrated service startup defects.

## Potential Causes

1. **Network connectivity**: Docker daemon cannot reach debian package mirrors
2. **Docker registry issues**: Temporary outages with Docker Hub or debian mirrors
3. **Firewall/proxy**: Corporate firewall or proxy blocking package downloads
4. **Docker daemon state**: Docker daemon may be in a degraded state

## Next Steps for Investigation

1. **Retry the targeted build first**: confirm whether the lighter Layer 1 image path still reproduces the original failure

   ```bash
   docker compose -f docker-compose.backend-integrated.yml build layer1
   ```

2. **Retry full backend-integrated startup** after the targeted build succeeds

   ```bash
   docker compose -f docker-compose.backend-integrated.yml up --build -d
   ```

3. **Check Docker daemon health**:

   ```bash
   docker ps
   docker info
   ```

4. **Test network connectivity**:

   ```bash
   docker run --rm debian:bookworm apt-get update
   ```

5. **Check for proxy settings**: Verify if Docker is configured to use a proxy

6. **If the rerun still fails, capture the exact failing service and build step**: do not assume the failure is still network-only unless the logs show the same boundary

## Workarounds

- **Retry build**: Network errors are often transient; retrying may succeed
- **Use pre-built images**: If available, use pre-built images instead of building from source
- **Configure Docker proxy**: If behind corporate firewall, configure Docker proxy settings
- **Focus on contract/deep tests**: Continue with contract and deep tests that don't require backend
- **Document as known issue**: Add to technical debt for later resolution

Since the backend stack cannot be started, Phase 1 backend validation is blocked. However:

- The seed script (`scripts/db/seed-e2e-data.ts`) is functional and can be used when backend is available
- Playwright backend-integrated configuration is ready (requires `@backend` tag on tests)
- Test infrastructure is in place (global-setup.ts seeds data automatically)

Proceeding with Phase 2 (backend-integrated test creation) which can be validated once backend issues are resolved.
